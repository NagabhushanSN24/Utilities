#!/usr/bin/env python3
"""
Generate a list of git-ignored paths including submodules (extended version).
Extended from GenerateGitIgnoredPaths02.py with submodule support.

Recursively discovers and processes git-ignored paths in the main repository
and all its submodules.
"""

import argparse
import datetime
import subprocess
import time
import traceback
from pathlib import Path

this_filepath = Path(__file__)
this_filename = this_filepath.stem
root_dirpath = this_filepath.parent.parent
project_dirpath = this_filepath.parent.parent.parent.parent.parent


def get_submodules(repo_root, verbose=False):
    """
    Get all submodule paths in the repository.
    
    Args:
        repo_root: Path to the git repository root
        verbose: Whether to print verbose output
        
    Returns:
        List of submodule paths relative to repo_root
    """
    if verbose:
        print('Discovering submodules...')
    
    result = subprocess.run(
        ['git', 'config', '--file', '.gitmodules', '--get-regexp', 'path'],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    
    submodules = []
    if result.returncode == 0 and result.stdout:
        for line in result.stdout.splitlines():
            # Format: submodule.<name>.path <path>
            parts = line.split()
            if len(parts) >= 2:
                submodule_path = parts[1]
                # Check if submodule is actually initialized
                submodule_full_path = repo_root / submodule_path
                if (submodule_full_path / '.git').exists() or (submodule_full_path / '.git').is_file():
                    submodules.append(submodule_path)
    
    if verbose:
        print(f'Found {len(submodules)} initialized submodules')
    
    return submodules


def get_ignored_paths_single_repo(repo_root, relative_prefix='', verbose=False):
    """
    Get git-ignored paths for a single repository (no submodule traversal).
    
    Args:
        repo_root: Path to the git repository root
        relative_prefix: Prefix to add to all paths (for submodules)
        verbose: Whether to print verbose output
        
    Returns:
        Set of ignored paths with relative_prefix applied
    """
    exclude_patterns = ['.idea', '.git', '__pycache__', '/releases']
    
    if verbose:
        repo_name = relative_prefix if relative_prefix else 'main repository'
        print(f'  Checking: {repo_name}')
    
    result = subprocess.run(
        ['git', 'ls-files', '--others', '--ignored', '--exclude-standard', '--directory'],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    
    ignored_paths = set()
    for path in result.stdout.splitlines():
        path = path.strip().rstrip('/')
        if path and not any(pattern in path for pattern in exclude_patterns):
            # Add prefix for submodules
            if relative_prefix:
                full_path = f"{relative_prefix}/{path}"
            else:
                full_path = path
            ignored_paths.add(full_path + ('/' if full_path else ''))
    
    if verbose:
        print(f'    Found {len(ignored_paths)} ignored paths')
    
    return ignored_paths


def get_ignored_paths_recursive(repo_root, verbose=False):
    """
    Recursively get all git-ignored paths including submodules.
    
    Args:
        repo_root: Path to the git repository root
        verbose: Whether to print verbose output
        
    Returns:
        List of ignored paths (sorted, with redundant child paths removed)
    """
    print(f'Searching for git-ignored paths in: {repo_root}')
    
    all_ignored_paths = set()
    
    # Get ignored paths from main repository
    print('Running git ls-files command on main repository...')
    main_ignored = get_ignored_paths_single_repo(repo_root, '', verbose)
    all_ignored_paths.update(main_ignored)
    
    # Get submodules
    submodules = get_submodules(repo_root, verbose)
    
    if submodules:
        print(f'Processing {len(submodules)} submodules...')
        for submodule_path in submodules:
            submodule_full_path = repo_root / submodule_path
            if verbose:
                print(f'  Processing submodule: {submodule_path}')
            
            submodule_ignored = get_ignored_paths_single_repo(
                submodule_full_path,
                relative_prefix=submodule_path,
                verbose=verbose
            )
            all_ignored_paths.update(submodule_ignored)
    
    print(f'Git ls-files command completed for all repositories.')
    if verbose:
        print(f'Total paths before deduplication: {len(all_ignored_paths)}')
    
    # Remove child paths if parent is already included
    print('Removing redundant child paths...')
    
    final_paths = set()
    sorted_paths = sorted(all_ignored_paths, key=lambda p: p.count('/'))
    
    for path in sorted_paths:
        # Check if this path is a child of any already-added parent
        is_child = any(path.startswith(parent) and path != parent
                      for parent in final_paths)
        if not is_child:
            final_paths.add(path)
    
    print('Removed redundant child paths.')
    if verbose:
        print(f'Final paths after deduplication: {len(final_paths)}')
    
    return sorted(final_paths)


def main():
    args = parse_args()

    output_dirpath = root_dirpath / 'data/reports'
    output_dirpath.mkdir(parents=True, exist_ok=True)
    output_file = output_dirpath / 'git_ignored_paths.txt'

    if args.verbose:
        print(f'Project directory: {project_dirpath}')
        print(f'Output directory: {output_dirpath}')
        print()
    
    ignored_paths = get_ignored_paths_recursive(project_dirpath, verbose=args.verbose)
    
    if args.verbose:
        print()
        print(f'Writing to file: {output_file}')
    
    with open(output_file, 'w') as f:
        for path in ignored_paths:
            f.write(path + '\n')
    
    print(f"Found {len(ignored_paths)} ignored paths (including submodules)")
    print(f"Written to {output_file}")
    return


def parse_args():
    parser = argparse.ArgumentParser()
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
