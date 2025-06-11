#!/bin/bash

# Exit if a command fails
set -e

# Exit if project name or python version aren't specified as args
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <project name> <python version to use>"
    exit 1
fi

# Sanitize project name
PACKAGE_NAME=$(echo "$1" | tr "-" "_")

# Install desired python version if not already installed
pyenv install --skip-existing "$2"

# Set python version for pyenv
pyenv local "$2"

# Check poetry's major version >= 2
poetry_version=$(poetry --version | sed -E 's/^Poetry \(version (.*)\)$/\1/')
if [[ $(echo $poetry_version | cut -d'.' -f1) -lt 2 ]]; then
    echo "Unsupported poetry version. Support >= 2.0.0, found ${poetry_version}"
    exit 1
fi

# Initialize poetry env with specified python
poetry init --no-interaction --name "$PACKAGE_NAME" --python "~=$2"

# Make poetry use the correct version of python when spawning the venv
pyenv which python | xargs poetry env use

# Make poetry store the venv in the .venv folder inside the project
poetry config virtualenvs.in-project true --local

# Install venv and add dev deps
poetry add --group dev ruff docstr-coverage pytest pytest-cov pre-commit detect-secrets memray pyinstrument
poetry add --group cicd basedpyright

# Install pre-commit hooks
poetry run pre-commit install

# Rename source code folder
mv project_base "$PACKAGE_NAME"

# If testing the template rename project imports in test script (for template development purposes)
# else remove the test script
if [ "$test" = true ]; then
    sed -i '' "s/project_base/$PACKAGE_NAME/" "$PACKAGE_NAME/test.py"
else
    rm "$PACKAGE_NAME/test.py"
fi

# Update FastAPI App configuration in launch.json to use the new package name
if [ -f ".vscode/launch.json" ]; then
    echo "Updating FastAPI App configuration in launch.json"
    # Replace 'your_package' with the actual package name in the FastAPI configuration.
    sed -i '' "s/your_package\.apis\.service\.app:app/$PACKAGE_NAME\.apis\.service\.app:app/g" .vscode/launch.json
fi

# Install current project's source
poetry sync

# Create a baseline for detect-secrets
poetry run detect-secrets scan >.secrets.baseline

# pin poetry version requirement
echo "[tool.poetry]\nrequires-poetry = \">=2.0\"" >>pyproject.toml

# Finally, remove all dangling files.
rm -rf docs/assets CONTRIBUTING.md README.md "$0"

# Create a README file to avoid errors when running workflows
# since pyproject.toml adds the Readme file as a dependency
echo "# $PACKAGE_NAME" > README.md
