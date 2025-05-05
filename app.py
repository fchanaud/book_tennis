#!/usr/bin/env python3

import os
import logging
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from tennis_booking import check_court_availability

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Create scheduler
scheduler = BackgroundScheduler()

# Schedule the tennis booking check to run every day between 9:55 PM and 10:05 PM UK time
# This is approximately between 21:55 and 22:05 UTC during summer time
scheduler.add_job(
    check_court_availability,
    'cron',
    hour='21-22',
    minute='55-5',
    timezone='Europe/London'
)

# Start the scheduler
scheduler.start()

@app.route('/')
def index():
    return jsonify({
        "status": "running",
        "app": "Tennis Court Booking Automation"
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy"
    }), 200

@app.route('/run-check')
def run_check():
    """Manually trigger a court availability check."""
    try:
        check_court_availability()
        return jsonify({
            "status": "success",
            "message": "Court availability check completed"
        })
    except Exception as e:
        logger.error(f"Error running court availability check: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    # Only for local development
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True) 