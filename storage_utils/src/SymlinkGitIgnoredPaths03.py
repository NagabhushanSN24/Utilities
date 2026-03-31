#!/usr/bin/env python3
"""
Create individual file symlinks for git-ignored paths that have been moved to target directory.
Extended from SymlinkGitIgnoredPaths02.py with optional paths file support.

Two modes of operation:
1. With ignored_paths_filepath: Creates symlinks based on paths listed in file (traceability mode)
2. Without ignored_paths_filepath: Scans target directory and creates symlinks for all files (sync mode)

Both modes create individual file-level symlinks and validate existing symlinks.
"""

import argparse
import datetime
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


def create_symlink(source_path, target_path, conflict_report, missing_report, verbose=False):
    """
    Create a symlink from source to target, checking for conflicts.
    
    Args:
        source_path: Path where symlink should be created
        target_path: Path that symlink should point to
        conflict_report: List to append conflict messages
        missing_report: List to append missing path messages
        verbose: Whether to print verbose output
        
    Returns:
        True if symlink was created or already correct, False otherwise
    """
    # Check if target exists
    if not target_path.exists() and not target_path.is_symlink():
        msg = f'Target does not exist: {target_path} (cannot create symlink at {source_path})'
        missing_report.append(msg)
        if verbose:
            print(f'  WARNING: {msg}')
        return False
    
    # Check what exists at source location
    if source_path.is_symlink():
        # Symlink already exists - check if it's correct
        existing_target = source_path.readlink()
        
        # Resolve to absolute paths for comparison
        existing_target_resolved = (source_path.parent / existing_target).resolve()
        expected_target_resolved = target_path.resolve()
        
        if existing_target_resolved == expected_target_resolved:
            if verbose:
                print(f'  Symlink already correct: {source_path} -> {target_path}')
            return True
        else:
            msg = f'Incorrect symlink: {source_path} -> {existing_target} (expected -> {target_path})'
            conflict_report.append(msg)
            if verbose:
                print(f'  CONFLICT: {msg}')
            return False
    
    elif source_path.exists():
        # File or directory exists at source location
        if source_path.is_file():
            msg = f'File exists at symlink location: {source_path} (cannot create symlink to {target_path})'
        else:
            msg = f'Directory exists at symlink location: {source_path} (cannot create symlink to {target_path})'
        conflict_report.append(msg)
        if verbose:
            print(f'  CONFLICT: {msg}')
        return False
    
    else:
        # Nothing exists at source - create symlink
        if verbose:
            print(f'  Creating symlink: {source_path} -> {target_path}')
        
        # Create parent directory if needed
        source_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create symlink
        source_path.symlink_to(target_path)
        return True


def get_files_from_paths_file(repository_dirpath, target_dirpath, ignored_paths_filepath, verbose=False):
    """
    Mode 1: Read paths from file and expand to file tuples.
    
    Args:
        repository_dirpath: Root directory of the repository
        target_dirpath: Directory where files were moved to
        ignored_paths_filepath: Path to file containing ignored paths
        verbose: Whether to print verbose output
        
    Returns:
        List of (source_path, target_path) tuples for each file
    """
    paths = load_ignored_paths(ignored_paths_filepath, verbose)
    file_tuples = []
    
    if verbose:
        print(f'Expanding {len(paths)} paths to individual files...')
    
    for relative_path in paths:
        if relative_path.endswith('/'):
            # Directory: scan target to expand to individual files
            clean_path = relative_path.rstrip('/')
            target_dir = target_dirpath / clean_path
            
            if target_dir.exists():
                for target_file in target_dir.rglob('*'):
                    if target_file.is_file() and not target_file.is_symlink():
                        rel_path = target_file.relative_to(target_dirpath)
                        source_file = repository_dirpath / rel_path
                        file_tuples.append((source_file, target_file))
            elif verbose:
                print(f'  Warning: Directory not found in target: {clean_path}')
        else:
            # Individual file: create direct tuple
            source_file = repository_dirpath / relative_path
            target_file = target_dirpath / relative_path
            file_tuples.append((source_file, target_file))
    
    if verbose:
        print(f'Expanded to {len(file_tuples)} individual files')
    
    return file_tuples


def get_files_from_target_scan(repository_dirpath, target_dirpath, verbose=False):
    """
    Mode 2: Scan entire target directory for all files.
    
    Args:
        repository_dirpath: Root directory of the repository
        target_dirpath: Directory where files were moved to
        verbose: Whether to print verbose output
        
    Returns:
        List of (source_path, target_path) tuples for each file
    """
    file_tuples = []
    
    if verbose:
        print(f'Scanning target directory for all files: {target_dirpath}')
    
    for target_file in target_dirpath.rglob('*'):
        if target_file.is_file() and not target_file.is_symlink():
            rel_path = target_file.relative_to(target_dirpath)
            source_file = repository_dirpath / rel_path
            file_tuples.append((source_file, target_file))
    
    if verbose:
        print(f'Found {len(file_tuples)} files in target directory')
    
    return file_tuples


