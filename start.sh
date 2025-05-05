#!/bin/bash
set -e

# Print some debugging info
echo "Starting server at $(date)"
echo "Current directory: $(pwd)"
echo "Content of current directory:"
ls -la

# Find Python binary
echo "Looking for Python..."
which python3 || echo "python3 not found"
find / -name python3 -type f 2>/dev/null | grep -v "Permission denied" || echo "No python3 found in search"

# Try to activate the virtual environment
if [ -d ".venv" ]; then
    echo "Activating .venv virtual environment"
    source .venv/bin/activate
elif [ -d "/opt/render/project/src/.venv" ]; then
    echo "Activating Render virtual environment"
    source /opt/render/project/src/.venv/bin/activate
elif [ -d "${HOME}/.venv" ]; then
    echo "Activating home directory virtual environment"
    source ${HOME}/.venv/bin/activate
else
    echo "No virtual environment found, trying to use python3 directly"
fi

# Set the environment variable for Playwright browsers
export PLAYWRIGHT_BROWSERS_PATH=$HOME/pw-browsers

# Try running with python3 if python is not found
if command -v python >/dev/null 2>&1; then
    echo "Using python command"
    python -m gunicorn server:app --timeout 120 --bind 0.0.0.0:$PORT
else
    echo "Python not found, trying python3"
    python3 -m gunicorn server:app --timeout 120 --bind 0.0.0.0:$PORT
fi 