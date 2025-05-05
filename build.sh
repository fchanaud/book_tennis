#!/bin/bash
set -e

# Print debugging information
echo "Build starting at $(date)"
echo "Current directory: $(pwd)"
echo "Content of current directory:"
ls -la

# Find Python binary
echo "Looking for Python..."
which python3 || echo "python3 not found"
which python || echo "python not found"

# Use python3 command if python is not found
if command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

echo "Using $PYTHON_CMD for installation"

# Update pip
$PYTHON_CMD -m pip install --upgrade pip

# Install dependencies
$PYTHON_CMD -m pip install -r requirements.txt

# Make sure gunicorn is installed
$PYTHON_CMD -m pip install gunicorn uvicorn

# Install Playwright without browser
$PYTHON_CMD -m pip install playwright

# Install just the browser binaries without system dependencies
export PLAYWRIGHT_BROWSERS_PATH=$HOME/pw-browsers
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
$PYTHON_CMD -m playwright install chromium || echo "Failed to install Playwright browser, but continuing anyway"

echo "Build completed successfully!" 