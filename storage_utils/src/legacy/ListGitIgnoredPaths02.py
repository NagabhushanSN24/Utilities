#!/usr/bin/env python3
"""
Generate a list of git-ignored paths (optimized version).
Extended from GenerateGitIgnoredPaths01.py and optimized.

Uses git ls-files for direct extraction of ignored paths.
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


def get_ignored_paths(repo_root, verbose=False):
    """
    Efficiently get all git-ignored paths using git ls-files.
    
    Args:
        repo_root: Path to the git repository root
        verbose: Whether to print verbose output
        
    Returns:
        List of ignored paths (sorted, with redundant child paths removed)
    """
    exclude_patterns = ['.idea', '.git', '__pycache__', '/releases']

    print(f'Searching for git-ignored paths in: {repo_root}')
    if verbose:
        print(f'Exclude patterns: {exclude_patterns}')

    # Get all ignored files and directories in one command
    # --others: untracked files
    # --ignored: show ignored files
    # --exclude-standard: use .gitignore rules
    # --directory: show directories instead of listing contents
    print('Running git ls-files command...')

    result = subprocess.run(
        ['git', 'ls-files', '--others', '--ignored', '--exclude-standard', '--directory'],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )

    print(f'Git ls-files command completed.')
    if verbose:
        print(f'Raw output lines: {len(result.stdout.splitlines())}')

    print('Filtering excluded dirctories from ignored paths.')

    ignored_paths = set()
    for path in result.stdout.splitlines():
        path = path.strip().rstrip('/')
        if path and not any(pattern in path for pattern in exclude_patterns):
            ignored_paths.add(path + ('/' if path else ''))

    print('Filtering complete.')
    if verbose:
        print(f'Paths after filtering: {len(ignored_paths)}')

    # Remove child paths if parent is already included
    print('Removing redundant child paths...')

    final_paths = set()
    sorted_paths = sorted(ignored_paths, key=lambda p: p.count('/'))

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
    
    ignored_paths = get_ignored_paths(project_dirpath, verbose=args.verbose)
    
    if args.verbose:
        print()
        print(f'Writing to file: {output_file}')
    
    with open(output_file, 'w') as f:
        for path in ignored_paths:
            f.write(path + '\n')
    
    print(f"Found {len(ignored_paths)} ignored paths")
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
