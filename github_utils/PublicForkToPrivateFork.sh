#!/bin/bash
# Converts a public fork to private fork. Clones the public fork, deletes the public fork in GitHub,
# creates a new private repo in GitHub, and pushes the local repo to private GitHub repo.
# Example usage: bash PublicForkToPrivateFork.sh https://github.com/NagabhushanSN24/forked-repo
#
# This script requires delete access. Give the access by running `gh auth refresh -h github.com -s delete_repo`.
# Revoke the delete access once the process is complete. However, delete access alone cannot be revoked. Revoke all
# access by visiting the below link: https://github.com/settings/connections/applications/178c6fc778ccc68e1d6a
# Then authorize GitHub CLI again by running `gh auth login`.

# Function to display usage information
usage() {
    echo "Usage: $0 <public_forked_repo_url>"
    exit 1
}

# Check if the correct number of arguments is provided
if [ "$#" -ne 1 ]; then
    usage
fi

# Assign arguments to variables
PUBLIC_FORKED_REPO_URL=$1
USERNAME=$(gh api user | jq -r '.login')
REPO_NAME=$(basename -s .git "$PUBLIC_FORKED_REPO_URL")

# Check if the repository is public
repo_visibility=$(gh api repos/$USERNAME/$REPO_NAME --jq '.private')

# Check if the repository is already private
if [ "$repo_visibility" = "true" ]; then
    echo "The repository '$USERNAME/$REPO_NAME' is already private."
    exit 0
fi

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

# Define the temporary directory name
TEMP_DIR="temp_repo"

# Remove the temporary directory if it already exists
if [ -d "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
fi

# Clone the forked public repository (bare) to the temporary directory
git clone --bare "$PUBLIC_FORKED_REPO_URL" "$TEMP_DIR"
cd "$TEMP_DIR" || exit

# Delete the forked public repository on GitHub
gh repo delete --yes "$USERNAME/$REPO_NAME"

# Create a new private repository with the same name
gh repo create "$USERNAME/$REPO_NAME" --private

# Add the new private repository as a remote
git remote add private "https://github.com/$USERNAME/$REPO_NAME.git"

# Increase buffer size to push large objects
git config http.postBuffer 524288000

# Push all branches and tags to the private repository
git push --mirror private

# Cleanup
cd ..
rm -rf "$TEMP_DIR"

echo "Public fork converted to private fork successfully: https://github.com/$USERNAME/$REPO_NAME"
