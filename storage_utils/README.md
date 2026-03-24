# Storage Analysis Tools

Tools for managing git-ignored files by moving them to an archive directory and creating symlinks.

## Scripts

### Core Tools
- **ListGitIgnoredPaths04.py** - Lists all git-ignored paths (excluding symlinks, including submodules)
- **MoveGitIgnoredPaths01.py** - Moves ignored paths to target directory with conflict detection
- **SymlinkGitIgnoredPaths01.py** - Creates symlinks pointing to moved files
- **OrganizeGitIgnoredPaths01.py** - Master script that runs all three sequentially

## Quick Start

```bash
# Run the complete workflow
python src/OrganizeGitIgnoredPaths01.py \
    --repository_dirpath /path/to/repository \
    --target_dirpath /path/to/archive \
    --verbose
```

This will:
1. Generate fresh list of git-ignored paths from the specified repository
2. Move them to archive directory (preserving structure)
3. Create symlinks back to original locations
4. Save all reports to `data/reports/YYYYMMDD_HHMMSS/`

## Individual Scripts

Run each script separately for more control:

```bash
# Step 1: List git-ignored paths
python src/ListGitIgnoredPaths04.py \
    --repository_dirpath /path/to/repository \
    --reports_dirpath /path/to/reports \
    --verbose

# Step 2: Move files to archive
python src/MoveGitIgnoredPaths01.py \
    --repository_dirpath /path/to/repository \
    --target_dirpath /path/to/archive \
    --ignored_paths_filepath /path/to/reports/git_ignored_paths.txt \
    --reports_dirpath /path/to/reports \
    --verbose

# Step 3: Create symlinks
python src/SymlinkGitIgnoredPaths01.py \
    --repository_dirpath /path/to/repository \
    --target_dirpath /path/to/archive \
    --ignored_paths_filepath /path/to/reports/git_ignored_paths.txt \
    --reports_dirpath /path/to/reports \
    --verbose
```

## Reports

Each run creates a timestamped directory with:
- `git_ignored_paths.txt` - List of paths processed
- `move_conflicts.txt` - File conflicts during move (if any)
- `move_missing_paths.txt` - Missing/skipped paths (if any)
- `symlink_conflicts.txt` - Symlink creation conflicts (if any)
- `symlink_missing_targets.txt` - Missing targets (if any)

## Safety Features

- No data overwrites - all conflicts reported for manual review
- Automatic empty directory cleanup
- Symlink validation before creation
- Recursive directory merging
