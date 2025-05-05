#!/bin/bash
set -e

# Set the environment variable for Playwright browsers
export PLAYWRIGHT_BROWSERS_PATH=$HOME/pw-browsers

# Print some debugging info
echo "Starting server at $(date)"
echo "Current directory: $(pwd)"
echo "Content of current directory:"
ls -la

# Run the application with gunicorn
python -m gunicorn server:app --timeout 120 --bind 0.0.0.0:$PORT 