def collect_file_tuples(repository_dirpath, target_dirpath, ignored_paths_filepath, verbose=False):
    """
    Router function: decides mode and collects files to symlink.
    
    Args:
        repository_dirpath: Root directory of the repository
        target_dirpath: Directory where files were moved to
        ignored_paths_filepath: Optional path to file containing ignored paths
        verbose: Whether to print verbose output
        
    Returns:
        List of (source_path, target_path) tuples for each file
    """
    if ignored_paths_filepath:
        if verbose:
            print(f'Mode: Using paths from file: {ignored_paths_filepath}')
        file_tuples = get_files_from_paths_file(
            repository_dirpath, target_dirpath, ignored_paths_filepath, verbose
        )
    else:
        if verbose:
            print('Mode: Scanning target directory for all files')
        file_tuples = get_files_from_target_scan(
            repository_dirpath, target_dirpath, verbose
        )
    
    return file_tuples


def save_reports(conflict_report, missing_report, reports_dirpath):
    """
    Save conflict and missing reports to files.
    
    Args:
        conflict_report: List of conflict messages
        missing_report: List of missing path messages
        reports_dirpath: Directory to save reports in
    """
    if conflict_report:
        conflict_file = reports_dirpath / 'symlink_conflicts.txt'
        with open(conflict_file, 'w') as f:
            f.write('\n'.join(conflict_report))
        print(f'Found {len(conflict_report)} conflicts. Saved to: {conflict_file}')
    
    if missing_report:
        missing_file = reports_dirpath / 'symlink_missing_targets.txt'
        with open(missing_file, 'w') as f:
            f.write('\n'.join(missing_report))
        print(f'Found {len(missing_report)} missing targets. Saved to: {missing_file}')


def symlink_all_files(file_tuples, reports_dirpath, verbose=False):
    """
    Unified execution: create symlinks for all file tuples.
    Works identically regardless of input mode.
    
    Args:
        file_tuples: List of (source_path, target_path) tuples
        reports_dirpath: Directory to save reports in
        verbose: Whether to print verbose output
        
    Returns:
        Number of symlinks created
    """
    conflict_report = []
    missing_report = []
    symlinks_created = 0
    
    total = len(file_tuples)
    print(f'Creating symlinks for {total} files...')
    
    for i, (source_path, target_path) in enumerate(file_tuples, 1):
        if verbose or i % 100 == 0:
            print(f'  [{i}/{total}] {source_path.name}')
        
        if create_symlink(source_path, target_path, conflict_report, missing_report, verbose):
            symlinks_created += 1
    
    # Save reports
    save_reports(conflict_report, missing_report, reports_dirpath)
    
    return symlinks_created


def main():
    args = parse_args()
    
    # Setup paths
    repository_dirpath = Path(args.repository_dirpath).resolve()
    target_dirpath = Path(args.target_dirpath).resolve()
    ignored_paths_filepath = (Path(args.ignored_paths_filepath).resolve() 
                             if args.ignored_paths_filepath else None)
    
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
        print(f'Ignored paths file: {ignored_paths_filepath or "Not provided (scan mode)"}')
        print(f'Reports directory: {reports_dirpath}')
        print()
    
    # Validate inputs
    if ignored_paths_filepath and not ignored_paths_filepath.exists():
        raise FileNotFoundError(f'Ignored paths file not found: {ignored_paths_filepath}')
    
    if not target_dirpath.exists():
        raise FileNotFoundError(f'Target directory not found: {target_dirpath}')
    
    # Collect files to symlink (mode decision happens here)
    file_tuples = collect_file_tuples(
        repository_dirpath, target_dirpath, ignored_paths_filepath, args.verbose
    )
    
    if not file_tuples:
        print('No files found to symlink.')
        return
    
    # Create symlinks (identical for both modes)
    symlinks_created = symlink_all_files(file_tuples, reports_dirpath, args.verbose)
    
    print(f'\nCreated/verified {symlinks_created} individual file symlinks')
    print(f'Reports saved to: {reports_dirpath}')
    return


def parse_args():
    parser = argparse.ArgumentParser(
        description='Create individual file symlinks for moved git-ignored paths',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Two modes of operation:

1. Traceability mode (with --ignored_paths_filepath):
   Reads paths from file and creates symlinks only for those paths.
   Used by OrganizeGitIgnoredPaths for audit trail.
   
2. Sync mode (without --ignored_paths_filepath):
   Scans entire target directory and creates symlinks for all files found.
   Useful for standalone operation or fixing broken symlinks.

Examples:
  # Traceability mode (with orchestrator)
  python SymlinkGitIgnoredPaths03.py --repository_dirpath /path/to/repo 
         --target_dirpath /path/to/archive --ignored_paths_filepath paths.txt
  
  # Sync mode (standalone)
  python SymlinkGitIgnoredPaths03.py --repository_dirpath /path/to/repo 
         --target_dirpath /path/to/archive
        '''
    )
    parser.add_argument('--repository_dirpath', required=True, 
                       help='Path to the repository')
    parser.add_argument('--target_dirpath', required=True, 
                       help='Target directory where files were moved to')
    parser.add_argument('--ignored_paths_filepath', required=False, 
                       help='File containing list of ignored paths (optional; if omitted, scans target)')
    parser.add_argument('--reports_dirpath', 
                       help='Directory to save reports in (optional, will create timestamped if not provided)')
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
