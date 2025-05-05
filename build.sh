#!/bin/bash
set -e

# Update pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Make sure gunicorn is installed
pip install gunicorn uvicorn

# Install Playwright without browser
pip install playwright

# Install just the browser binaries without system dependencies
export PLAYWRIGHT_BROWSERS_PATH=$HOME/pw-browsers
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
python -m playwright install chromium --with-deps || python -m playwright install chromium

echo "Build completed successfully!" 