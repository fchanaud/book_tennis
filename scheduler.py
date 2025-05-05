#!/usr/bin/env python3

import os
import time
import logging
import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from tennis_booking import check_court_availability

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scheduler.log')
    ]
)
logger = logging.getLogger(__name__)

def is_within_booking_window():
    """Check if current time is within the booking window (9:55 PM - 10:05 PM UK time)."""
    london_tz = pytz.timezone('Europe/London')
    now = datetime.datetime.now(london_tz)
    
    # Define the booking window
    start_hour, start_minute = 21, 55  # 9:55 PM
    end_hour, end_minute = 22, 5       # 10:05 PM
    
    # Current time in hours and minutes
    current_hour, current_minute = now.hour, now.minute
    
    # Check if current time is within the booking window
    if current_hour == start_hour and current_minute >= start_minute:
        return True
    if current_hour == end_hour and current_minute <= end_minute:
        return True
    
    return False

def scheduled_job():
    """Wrapper for the check_court_availability function that only runs during the booking window."""
    logger.info("Scheduled job triggered")
    
    if is_within_booking_window():
        logger.info("Current time is within booking window, executing court availability check")
        check_court_availability()
    else:
        logger.info("Current time is outside booking window, skipping court availability check")

def main():
    logger.info("Starting the tennis court booking scheduler")
    
    # Create a scheduler
    scheduler = BackgroundScheduler()
    
    # Schedule the job to run every minute
    scheduler.add_job(
        scheduled_job,
        trigger=CronTrigger(minute='*'),  # Run every minute
        id='check_court_availability',
        name='Check tennis court availability',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started, waiting for booking window")
    
    try:
        # Keep the script running
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        # Shut down the scheduler gracefully
        scheduler.shutdown()
        logger.info("Scheduler shut down")

if __name__ == "__main__":
    main() 