#!/usr/bin/env python3
"""
Create individual file symlinks for git-ignored paths that have been moved to target directory.
Extended from SymlinkGitIgnoredPaths01.py with granular file-level symlinking.

Creates individual file symlinks in the original repository locations pointing to the 
moved files in the target directory. When a directory is listed, recursively creates
symlinks for all files within it. Validates existing symlinks and reports conflicts.
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


def create_directory_symlinks_recursive(source_dir, target_dir, conflict_report, missing_report, verbose=False):
    """
    Recursively create individual file symlinks for all files in target directory.
    
    Args:
        source_dir: Directory path in repository where symlinks should be created
        target_dir: Directory path in target where actual files are located
        conflict_report: List to append conflict messages
        missing_report: List to append missing path messages
        verbose: Whether to print verbose output
        
    Returns:
        Number of symlinks created
    """
    symlinks_created = 0
    
    # Check if target directory exists
    if not target_dir.exists():
        msg = f'Target directory does not exist: {target_dir}'
        missing_report.append(msg)
        if verbose:
            print(f'  WARNING: {msg}')
        return 0
    
    # Recursively walk through target directory
    try:
        for target_item in target_dir.rglob('*'):
            # Only create symlinks for files, not directories
            if target_item.is_file() and not target_item.is_symlink():
                # Calculate relative path from target_dir
                rel_path = target_item.relative_to(target_dir)
                
                # Calculate corresponding source path
                source_item = source_dir / rel_path
                
                # Create symlink
                if create_symlink(source_item, target_item, conflict_report, missing_report, verbose):
                    symlinks_created += 1
    except (PermissionError, OSError) as e:
        msg = f'Error accessing target directory {target_dir}: {e}'
        missing_report.append(msg)
        if verbose:
            print(f'  ERROR: {msg}')
    
    return symlinks_created


def symlink_ignored_paths(repository_dirpath, target_dirpath, ignored_paths_filepath, reports_dirpath, verbose=False):
    """
    Create individual file symlinks for all ignored paths.
    
    Args:
        repository_dirpath: Root directory of the repository
        target_dirpath: Directory where files were moved to
        ignored_paths_filepath: Path to file containing ignored paths
        reports_dirpath: Directory to save reports in
        verbose: Whether to print verbose output
        
    Returns:
        Number of symlinks created
    """
    print('Loading ignored paths...')
    ignored_paths = load_ignored_paths(ignored_paths_filepath, verbose)
    
    conflict_report = []
    missing_report = []
    symlinks_created = 0
    
    print(f'Creating individual file symlinks for {len(ignored_paths)} paths...')
    
    for i, relative_path in enumerate(ignored_paths, 1):
        if verbose or i % 100 == 0:
            print(f'Processing {i}/{len(ignored_paths)}: {relative_path}')
        
        is_directory = relative_path.endswith('/')
        clean_path = relative_path.rstrip('/')
        
        source_path = repository_dirpath / clean_path
        target_path = target_dirpath / clean_path
        
        if is_directory:
            # Create individual file symlinks for all files in directory
            if verbose:
                print(f'  Processing directory: {relative_path}')
            created = create_directory_symlinks_recursive(
                source_path, target_path, conflict_report, missing_report, verbose
            )
            symlinks_created += created
            if verbose and created > 0:
                print(f'  Created {created} file symlinks in directory')
        else:
            # Single file - create one symlink
            if create_symlink(source_path, target_path, conflict_report, missing_report, verbose):
                symlinks_created += 1
    
    # Save reports
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
    
    return symlinks_created


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
    
    if not target_dirpath.exists():
        raise FileNotFoundError(f'Target directory not found: {target_dirpath}')
    
    # Create symlinks
    symlinks_created = symlink_ignored_paths(
        repository_dirpath, target_dirpath, ignored_paths_filepath, reports_dirpath, args.verbose
    )
    
    print(f'Created/verified {symlinks_created} individual file symlinks')
    print(f'Reports saved to: {reports_dirpath}')
    return


def parse_args():
    parser = argparse.ArgumentParser(description='Create individual file symlinks for moved git-ignored paths')
    parser.add_argument('--repository_dirpath', required=True, help='Path to the repository')
    parser.add_argument('--target_dirpath', required=True, help='Target directory where files were moved to')
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
