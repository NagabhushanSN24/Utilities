#!/bin/bash
# Synchronizes changes from a public repository to a private fork and creates pull requests for each branch with new changes
# Also pushes new tags that are not in the private fork
# Example usage: bash PullPublicRepoToPrivateFork.sh https://github.com/octocat/public-repo my_private_repo_name

# Function to display usage information
usage() {
    echo "Usage: $0 <public_repo_url> <private_repo_name>"
    exit 1
}

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
    usage
fi

# Assign arguments to variables
PUBLIC_REPO_URL=$1
PRIVATE_REPO_NAME=$2
USERNAME=$(gh api user | jq -r '.login')

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "jq is required for this script to work. Please install jq and try again."
    echo "For Debian/ubuntu-based systems, you can install jq using the following command:"
    echo "sudo apt-get install jq"
    echo "For MacOS, you can install jq using the following command:"
    echo "brew install jq"
    echo "Visit https://stedolan.github.io/jq/download/ for detailed installation instructions."
    exit 1
fi

# Create a temporary directory
TEMP_DIR="temp_private_repo"
if [ -d "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
fi

# Clone the public repository
git clone "$PUBLIC_REPO_URL" "$TEMP_DIR"
cd "$TEMP_DIR" || exit

# Set local configurations for large repo handling
git config http.postBuffer 524288000
git config http.maxRequestBuffer 1024M
git config core.compression -1

# Fetch all branches and tags from the public repository
git fetch origin --prune --tags

# Get the names of all remote branches upfront and store them in a variable
# REMOTE_BRANCHES=$(git branch -r | grep 'origin/' | grep -v '\->' | sed 's|origin/||')
REMOTE_BRANCHES=$(git for-each-ref --format '%(refname:short)' refs/remotes/origin | grep -v 'HEAD\|tags/')
echo "Remote branches found: $REMOTE_BRANCHES"

# Set the private repository as the new remote
git remote set-url origin "https://github.com/$USERNAME/$PRIVATE_REPO_NAME.git"

# Pseudo code:
# For each local branch
#   Check if the branch exists in the remote
#   if remote branch does not exist:
#     push the local branch to remote
#   else:
#     check if local branch has any commits that are not there in remote branch
#     if there are changes:
#       rename the local branch
#       push the renamed local branch to remote
#       create a pull request from the renamed branch to the original branch
#     else:
#       print that there are no changes and do nothing

# Loop through all branches in the remote public repository
for REMOTE_BRANCH in $REMOTE_BRANCHES; do
    echo "Processing branch: $REMOTE_BRANCH"

    # Checkout the remote branch locally
    git checkout -B "$REMOTE_BRANCH" "origin/$REMOTE_BRANCH"

    # Check if the branch exists in the remote private repository
    if git ls-remote --heads origin "$REMOTE_BRANCH" | grep "$REMOTE_BRANCH" >/dev/null; then
        echo "Branch $REMOTE_BRANCH exists in remote. Checking for differences..."

        # Check if there are any commits in the local branch that are not in the remote
        git fetch origin
        if [ $(git rev-list --count "origin/$REMOTE_BRANCH".."$REMOTE_BRANCH") -gt 0 ]; then
            echo "Local branch $REMOTE_BRANCH has new commits not in remote."

            # Rename the local branch
            NEW_BRANCH_NAME="${REMOTE_BRANCH}-updates-$(date +%Y%m%d%H%M%S)"
            git branch -m "$REMOTE_BRANCH" "$NEW_BRANCH_NAME"

            # Push the renamed branch to the remote
            git push origin "$NEW_BRANCH_NAME"

            # Create a pull request using GitHub CLI
            gh pr create --title "Sync updates for branch $REMOTE_BRANCH" --body "This PR syncs updates from the public repository." --base "$REMOTE_BRANCH" --head "$NEW_BRANCH_NAME"
        else
            echo "No changes in the local branch $REMOTE_BRANCH compared to the remote."
        fi
    else
        echo "Branch $REMOTE_BRANCH does not exist in the remote. Pushing branch..."
        git push -u origin "$REMOTE_BRANCH"
    fi
done

# Get all tags from the public repository
REMOTE_TAGS=$(git ls-remote --tags origin | grep -o 'refs/tags/[a-zA-Z0-9._-]*$' | sed 's/refs\/tags\///')
echo "Remote tags found: $REMOTE_TAGS"

# Loop through all tags in the remote public repository
for TAG in $REMOTE_TAGS; do
    echo "Processing tag: $TAG"

    # Check if the tag exists in the remote private repository
    if git ls-remote --tags origin "$TAG" | grep "$TAG" >/dev/null; then
        echo "Tag $TAG already exists in the remote. Skipping..."
    else
        echo "Tag $TAG does not exist in the remote. Pushing tag..."
        git push origin "refs/tags/$TAG"
    fi
done

# Cleanup
cd ..
rm -rf "$TEMP_DIR"

echo "Sync completed successfully."
