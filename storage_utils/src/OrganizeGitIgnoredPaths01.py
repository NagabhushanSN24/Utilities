#!/usr/bin/env python3
"""
Master script to organize git-ignored paths by listing, moving, and symlinking.

Orchestrates the complete workflow:
1. Lists git-ignored paths (excluding symlinks)
2. Moves them to target directory
3. Creates symlinks back to original locations
"""

import argparse
import datetime
import subprocess
import sys
import time
import traceback
from pathlib import Path

this_filepath = Path(__file__)
this_filename = this_filepath.stem
root_dirpath = this_filepath.parent.parent


def run_script(script_name, args_list, verbose=False):
    """
    Run a Python script with arguments.
    
    Args:
        script_name: Name of the script to run (without .py extension)
        args_list: List of command-line arguments
        verbose: Whether to print verbose output
        
    Returns:
        True if script succeeded, False otherwise
    """
    script_path = this_filepath.parent / f'{script_name}.py'
    
    if not script_path.exists():
        print(f'ERROR: Script not found: {script_path}')
        return False
    
    cmd = [sys.executable, str(script_path)] + args_list
    
    if verbose:
        print(f'Running: {" ".join(cmd)}')
    
    print(f'\n{"="*80}')
    print(f'Running {script_name}...')
    print(f'{"="*80}\n')
    
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print(f'\nERROR: {script_name} failed with exit code {result.returncode}')
        return False
    
    print(f'\n{script_name} completed successfully.\n')
    return True


def main():
    args = parse_args()
    
    repository_dirpath = Path(args.repository_dirpath).resolve()
    target_dirpath = Path(args.target_dirpath).resolve()
    
    # Create timestamped reports directory for this run
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    reports_dirpath = root_dirpath / 'data' / 'reports' / timestamp
    reports_dirpath.mkdir(parents=True, exist_ok=True)
    
    # Path for the ignored paths list
    ignored_paths_filepath = reports_dirpath / 'git_ignored_paths.txt'
    
    print(f'Repository directory: {repository_dirpath}')
    print(f'Target directory: {target_dirpath}')
    print(f'Reports directory: {reports_dirpath}')
    print(f'Ignored paths file: {ignored_paths_filepath}')
    print()
    
    # Validate target directory
    target_dirpath.mkdir(parents=True, exist_ok=True)
    
    # Step 1: List git-ignored paths
    list_args = [
        '--repository_dirpath', str(repository_dirpath),
        '--reports_dirpath', str(reports_dirpath)
    ]
    if args.verbose:
        list_args.append('--verbose')
    
    if not run_script('ListGitIgnoredPaths04', list_args, args.verbose):
        print('ERROR: Failed to list git-ignored paths.')
        return False
    
    # The file should now be in the reports directory
    if not ignored_paths_filepath.exists():
        print(f'ERROR: Expected output file not found: {ignored_paths_filepath}')
        return False
    
    # Step 2: Move git-ignored paths to target directory
    move_args = [
        '--repository_dirpath', str(repository_dirpath),
        '--target_dirpath', str(target_dirpath),
        '--ignored_paths_filepath', str(ignored_paths_filepath),
        '--reports_dirpath', str(reports_dirpath)
    ]
    if args.verbose:
        move_args.append('--verbose')
    
    if not run_script('MoveGitIgnoredPaths01', move_args, args.verbose):
        print('ERROR: Failed to move git-ignored paths.')
        return False
    
    # Step 3: Create symlinks
    symlink_args = [
        '--repository_dirpath', str(repository_dirpath),
        '--target_dirpath', str(target_dirpath),
        '--ignored_paths_filepath', str(ignored_paths_filepath),
        '--reports_dirpath', str(reports_dirpath)
    ]
    if args.verbose:
        symlink_args.append('--verbose')
    
    if not run_script('SymlinkGitIgnoredPaths01', symlink_args, args.verbose):
        print('ERROR: Failed to create symlinks.')
        return False
    
    print(f'\n{"="*80}')
    print('WORKFLOW COMPLETED SUCCESSFULLY')
    print(f'{"="*80}')
    print(f'\nAll reports saved to: {reports_dirpath}')
    print(f'Ignored paths list: {ignored_paths_filepath}')
    print('\nNext steps:')
    print('1. Review conflict reports (if any) in the reports directory')
    print('2. Manually resolve any conflicts')
    print('3. Verify that symlinks are working correctly')
    print('4. Test your code to ensure nothing is broken')
    
    return True


def parse_args():
    parser = argparse.ArgumentParser(
        description='Organize git-ignored paths by listing, moving, and symlinking',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Example usage:
  python OrganizeGitIgnoredPaths01.py --repository_dirpath /path/to/repo --target_dirpath /path/to/archive
  python OrganizeGitIgnoredPaths01.py --repository_dirpath /path/to/repo --target_dirpath /path/to/archive --verbose
        '''
    )
    parser.add_argument('--repository_dirpath', required=True, help='Path to the repository to analyze')
    parser.add_argument('--target_dirpath', required=True, help='Target directory to move files to')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    print('='*80)
    print('GIT IGNORED PATHS ORGANIZER')
    print('='*80)
    print('Program started at ' + datetime.datetime.now().strftime('%d/%m/%Y %I:%M:%S %p'))
    start_time = time.time()
    
    try:
        success = main()
        if success:
            run_result = 'Program completed successfully!'
        else:
            run_result = 'Program completed with errors.'
            sys.exit(1)
    except Exception as e:
        print(e)
        traceback.print_exc()
        run_result = 'Error: ' + str(e)
        sys.exit(1)
    
    end_time = time.time()
    print('\n' + '='*80)
    print('Program ended at ' + datetime.datetime.now().strftime('%d/%m/%Y %I:%M:%S %p'))
    print('Execution time: ' + str(datetime.timedelta(seconds=end_time - start_time)))
    print('='*80)
