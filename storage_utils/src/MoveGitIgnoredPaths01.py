#!/usr/bin/env python3
"""
Move git-ignored paths to a target directory maintaining repository structure.

Moves files and directories listed in the ignored paths file to a target directory,
preserving the directory structure. Handles directory merging and reports conflicts.
"""

import argparse
import datetime
import shutil
import time
import traceback
from pathlib import Path

this_filepath = Path(__file__)
this_filename = this_filepath.stem
root_dirpath = this_filepath.parent.parent


def load_ignored_paths(ignored_paths_filepath, verbose=False):
    """
    Load ignored paths from file.
    
    Args:
        ignored_paths_filepath: Path to the file containing ignored paths
        verbose: Whether to print verbose output
        
    Returns:
        List of path strings
    """
    if verbose:
        print(f'Loading ignored paths from: {ignored_paths_filepath}')
    
    with open(ignored_paths_filepath, 'r') as f:
        paths = [line.strip() for line in f if line.strip()]
    
    if verbose:
        print(f'Loaded {len(paths)} paths')
    
    return paths


def delete_empty_directories(dirpath, verbose=False):
    """
    Recursively delete empty directories.
    
    Args:
        dirpath: Path to check and potentially delete
        verbose: Whether to print verbose output
        
    Returns:
        True if directory was deleted, False otherwise
    """
    if not dirpath.is_dir():
        return False
    
    # First, try to delete empty subdirectories
    for child in list(dirpath.iterdir()):
        if child.is_dir() and not child.is_symlink():
            delete_empty_directories(child, verbose)
    
    # Check if directory is now empty
    if not any(dirpath.iterdir()):
        if verbose:
            print(f'  Deleting empty directory: {dirpath}')
        dirpath.rmdir()
        return True
    
    return False


def move_path_recursive(source_path, target_path, conflict_report, missing_report, verbose=False):
    """
    Recursively move a path from source to target, handling merges and conflicts.
    
    Args:
        source_path: Path object pointing to source
        target_path: Path object pointing to target
        conflict_report: List to append conflict messages
        missing_report: List to append missing path messages
        verbose: Whether to print verbose output
        
    Returns:
        Tuple (files_moved, bytes_moved)
    """
    files_moved = 0
    bytes_moved = 0
    
    # Check if source exists
    if not source_path.exists() and not source_path.is_symlink():
        msg = f'Source path does not exist: {source_path}'
        missing_report.append(msg)
        if verbose:
            print(f'  WARNING: {msg}')
        return files_moved, bytes_moved
    
    # If source is a symlink, skip it (shouldn't happen if ListGitIgnoredPaths works correctly)
    if source_path.is_symlink():
        msg = f'Source is a symlink (skipping): {source_path}'
        missing_report.append(msg)
        if verbose:
            print(f'  WARNING: {msg}')
        return files_moved, bytes_moved
    
    # If target doesn't exist, move the entire source
    if not target_path.exists():
        if verbose:
            print(f'  Moving: {source_path} -> {target_path}')
        
        # Create parent directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get size before moving
        if source_path.is_file():
            bytes_moved = source_path.stat().st_size
            files_moved = 1
        elif source_path.is_dir():
            for item in source_path.rglob('*'):
                if item.is_file() and not item.is_symlink():
                    bytes_moved += item.stat().st_size
                    files_moved += 1
        
        # Move the entire source
        shutil.move(str(source_path), str(target_path))
        return files_moved, bytes_moved
    
    # Target exists - need to handle merging
    if source_path.is_file():
        # Source is a file, target exists
        msg = f'File conflict: {source_path} (target already exists: {target_path})'
        conflict_report.append(msg)
        if verbose:
            print(f'  CONFLICT: {msg}')
        return files_moved, bytes_moved
    
    # Source is a directory, target also exists
    if target_path.is_file():
        # Can't merge directory into file
        msg = f'Type conflict: {source_path} is directory but target is file: {target_path}'
        conflict_report.append(msg)
        if verbose:
            print(f'  CONFLICT: {msg}')
        return files_moved, bytes_moved
    
    # Both are directories - merge recursively
    if verbose:
        print(f'  Merging directory: {source_path} -> {target_path}')
    
    for item in source_path.iterdir():
        target_item = target_path / item.name
        moved, moved_bytes = move_path_recursive(item, target_item, conflict_report, missing_report, verbose)
        files_moved += moved
        bytes_moved += moved_bytes
    
    return files_moved, bytes_moved


