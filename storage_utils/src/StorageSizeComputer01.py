#!/usr/bin/env python3
"""
Compute and report storage sizes of files and folders in a repository.

Recursively analyzes directory structure up to a specified depth, showing the
largest files and folders at each level. Outputs a human-readable report saved
to disk with timestamp.
"""

import argparse
import datetime
import time
import traceback
from pathlib import Path

this_filepath = Path(__file__)
this_filename = this_filepath.stem
root_dirpath = this_filepath.parent.parent


def format_size(size_bytes):
    """
    Convert bytes to human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string (e.g., "1.2 GB", "500 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            if unit == 'B':
                return f"{size_bytes:.0f} {unit}"
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def compute_size(path, skip_symlinks=True):
    """
    Compute total size of a file or directory.
    
    Args:
        path: Path object to compute size for
        skip_symlinks: Whether to skip symbolic links
        
    Returns:
        Total size in bytes
    """
    if skip_symlinks and path.is_symlink():
        return 0
    
    if path.is_file():
        try:
            return path.stat().st_size
        except (PermissionError, OSError):
            return 0
    
    if path.is_dir():
        total_size = 0
        try:
            for item in path.iterdir():
                if skip_symlinks and item.is_symlink():
                    continue
                total_size += compute_size(item, skip_symlinks)
        except (PermissionError, OSError):
            pass
        return total_size
    
    return 0


def analyze_directory(dir_path, current_level, max_levels, max_entries, skip_symlinks=True, indent=""):
    """
    Analyze directory contents and generate report lines.
    
    Args:
        dir_path: Path to the directory to analyze
        current_level: Current depth level (0-indexed)
        max_levels: Maximum depth to traverse
        max_entries: Maximum entries to show per directory
        skip_symlinks: Whether to skip symbolic links
        indent: Indentation string for current level
        
    Returns:
        List of report lines
    """
    lines = []
    
    if current_level >= max_levels:
        return lines
    
    try:
        entries = []
        for item in dir_path.iterdir():
            if skip_symlinks and item.is_symlink():
                continue
            
            size = compute_size(item, skip_symlinks)
            entries.append({
                'path': item,
                'size': size,
                'is_dir': item.is_dir()
            })
        
        # Sort by size (largest first)
        entries.sort(key=lambda x: x['size'], reverse=True)
        
        # Show top entries
        shown_entries = entries[:max_entries]
        skipped_entries = entries[max_entries:]
        
        for entry in shown_entries:
            item_type = "DIR " if entry['is_dir'] else "FILE"
            size_str = format_size(entry['size'])
            lines.append(f"{indent}{item_type} {entry['path'].name:<50} {size_str:>12}")
            
            # Recurse into directories
            if entry['is_dir'] and current_level + 1 < max_levels:
                sub_lines = analyze_directory(
                    entry['path'],
                    current_level + 1,
                    max_levels,
                    max_entries,
                    skip_symlinks,
                    indent + "  "
                )
                lines.extend(sub_lines)
        
        # Add summary line for skipped entries
        if skipped_entries:
            skipped_size = sum(e['size'] for e in skipped_entries)
            skipped_count = len(skipped_entries)
            size_str = format_size(skipped_size)
            lines.append(f"{indent}... and {skipped_count} more items totaling {size_str}")
    
    except (PermissionError, OSError) as e:
        lines.append(f"{indent}[Permission denied or error accessing directory]")
    
    return lines


def generate_report(repository_dirpath, num_levels, max_entries_single_level):
    """
    Generate storage size report for the repository.
    
    Args:
        repository_dirpath: Path to the repository root
        num_levels: Number of directory levels to analyze
        max_entries_single_level: Maximum entries to show per directory level
        
    Returns:
        List of report lines
    """
    repo_path = Path(repository_dirpath)
    
    if not repo_path.exists():
        raise ValueError(f"Repository path does not exist: {repository_dirpath}")
    
    if not repo_path.is_dir():
        raise ValueError(f"Repository path is not a directory: {repository_dirpath}")
    
    lines = []
    lines.append("=" * 80)
    lines.append("STORAGE SIZE REPORT")
    lines.append("=" * 80)
    lines.append(f"Repository: {repo_path.as_posix()}")
    lines.append(f"Analysis depth: {num_levels} level(s)")
    lines.append(f"Max entries per level: {max_entries_single_level}")
    lines.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    lines.append("")
    
    # Compute total size
    total_size = compute_size(repo_path, skip_symlinks=True)
    lines.append(f"TOTAL SIZE: {format_size(total_size)}")
    lines.append("")
    lines.append("-" * 80)
    lines.append("")
    
    # Analyze directory structure
    analysis_lines = analyze_directory(
        repo_path,
        current_level=0,
        max_levels=num_levels,
        max_entries=max_entries_single_level,
        skip_symlinks=True,
        indent=""
    )
    lines.extend(analysis_lines)
    
    lines.append("")
    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)
    
    return lines


def save_report(report_lines, repository_dirpath, num_levels, max_entries_single_level):
    """
    Save report to file with timestamp.
    
    Args:
        report_lines: List of report text lines
        repository_dirpath: Original repository path
        num_levels: Number of levels analyzed
        max_entries_single_level: Max entries per level
        
    Returns:
        Path to the saved report file
    """
    import json
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    report_dir = root_dirpath / "data" / "reports" / timestamp
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # Save report
    report_filename = "storage_sizes.txt"
    report_filepath = report_dir / report_filename
    
    with open(report_filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    # Save configuration
    config = {
        'repository_dirpath': str(Path(repository_dirpath).as_posix()),
        'repository_name': Path(repository_dirpath).name,
        'num_levels': num_levels,
        'max_entries_single_level': max_entries_single_level,
        'report_filename': report_filename,
        'script_filename': this_filename,
        'timestamp': timestamp,
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    config_filepath = report_dir / "config.json"
    with open(config_filepath, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    return report_filepath


def main():
    args = parse_args()
    
    print(f"Analyzing repository: {args.repository_dirpath}")
    print(f"Depth: {args.num_levels} levels")
    print(f"Max entries per level: {args.max_entries_single_level}")
    print()
    
    # Generate report
    report_lines = generate_report(
        args.repository_dirpath,
        args.num_levels,
        args.max_entries_single_level
    )
    
    # Save report
    report_filepath = save_report(
        report_lines,
        args.repository_dirpath,
        args.num_levels,
        args.max_entries_single_level
    )
    
    print(f"Report saved to: {report_filepath.as_posix()}")
    print()
    
    # Print report to console
    if args.verbose:
        print("Report contents:")
        print()
        for line in report_lines:
            print(line)
    
    return


def parse_args():
    parser = argparse.ArgumentParser(
        description='Compute storage sizes of files and folders in a repository'
    )
    parser.add_argument(
        '--repository_dirpath',
        type=str,
        required=True,
        help='Path to the repository root directory to analyze'
    )
    parser.add_argument(
        '--num_levels',
        type=int,
        required=True,
        help='Number of directory levels to traverse (1 = top-level only)'
    )
    parser.add_argument(
        '--max_entries_single_level',
        type=int,
        required=True,
        help='Maximum number of entries to display per directory level'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print the report to console in addition to saving it'
    )
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    print('Program started at ' + datetime.datetime.now().strftime('%d/%m/%Y %I:%M:%S %p'))
    start_time = time.time()
    try:
        main()
        run_result = 'Program completed successfully!'
    except Exception as e:
        print(e)
        traceback.print_exc()
        run_result = 'Error: ' + str(e)
    end_time = time.time()
    print('Program ended at ' + datetime.datetime.now().strftime('%d/%m/%Y %I:%M:%S %p'))
    print('Execution time: ' + str(datetime.timedelta(seconds=end_time - start_time)))
