#!/usr/bin/env python3

import os
import threading
import logging
from flask import Flask, jsonify
from scheduler import main as run_scheduler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Start the scheduler in a separate thread
scheduler_thread = None

def start_scheduler():
    global scheduler_thread
    if scheduler_thread is None or not scheduler_thread.is_alive():
        logger.info("Starting scheduler thread")
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        logger.info("Scheduler thread started")

# Create Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "message": "Tennis Court Booking Service is running"
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "scheduler_running": scheduler_thread is not None and scheduler_thread.is_alive()
    })

@app.route('/start-scheduler')
def trigger_scheduler():
    start_scheduler()
    return jsonify({
        "status": "success",
        "message": "Scheduler started"
    })

if __name__ == '__main__':
    # Start the scheduler
    start_scheduler()
    
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=port) 