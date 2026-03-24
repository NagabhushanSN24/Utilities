#!/usr/bin/env python3
"""
Generate a list of git-ignored paths excluding symlinks.
Extended from GenerateGitIgnoredPaths03.py with symlink filtering.

Recursively discovers and processes git-ignored paths in the main repository
and all its submodules, excluding any paths that are symlinks.
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


def get_ignored_paths_single_repo(repo_root, exclude_patterns, exclude_root_paths, relative_prefix='', verbose=False):
    """
    Get git-ignored paths for a single repository (no submodule traversal).
    
    Args:
        repo_root: Path to the git repository root
        exclude_patterns: List of patterns to exclude from results (matches anywhere)
        exclude_root_paths: List of paths to exclude only at main repository root
        relative_prefix: Prefix to add to all paths (for submodules)
        verbose: Whether to print verbose output
        
    Returns:
        Set of ignored paths with relative_prefix applied
    """
    
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
        original_path = path.strip()
        is_directory = original_path.endswith('/')
        path = original_path.rstrip('/')
        
        if path:
            # Check exclude patterns (match anywhere)
            excluded = False
            for pattern in exclude_patterns:
                if pattern in path:
                    excluded = True
                    break
            
            # Check root paths (only applied when list is not empty)
            if not excluded:
                for root_path in exclude_root_paths:
                    if path.startswith(root_path.strip('/')):
                        excluded = True
                        break
            
            if not excluded:
                # Add prefix for submodules
                if relative_prefix:
                    full_path = f"{relative_prefix}/{path}"
                else:
                    full_path = path
                
                # Add trailing slash only for directories
                if is_directory:
                    full_path += '/'
                
                ignored_paths.add(full_path)
    
    if verbose:
        print(f'    Found {len(ignored_paths)} ignored paths')
    
    return ignored_paths


def filter_symlinks(paths, base_path, verbose=False):
    """
    Filter out paths that are symlinks.
    
    Args:
        paths: Iterable of path strings (relative to base_path)
        base_path: Base path to resolve relative paths against
        verbose: Whether to print verbose output
        
    Returns:
        Set of paths that are not symlinks
    """
    if verbose:
        print('Filtering out symlinks...')
    
    non_symlink_paths = set()
    symlink_count = 0
    
    for path_str in paths:
        # Remove trailing slash for proper path resolution
        clean_path = path_str.rstrip('/')
        full_path = base_path / clean_path
        
        # Check if path is a symlink
        # Use lexists() to handle broken symlinks correctly
        if full_path.exists() or full_path.is_symlink():
            if full_path.is_symlink():
                symlink_count += 1
                if verbose:
                    print(f'  Skipping symlink: {path_str}')
                continue
        
        non_symlink_paths.add(path_str)
    
    if verbose:
        print(f'Filtered out {symlink_count} symlinks')
    
    return non_symlink_paths


def get_ignored_paths_recursive(repo_root, exclude_patterns, exclude_root_paths, exclude_submodules, verbose=False):
    """
    Recursively get all git-ignored paths including submodules, excluding symlinks.
    
    Args:
        repo_root: Path to the git repository root
        exclude_patterns: List of patterns to exclude from results (matches anywhere)
        exclude_root_paths: List of paths to exclude only at main repository root
        exclude_submodules: List of submodule paths to skip entirely
        verbose: Whether to print verbose output
        
    Returns:
        List of ignored paths (sorted, with redundant child paths removed, no symlinks)
    """
    print(f'Searching for git-ignored paths in: {repo_root}')
    
    all_ignored_paths = set()
    
    # Get ignored paths from main repository
    print('Running git ls-files command on main repository...')
    main_ignored = get_ignored_paths_single_repo(repo_root, exclude_patterns, exclude_root_paths, '', verbose)
    all_ignored_paths.update(main_ignored)
    
    # Get submodules
    submodules = get_submodules(repo_root, verbose)
    
    if submodules:
        print(f'Processing {len(submodules)} submodules...')
        for submodule_path in submodules:
            # Skip excluded submodules
            if submodule_path in exclude_submodules:
                if verbose:
                    print(f'  Skipping excluded submodule: {submodule_path}')
                continue
            
            submodule_full_path = repo_root / submodule_path
            if verbose:
                print(f'  Processing submodule: {submodule_path}')
            
            submodule_ignored = get_ignored_paths_single_repo(
                submodule_full_path,
                exclude_patterns,
                [],  # Don't apply root path exclusions to submodules
                relative_prefix=submodule_path,
                verbose=verbose
            )
            all_ignored_paths.update(submodule_ignored)
    
    print(f'Git ls-files command completed for all repositories.')
    if verbose:
        print(f'Total paths before filtering: {len(all_ignored_paths)}')
    
    # Filter out symlinks
    all_ignored_paths = filter_symlinks(all_ignored_paths, repo_root, verbose)
    
    if verbose:
        print(f'Total paths after symlink filtering: {len(all_ignored_paths)}')
    
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

    # Get repository directory path
    repository_dirpath = Path(args.repository_dirpath).resolve()

    # Patterns to exclude from git-ignored paths (matches anywhere in any repo)
    exclude_patterns = ['.idea', '.git', '__pycache__', 'build', 'egg-info', 'tmp']
    
    # Paths to exclude only at main repository root (not in submodules)
    exclude_root_paths = ['releases/code_releases', 'workspace/utilities/004_StorageAnalysis/data']
    
    # Submodules to skip entirely (will not process ignored files from these)
    exclude_submodules = ['workspace/clothing_humans/literature/011_GarmentCode/NvidiaWarp-GarmentCode']

    # Use provided reports directory or default
    if args.reports_dirpath:
        output_dirpath = Path(args.reports_dirpath).resolve()
    else:
        output_dirpath = root_dirpath / 'data/reports'
    output_dirpath.mkdir(parents=True, exist_ok=True)
    output_file = output_dirpath / 'git_ignored_paths.txt'

    if args.verbose:
        print(f'Repository directory: {repository_dirpath}')
        print(f'Output directory: {output_dirpath}')
        print(f'Exclude patterns (anywhere): {exclude_patterns}')
        print(f'Exclude root paths (main repo only): {exclude_root_paths}')
        print(f'Exclude submodules: {exclude_submodules}')
        print()
    
    ignored_paths = get_ignored_paths_recursive(repository_dirpath, exclude_patterns, exclude_root_paths, exclude_submodules, verbose=args.verbose)
    
    if args.verbose:
        print()
        print(f'Writing to file: {output_file}')
    
    with open(output_file, 'w') as f:
        for path in ignored_paths:
            f.write(path + '\n')
    
    print(f"Found {len(ignored_paths)} ignored paths (excluding symlinks)")
    print(f"Written to {output_file}")
    return


def parse_args():
    parser = argparse.ArgumentParser(description='List git-ignored paths excluding symlinks')
    parser.add_argument('--repository_dirpath', required=True, help='Path to the repository to analyze')
    parser.add_argument('--reports_dirpath', help='Directory to save reports in (optional, defaults to data/reports)')
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
