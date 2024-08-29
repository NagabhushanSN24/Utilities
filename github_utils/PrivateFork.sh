#!/bin/bash
# Creates a private fork of a public repository on GitHub
# Example usage: bash PrivateFork.sh https://github.com/octocat/public-repo my_private_repo_name

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

# Define the temporary directory name
TEMP_DIR="temp_repo"

# Remove the temporary directory if it already exists
if [ -d "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
fi

# Clone the public repository (bare) to the temporary directory
git clone --bare "$PUBLIC_REPO_URL" "$TEMP_DIR"
cd "$TEMP_DIR" || exit

# Create a new private repository
gh repo create "$USERNAME/$PRIVATE_REPO_NAME" --private

# Add the new private repository as a remote
git remote add private "https://github.com/$USERNAME/$PRIVATE_REPO_NAME.git"

# Increase buffer size to push large objects
git config http.postBuffer 524288000

# Push all branches and tags to the private repository
git push --mirror private

# Cleanup
cd ..
rm -rf "$TEMP_DIR"

echo "Private fork created successfully: https://github.com/$USERNAME/$PRIVATE_REPO_NAME"
