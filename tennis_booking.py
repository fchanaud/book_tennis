#!/usr/bin/env python3

import os
import time
import logging
import datetime
import pytz
import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

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

def setup_driver():
    """Set up and return a Chrome WebDriver with headless options."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    try:
        # For local development
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except WebDriverException:
        # For production (Render.com)
        chrome_options.binary_location = os.getenv("CHROME_BIN", "/usr/bin/google-chrome")
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.set_page_load_timeout(30)
    return driver

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
    
    driver = None
    try:
        # Set up the WebDriver
        driver = setup_driver()
        
        # Get the target date (7 days from now)
        target_date = get_target_date()
        date_str = format_date_for_url(target_date)
        day_type = get_day_type(target_date)
        
        # Construct the URL for the target date
        url = f"{BASE_URL}#?date={date_str}"
        logger.info(f"Checking availability for {date_str} (day type: {day_type})")
        
        # Navigate to the page
        driver.get(url)
        
        # Wait for the booking table to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "resource-schedule"))
        )
        
        # Give additional time for JavaScript to fully render the page
        time.sleep(2)
        
        # Find all available slots
        available_slots = driver.find_elements(By.CSS_SELECTOR, ".slot:not(.unavailable)")
        
        if not available_slots:
            logger.info(f"No available slots found for {date_str}")
            return
        
        logger.info(f"Found {len(available_slots)} potentially available slots")
        
        # Process each available slot
        for slot in available_slots:
            try:
                # Extract information from the slot
                court_element = slot.find_element(By.XPATH, "ancestor::div[contains(@class, 'resource-row')]")
                court_name = court_element.find_element(By.CLASS_NAME, "resource-name").text.strip()
                
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
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "continueButton"))
                    )
                    
                    # Get the current URL, which will be the booking URL
                    booking_url = driver.current_url
                    
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
                    driver.get(url)
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "resource-schedule"))
                    )
                    time.sleep(2)
            
            except (NoSuchElementException, TimeoutException) as e:
                logger.error(f"Error processing slot: {str(e)}")
                # Continue with next slot
                driver.get(url)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "resource-schedule"))
                )
                time.sleep(2)
    
    except Exception as e:
        logger.error(f"Error checking court availability: {str(e)}")
    
    finally:
        if driver:
            driver.quit()
        logger.info("Completed court availability check")

if __name__ == "__main__":
    check_court_availability() 