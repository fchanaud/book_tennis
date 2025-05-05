from flask import Flask
import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from tennis_booking import check_court_availability
import pytz
import sys
import subprocess

# Set Playwright browsers path if not already set
if 'PLAYWRIGHT_BROWSERS_PATH' not in os.environ:
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.join(os.path.expanduser('~'), 'pw-browsers')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Create a scheduler
scheduler = BackgroundScheduler()
scheduler_started = False

# Schedule the job to run daily at a specific time (UK time)
def schedule_job():
    global scheduler_started
    if scheduler_started:
        return
        
    uk_timezone = pytz.timezone('Europe/London')
    # Run at 9:55 PM UK time
    scheduler.add_job(check_court_availability, 'cron', hour=21, minute=55, timezone=uk_timezone)
    # Run at 10:00 PM UK time
    scheduler.add_job(check_court_availability, 'cron', hour=22, minute=0, timezone=uk_timezone)
    # Run at 10:05 PM UK time
    scheduler.add_job(check_court_availability, 'cron', hour=22, minute=5, timezone=uk_timezone)
    
    scheduler.start()
    scheduler_started = True
    logger.info("Scheduler started with jobs")

# Start the scheduler with app
with app.app_context():
    try:
        schedule_job()
        logger.info("Jobs scheduled during app initialization")
    except Exception as e:
        logger.error(f"Error scheduling jobs during initialization: {str(e)}")

# Health check endpoint
@app.route('/')
def health_check():
    return {
        "status": "healthy",
        "message": "Tennis booking service running"
    }

# Manual trigger endpoint
@app.route('/run-check', methods=['GET'])
def run_check():
    try:
        check_court_availability()
        return {
            "status": "success",
            "message": "Court availability check triggered manually"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error running court availability check: {str(e)}"
        }

if __name__ == "__main__":
    # Start the Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port) 