def move_ignored_paths(repository_dirpath, target_dirpath, ignored_paths_filepath, reports_dirpath, verbose=False):
    """
    Move all ignored paths to target directory.
    
    Args:
        repository_dirpath: Root directory of the repository
        target_dirpath: Directory to move files to
        ignored_paths_filepath: Path to file containing ignored paths
        reports_dirpath: Directory to save reports in
        verbose: Whether to print verbose output
        
    Returns:
        Tuple (files_moved, bytes_moved)
    """
    print('Loading ignored paths...')
    ignored_paths = load_ignored_paths(ignored_paths_filepath, verbose)
    
    conflict_report = []
    missing_report = []
    total_files_moved = 0
    total_bytes_moved = 0
    
    print(f'Moving {len(ignored_paths)} paths from {repository_dirpath} to {target_dirpath}...')
    
    for i, relative_path in enumerate(ignored_paths, 1):
        if verbose or i % 100 == 0:
            print(f'Processing {i}/{len(ignored_paths)}: {relative_path}')
        
        source_path = repository_dirpath / relative_path.rstrip('/')
        target_path = target_dirpath / relative_path.rstrip('/')
        
        files_moved, bytes_moved = move_path_recursive(
            source_path, target_path, conflict_report, missing_report, verbose
        )
        total_files_moved += files_moved
        total_bytes_moved += bytes_moved
    
    # Clean up empty directories in source
    print('Cleaning up empty directories...')
    for relative_path in sorted(ignored_paths, key=lambda p: p.count('/'), reverse=True):
        source_path = repository_dirpath / relative_path.rstrip('/')
        if source_path.exists() and source_path.is_dir():
            delete_empty_directories(source_path, verbose)
    
    # Save reports
    if conflict_report:
        conflict_file = reports_dirpath / 'move_conflicts.txt'
        with open(conflict_file, 'w') as f:
            f.write('\n'.join(conflict_report))
        print(f'Found {len(conflict_report)} conflicts. Saved to: {conflict_file}')
    
    if missing_report:
        missing_file = reports_dirpath / 'move_missing_paths.txt'
        with open(missing_file, 'w') as f:
            f.write('\n'.join(missing_report))
        print(f'Found {len(missing_report)} missing/skipped paths. Saved to: {missing_file}')
    
    return total_files_moved, total_bytes_moved


def main():
    args = parse_args()
    
    repository_dirpath = Path(args.repository_dirpath).resolve()
    target_dirpath = Path(args.target_dirpath).resolve()
    ignored_paths_filepath = Path(args.ignored_paths_filepath).resolve()
    
    # Create or use provided reports directory
    if args.reports_dirpath:
        reports_dirpath = Path(args.reports_dirpath).resolve()
    else:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        reports_dirpath = root_dirpath / 'data' / 'reports' / timestamp
    reports_dirpath.mkdir(parents=True, exist_ok=True)
    
    if args.verbose:
        print(f'Repository directory: {repository_dirpath}')
        print(f'Target directory: {target_dirpath}')
        print(f'Ignored paths file: {ignored_paths_filepath}')
        print(f'Reports directory: {reports_dirpath}')
        print()
    
    # Validate inputs
    if not ignored_paths_filepath.exists():
        raise FileNotFoundError(f'Ignored paths file not found: {ignored_paths_filepath}')
    
    target_dirpath.mkdir(parents=True, exist_ok=True)
    
    # Move paths
    files_moved, bytes_moved = move_ignored_paths(
        repository_dirpath, target_dirpath, ignored_paths_filepath, reports_dirpath, args.verbose
    )
    
    mb_moved = bytes_moved / (1024 * 1024)
    print(f'Moved {files_moved} files ({mb_moved:.2f} MB)')
    print(f'Reports saved to: {reports_dirpath}')
    return


def parse_args():
    parser = argparse.ArgumentParser(description='Move git-ignored paths to target directory')
    parser.add_argument('--repository_dirpath', required=True, help='Path to the repository')
    parser.add_argument('--target_dirpath', required=True, help='Target directory to move files to')
    parser.add_argument('--ignored_paths_filepath', required=True, help='File containing list of ignored paths')
    parser.add_argument('--reports_dirpath', help='Directory to save reports in (optional, will create timestamped if not provided)')
    parser.add_argument('--verbose', action='store_true')
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
