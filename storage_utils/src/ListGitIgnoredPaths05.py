#!/usr/bin/env python3
"""
Generate a list of git-ignored paths with intelligent symlink handling.
Extended from ListGitIgnoredPaths04.py with recursive mixed-content detection.

Features:
- Filters out directories containing only symlinks
- Expands directories with mixed content (symlinks + real files) to list only real files
- Keeps directories with only real files as compact directory entries
- Recursively analyzes directory contents for optimal readability
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


def analyze_directory_contents(dir_path, verbose=False):
    """
    Recursively analyze directory to determine content type.
    
    Args:
        dir_path: Path to directory to analyze
        verbose: Whether to print verbose output
        
    Returns:
        Tuple of (has_real_files, has_symlinks, real_file_paths)
        - has_real_files: True if directory contains any real files/dirs (recursively)
        - has_symlinks: True if directory contains any symlinks (recursively)
        - real_file_paths: List of paths to real files (relative to dir_path)
    """
    has_real_files = False
    has_symlinks = False
    real_file_paths = []
    
    if not dir_path.exists():
        return False, False, []
    
    # Use rglob to recursively find all items
    try:
        for item in dir_path.rglob('*'):
            if item.is_symlink():
                has_symlinks = True
            else:
                # It's a real file or directory
                if item.is_file():
                    has_real_files = True
                    # Store path relative to dir_path
                    rel_path = item.relative_to(dir_path)
                    real_file_paths.append(str(rel_path))
                elif item.is_dir():
                    # Directory itself doesn't count, but we continue to check its contents
                    pass
    except (PermissionError, OSError) as e:
        if verbose:
            print(f'  Warning: Cannot access {dir_path}: {e}')
        # Assume it has real files to be safe
        return True, False, []
    
    return has_real_files, has_symlinks, real_file_paths


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
                
                # Handle directories with intelligent symlink detection
                if is_directory:
                    dir_full_path = repo_root / path
                    has_real, has_symlinks, real_files = analyze_directory_contents(dir_full_path, verbose)
                    
                    if not has_real and has_symlinks:
                        # Directory contains only symlinks - skip it
                        if verbose:
                            print(f'    Skipping directory with only symlinks: {full_path}')
                        continue
                    elif has_real and has_symlinks:
                        # Mixed content - expand to individual real files
                        if verbose:
                            print(f'    Expanding mixed directory: {full_path} ({len(real_files)} real files)')
                        for real_file in real_files:
                            real_file_full = f"{full_path}/{real_file}"
                            ignored_paths.add(real_file_full)
                    else:
                        # Only real files (or empty) - keep as directory
                        ignored_paths.add(full_path + '/')
                else:
                    # Individual file - check if it's a symlink
                    file_full_path = repo_root / path
                    if file_full_path.exists() or file_full_path.is_symlink():
                        if file_full_path.is_symlink():
                            if verbose:
                                print(f'    Skipping symlink file: {full_path}')
                            continue
                    ignored_paths.add(full_path)
    
    if verbose:
        print(f'    Found {len(ignored_paths)} ignored paths')
    
    return ignored_paths


def get_ignored_paths_recursive(repo_root, exclude_patterns, exclude_root_paths, exclude_submodules, verbose=False):
    """
    Recursively get all git-ignored paths including submodules, with intelligent symlink handling.
    
    Args:
        repo_root: Path to the git repository root
        exclude_patterns: List of patterns to exclude from results (matches anywhere)
        exclude_root_paths: List of paths to exclude only at main repository root
        exclude_submodules: List of submodule paths to skip entirely
        verbose: Whether to print verbose output
        
    Returns:
        List of ignored paths (sorted, with redundant child paths removed)
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
        print(f'Total paths after intelligent filtering: {len(all_ignored_paths)}')
    
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
    
    print(f"Found {len(ignored_paths)} ignored paths (with intelligent symlink handling)")
    print(f"Written to {output_file}")
    return


def parse_args():
    parser = argparse.ArgumentParser(description='List git-ignored paths with intelligent symlink handling')
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
