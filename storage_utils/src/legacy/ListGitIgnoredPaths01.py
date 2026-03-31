#!/usr/bin/env python3
"""
Generate a list of git-ignored paths (directories only).

This script uses find + git check-ignore to efficiently identify ignored directories.
"""

import subprocess
from pathlib import Path


def get_ignored_directories(repo_root):
    """
    Efficiently get all git-ignored directories using find and git check-ignore.
    
    Args:
        repo_root: Path to the git repository root
        
    Returns:
        Set of ignored directory paths
    """
    exclude_patterns = ['.idea', '.git', '__pycache__']
    
    # Find all directories, exclude .git itself
    find_cmd = ['find', '.', '-type', 'd', '-not', '-path', './.git/*', '-not', '-path', './.git']
    
    find_result = subprocess.run(
        find_cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    
    directories = [d.lstrip('./') for d in find_result.stdout.splitlines() if d != '.']
    
    # Check which directories are ignored
    ignored_dirs = set()
    batch_size = 10000
    
    for i in range(0, len(directories), batch_size):
        batch = directories[i:i+batch_size]
        
        # Use git check-ignore to see which directories are ignored
        check_result = subprocess.run(
            ['git', 'check-ignore'] + batch,
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        
        if check_result.stdout:
            for path in check_result.stdout.splitlines():
                path = path.strip()
                if path:
                    # Filter out unwanted patterns
                    if not any(pattern in path for pattern in exclude_patterns):
                        ignored_dirs.add(path + ('/' if not path.endswith('/') else ''))
    
    # Remove child directories if parent is already included
    final_dirs = set()
    sorted_dirs = sorted(ignored_dirs, key=lambda p: p.count('/'))
    
    for dir_path in sorted_dirs:
        is_child = any(dir_path.startswith(parent) for parent in final_dirs)
        if not is_child:
            final_dirs.add(dir_path)
    
    # Also check for individual ignored files in non-ignored directories
    find_files = subprocess.run(
        ['find', '.', '-type', 'f'],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True
    )
    
    files = [f.lstrip('./') for f in find_files.stdout.splitlines()]
    
    ignored_files = set()
    for i in range(0, len(files), batch_size):
        batch = files[i:i+batch_size]
        check_result = subprocess.run(
            ['git', 'check-ignore'] + batch,
            cwd=repo_root,
            capture_output=True,
            text=True
        )
        
        if check_result.stdout:
            for path in check_result.stdout.splitlines():
                path = path.strip()
                if path and not any(pattern in path for pattern in exclude_patterns):
                    # Only add if not already covered by a directory
                    if not any(path.startswith(d) for d in final_dirs):
                        ignored_files.add(path)
    
    return sorted(final_dirs | ignored_files)


def main():
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent.parent.parent
    
    ignored_paths = get_ignored_directories(repo_root)
    
    output_dir = script_dir.parent / 'res'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'git_ignored_paths_generated.txt'
    
    with open(output_file, 'w') as f:
        for path in ignored_paths:
            f.write(path + '\n')


if __name__ == '__main__':
    main()
