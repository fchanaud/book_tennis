#!/usr/bin/env python3

import os
import time
import logging
import datetime
import pytz
import requests
import asyncio
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tennis_booking.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Pushover configuration
PUSHOVER_USER_KEY = os.getenv('PUSHOVER_USER_KEY')
PUSHOVER_API_TOKEN = os.getenv('PUSHOVER_API_TOKEN')
PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"

# Tennis court booking configuration
BASE_URL = "https://clubspark.lta.org.uk/LondonFieldsPark/Booking/BookByDate"

# Time preferences
PREFERENCES = {
    "wednesday": [(8*60, 8*60+60), (12*60, 14*60)],  # 8:00-9:00 AM or 12:00-14:00
    "weekday": [(18*60, 22*60)],  # After 18:00
    "weekend": [(8*60, 22*60)]  # Any time (max 2 hours)
}

# Maximum booking duration in minutes
MAX_DURATION = {
    "wednesday": 120,
    "weekday": 120,
    "weekend": 120
}

def get_target_date():
    """Get the date 7 days from now."""
    london_tz = pytz.timezone('Europe/London')
    now = datetime.datetime.now(london_tz)
    target_date = now + datetime.timedelta(days=7)
    return target_date

def format_date_for_url(date):
    """Format the date for the URL parameter."""
    return date.strftime("%Y-%m-%d")

def get_day_type(date):
    """Return whether the given date is a weekday, weekend, or Wednesday."""
    weekday = date.weekday()
    if weekday == 2:  # Wednesday
        return "wednesday"
    elif weekday < 5:  # Monday-Friday (0-4)
        return "weekday"
    else:  # Saturday-Sunday (5-6)
        return "weekend"

def is_time_in_preferences(day_type, start_minutes, end_minutes):
    """Check if the time slot fits the user's preferences."""
    if day_type not in PREFERENCES:
        return False
    
    duration = end_minutes - start_minutes
    max_duration = MAX_DURATION.get(day_type, 120)
    
    # Check if the duration is acceptable
    if duration > max_duration:
        return False
    
    # Check if the time slot is within preferred hours
    for start_pref, end_pref in PREFERENCES[day_type]:
        # Time slot starts within the preference window
        if start_pref <= start_minutes < end_pref:
            return True
        # Time slot ends within the preference window
        if start_pref < end_minutes <= end_pref:
            return True
        # Time slot completely contains the preference window
        if start_minutes <= start_pref and end_minutes >= end_pref:
            return True
    
    return False

def minutes_to_time_str(minutes):
    """Convert minutes since midnight to a time string (HH:MM)."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"

def send_pushover_notification(slot_info):
    """Send a Pushover notification with booking URL."""
    if not all([PUSHOVER_USER_KEY, PUSHOVER_API_TOKEN]):
        logger.error("Pushover configuration missing. Please set PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN environment variables.")
        return False
    
    try:
        # Prepare notification message
        title = f"Tennis Court Available: {slot_info['date']} at {slot_info['start_time']}"
        message = f"Tennis court available at London Fields Park!\n\nDate: {slot_info['date']}\nCourt: {slot_info['court']}\nTime: {slot_info['start_time']} - {slot_info['end_time']}"
        
        # Prepare payload for Pushover API
        payload = {
            "token": PUSHOVER_API_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "title": title,
            "message": message,
            "url": slot_info['booking_url'],
            "url_title": "Book Now",
            "priority": 1,  # High priority
            "sound": "pushover"  # Distinct notification sound
        }
        
        # Send the notification
        response = requests.post(PUSHOVER_API_URL, data=payload)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        logger.info(f"Pushover notification sent for slot on {slot_info['date']} at {slot_info['start_time']}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send Pushover notification: {str(e)}")
        return False

def check_court_availability():
    """Main function to check for available tennis courts."""
    logger.info("Starting court availability check")
    
    with sync_playwright() as p:
        try:
            # Launch browser
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            
            # Get the target date (7 days from now)
            target_date = get_target_date()
            date_str = format_date_for_url(target_date)
            day_type = get_day_type(target_date)
            
            # Construct the URL for the target date
            url = f"{BASE_URL}#?date={date_str}"
            logger.info(f"Checking availability for {date_str} (day type: {day_type})")
            
            # Navigate to the page
            page.goto(url, wait_until="networkidle")
            
            # Wait for the booking table to load
            page.wait_for_selector(".resource-schedule", timeout=30000)
            
            # Find all available slots
            available_slots = page.query_selector_all(".slot:not(.unavailable)")
            
            if not available_slots:
                logger.info(f"No available slots found for {date_str}")
                return
            
            logger.info(f"Found {len(available_slots)} potentially available slots")
            
            # Process each available slot
            for slot in available_slots:
                try:
                    # Extract information from the slot
                    court_element = slot.evaluate("node => node.closest('.resource-row')")
                    court_name = page.evaluate("el => el.querySelector('.resource-name').textContent.trim()", court_element)
                    
                    # Get time information from attributes
                    start_minutes = int(slot.get_attribute("data-starttime"))
                    end_minutes = int(slot.get_attribute("data-endtime"))
                    
                    # Check if the slot matches preferences
                    if is_time_in_preferences(day_type, start_minutes, end_minutes):
                        start_time = minutes_to_time_str(start_minutes)
                        end_time = minutes_to_time_str(end_minutes)
                        
                        logger.info(f"Found matching slot: {court_name} on {date_str} at {start_time}-{end_time}")
                        
                        # Click on the slot to proceed to booking
                        slot.click()
                        
                        # Wait for the booking details to load
                        page.wait_for_selector("#continueButton", timeout=10000)
                        
                        # Get the current URL, which will be the booking URL
                        booking_url = page.url
                        
                        # Send notification with the booking URL
                        slot_info = {
                            "date": date_str,
                            "court": court_name,
                            "start_time": start_time,
                            "end_time": end_time,
                            "booking_url": booking_url
                        }
                        
                        send_pushover_notification(slot_info)
                        
                        # Go back to the availability page to check other slots
                        page.goto(url, wait_until="networkidle")
                        page.wait_for_selector(".resource-schedule", timeout=30000)
                
                except Exception as e:
                    logger.error(f"Error processing slot: {str(e)}")
                    # Continue with next slot
                    page.goto(url, wait_until="networkidle")
                    page.wait_for_selector(".resource-schedule", timeout=30000)
        
        except Exception as e:
            logger.error(f"Error checking court availability: {str(e)}")
            
        finally:
            if 'browser' in locals():
                browser.close()
            logger.info("Completed court availability check")

if __name__ == "__main__":
    check_court_availability() 