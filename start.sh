#!/bin/bash
set -e

# Run the application with gunicorn
python -m gunicorn server:app --timeout 120 --bind 0.0.0.0:$PORT 