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
import re

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
BASE_URL = "https://clubspark.lta.org.uk/ClissoldParkHackney/Booking/BookByDate"

# Time preferences
PREFERENCES = {
    "wednesday": [(8*60, 8*60+60), (12*60, 14*60)],  # 8:00-9:00 AM or 12:00-14:00
    "weekday": [(18*60, 22*60)],  # After 18:00
    "weekend": [(8*60, 22*60)]  # Any time (max 2 hours)
}

# Maximum booking duration in minutes
MAX_DURATION = {
    "wednesday": 60,  # 1 hour for morning slots, 2 hours for afternoon
    "weekday": 120,   # 2 hours max for weekday evenings
    "weekend": 120    # 2 hours max for weekends
}

def get_target_date():
    """Get the date 6 days from now."""
    london_tz = pytz.timezone('Europe/London')
    now = datetime.datetime.now(london_tz)
    target_date = now + datetime.timedelta(days=6)
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
    
    # Special handling for Wednesday with different max durations for morning vs afternoon
    if day_type == "wednesday":
        # Morning slot (8:00-9:00)
        if 8*60 <= start_minutes < 9*60:
            max_duration = 60  # 1 hour max for morning
        # Afternoon slot (12:00-14:00)
        elif 12*60 <= start_minutes < 14*60:
            max_duration = 120  # 2 hours max for afternoon
        else:
            max_duration = MAX_DURATION.get(day_type, 60)
    else:
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
        
        # Add additional message if provided
        if 'additional_message' in slot_info and slot_info['additional_message']:
            message += f"\n\n{slot_info['additional_message']}"
        
        # Handle long URLs (Pushover has limitations on URL length)
        booking_url = slot_info['booking_url']
        if len(booking_url) > 500:  # Pushover has limits on URL length
            # Extract the essential parts of the URL
            parts = booking_url.split("?")
            base_url = parts[0]
            # Just keep the base URL and note that it's truncated
            logger.warning(f"URL too long ({len(booking_url)} chars), truncating for Pushover")
            booking_url = f"{base_url}?...[truncated]"
            # Add the full URL to the message body
            message += f"\n\nFull URL (copy/paste):\n{slot_info['booking_url']}"
        
        # Prepare payload for Pushover API
        payload = {
            "token": PUSHOVER_API_TOKEN,
            "user": PUSHOVER_USER_KEY,
            "title": title,
            "message": message,
            "url": booking_url,
            "url_title": "Book Now",
            "priority": 1,  # High priority
            "sound": "pushover"  # Distinct notification sound
        }
        
        # For testing or debugging, print the payload length but mask sensitive data
        debug_payload = payload.copy()
        debug_payload["token"] = "***masked***"
        debug_payload["user"] = "***masked***"
        logger.debug(f"Pushover payload length: {len(str(payload))} bytes")
        
        # Send the notification
        response = requests.post(PUSHOVER_API_URL, data=payload)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        logger.info(f"Pushover notification sent for slot on {slot_info['date']} at {slot_info['start_time']}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send Pushover notification: {str(e)}")
        # For common errors, give more specific advice
        if "400" in str(e):
            logger.error("HTTP 400 Error: This could be due to invalid API credentials or message format")
        elif "413" in str(e) or "too large" in str(e).lower():
            logger.error("Message too large: Try shortening the URL or message")
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
            
            # Get the target date (6 days from now)
            target_date = get_target_date()
            date_str = format_date_for_url(target_date)
            day_type = get_day_type(target_date)
            
            # Construct the URL for the target date
            url = f"{BASE_URL}#?date={date_str}"
            logger.info(f"Checking availability for {date_str} (day type: {day_type})")
            
            # Navigate to the page and wait for it to be fully loaded
            page.goto(url, wait_until="networkidle")
            
            # Wait for the booking calendar to load
            try:
                # Wait for the booking-sheet class which is the correct one for this calendar view
                page.wait_for_selector(".booking-sheet", timeout=30000)
                logger.info("Booking calendar (.booking-sheet) loaded successfully")
            except Exception as e:
                logger.error(f"Error waiting for booking calendar: {str(e)}")
                logger.info("Attempting to continue anyway...")
                # Add a small delay to give the page more time to load
                page.wait_for_timeout(5000)
            
            # Find all available slots with the class 'not-booked'
            available_slots = page.query_selector_all(".not-booked")
            
            # Get information about available slots for debugging
            if available_slots:
                logger.info(f"Found {len(available_slots)} potentially available slots")
                
                # Debug: print information about the first few slots
                for idx, slot in enumerate(available_slots[:3]):  # Look at just the first 3 slots
                    try:
                        # Get attributes and properties
                        attributes = slot.evaluate("""node => {
                            const attrs = {};
                            for (let i = 0; i < node.attributes.length; i++) {
                                const attr = node.attributes[i];
                                attrs[attr.name] = attr.value;
                            }
                            
                            // Also get class list
                            attrs['classList'] = Array.from(node.classList);
                            
                            // Get inner text
                            attrs['innerText'] = node.innerText;
                            
                            // Get parent element info
                            if (node.parentElement) {
                                attrs['parentClasses'] = Array.from(node.parentElement.classList);
                            }
                            
                            return attrs;
                        }""")
                        
                        logger.info(f"Slot {idx + 1} debug info:")
                        for key, value in attributes.items():
                            logger.info(f"  {key}: {value}")
                    except Exception as e:
                        logger.error(f"Error getting debug info for slot {idx + 1}: {str(e)}")
            else:
                logger.info(f"No available slots found for {date_str}")
                return
            
            # Process each available slot
            for slot in available_slots:
                try:
                    # Try different methods to get court name
                    court_name = "Unknown Court"
                    
                    try:
                        # Method 1: Try to get the court name from any parent element with a court name
                        parent_row = slot.evaluate("node => node.closest('.resource-row')")
                        if parent_row:
                            court_name_el = page.evaluate("el => el.querySelector('.resource-name')", parent_row)
                            if court_name_el:
                                court_name = page.evaluate("el => el.textContent.trim()", court_name_el)
                    except Exception as e:
                        logger.warning(f"Method 1 failed to get court name: {str(e)}")
                        
                        try:
                            # Method 2: Try using data attributes on the slot
                            resource_id = slot.get_attribute("data-resourceid")
                            if resource_id:
                                # Look for elements with the same resource ID
                                resource_name_el = page.query_selector(f"[data-resourceid='{resource_id}'] .resource-name, [data-id='{resource_id}'] .resource-name")
                                if resource_name_el:
                                    court_name = resource_name_el.inner_text().strip()
                                else:
                                    # Just use the resource ID as a fallback
                                    court_name = f"Court {resource_id}"
                        except Exception as inner_e:
                            logger.warning(f"Method 2 failed to get court name: {str(inner_e)}")
                            
                            try:
                                # Method 3: Check if the slot has a title attribute with court info
                                title = slot.get_attribute("title")
                                if title and "Court" in title:
                                    court_name = title.split(" - ")[0].strip()
                            except Exception as inner_e2:
                                logger.warning(f"Method 3 failed to get court name: {str(inner_e2)}")
                    
                    # Get time information from attributes or alternative sources
                    try:
                        # Look for the 'available-booking-slot' span which contains the time information
                        time_span = slot.query_selector(".available-booking-slot")
                        if time_span:
                            time_text = time_span.inner_text()
                            logger.info(f"Found time text: {time_text}")
                            
                            # Extract time information from text like "Book at 07:00 - 08:00"
                            time_pattern = r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})"
                            time_match = re.search(time_pattern, time_text)
                            
                            if time_match:
                                start_time_str, end_time_str = time_match.groups()
                                
                                # Convert time strings to minutes
                                start_h, start_m = map(int, start_time_str.split(":"))
                                end_h, end_m = map(int, end_time_str.split(":"))
                                
                                start_minutes = start_h * 60 + start_m
                                end_minutes = end_h * 60 + end_m
                                
                                logger.info(f"Extracted time: {start_time_str} to {end_time_str}")
                            else:
                                # Try extracting from data-test-id which contains court|date|time
                                test_id = slot.get_attribute("data-test-id")
                                if test_id:
                                    parts = test_id.split("|")
                                    if len(parts) >= 3:
                                        # The third part is time in minutes from midnight
                                        try:
                                            start_minutes = int(parts[2])
                                            # Assume 1 hour slots by default
                                            end_minutes = start_minutes + 60
                                            logger.info(f"Extracted time from data-test-id: {start_minutes} minutes (slot duration: 60 min)")
                                        except ValueError:
                                            raise ValueError(f"Could not convert time value from data-test-id: {parts[2]}")
                                    else:
                                        raise ValueError(f"data-test-id does not contain expected format: {test_id}")
                                else:
                                    raise ValueError("No available-booking-slot span or data-test-id found")
                        else:
                            # Try extracting from data-test-id which contains court|date|time
                            test_id = slot.get_attribute("data-test-id")
                            if test_id:
                                parts = test_id.split("|")
                                if len(parts) >= 3:
                                    # The third part is time in minutes from midnight
                                    try:
                                        start_minutes = int(parts[2])
                                        # Assume 1 hour slots by default
                                        end_minutes = start_minutes + 60
                                        logger.info(f"Extracted time from data-test-id: {start_minutes} minutes (slot duration: 60 min)")
                                    except ValueError:
                                        raise ValueError(f"Could not convert time value from data-test-id: {parts[2]}")
                                else:
                                    raise ValueError(f"data-test-id does not contain expected format: {test_id}")
                            else:
                                # If all else fails, try to find any time-like text in the slot
                                inner_text = slot.inner_text()
                                time_pattern = r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})"
                                time_match = re.search(time_pattern, inner_text)
                                
                                if time_match:
                                    start_time_str, end_time_str = time_match.groups()
                                    
                                    # Convert time strings to minutes
                                    start_h, start_m = map(int, start_time_str.split(":"))
                                    end_h, end_m = map(int, end_time_str.split(":"))
                                    
                                    start_minutes = start_h * 60 + start_m
                                    end_minutes = end_h * 60 + end_m
                                    
                                    logger.info(f"Extracted time from inner text: {start_time_str} to {end_time_str}")
                                else:
                                    raise ValueError("Could not find time information in the slot")
                    except Exception as e:
                        logger.error(f"Error getting time information: {str(e)}")
                        # Skip this slot if we can't determine time
                        continue
                    
                    # Skip if we still don't have valid time information
                    if start_minutes is None or end_minutes is None:
                        logger.error("Invalid time information for slot")
                        continue
                    
                    # Check if the slot matches preferences
                    if is_time_in_preferences(day_type, start_minutes, end_minutes):
                        start_time = minutes_to_time_str(start_minutes)
                        end_time = minutes_to_time_str(end_minutes)
                        
                        logger.info(f"Found matching slot: {court_name} on {date_str} at {start_time}-{end_time}")
                        
                        # Click on the slot to proceed to booking
                        slot.click()
                        
                        # Wait for the booking details to load
                        try:
                            # Wait for the booking form or submit button
                            form_selector = "form, #submit-booking, #continueButton, button.primary[type='submit']"
                            page.wait_for_selector(form_selector, timeout=10000)
                            logger.info("Booking details page loaded successfully")
                            
                            # Take a screenshot of the booking page
                            screenshot_path = f"booking_page_{date_str}_{start_time.replace(':', '')}.png"
                            page.screenshot(path=screenshot_path)
                            logger.info(f"Saved screenshot of booking page to {screenshot_path}")
                            
                            # Get the current URL before clicking any buttons
                            initial_booking_url = page.url
                            
                            # Extract relevant details from the URL or page content
                            # Look for resource ID and other booking parameters
                            resource_id = None
                            date_param = None
                            
                            try:
                                # Try to find these values in the URL or in hidden form fields
                                resource_id_element = page.query_selector("[name='ResourceID']")
                                resource_id = slot.get_attribute("data-resourceid")
                                if not resource_id and resource_id_element:
                                    resource_id = resource_id_element.get_attribute("value")
                                
                                # Extract data from data-test-id (format: booking-GUID|date|time)
                                test_id = slot.get_attribute("data-test-id")
                                if test_id:
                                    parts = test_id.split("|")
                                    if len(parts) >= 2:
                                        booking_id = parts[0].replace("booking-", "")
                                        date_param = parts[1]
                            except Exception as e:
                                logger.warning(f"Error extracting booking parameters: {str(e)}")
                            
                            # Log the extracted parameters
                            if resource_id:
                                logger.info(f"Resource ID: {resource_id}")
                            if date_param:
                                logger.info(f"Date parameter: {date_param}")
                            
                            # Use the initial URL which should work with user login
                            booking_url = initial_booking_url
                            logger.info(f"Initial booking URL: {booking_url}")
                            
                            # Create a direct booking URL if possible with the extracted parameters
                            direct_url = None
                            if "ClissoldParkHackney" in booking_url:
                                venue_part = "ClissoldParkHackney"
                            elif "LondonFieldsPark" in booking_url:
                                venue_part = "LondonFieldsPark"
                            else:
                                # Extract venue name from URL
                                venue_match = re.search(r"//[^/]+/([^/]+)/Booking", booking_url)
                                venue_part = venue_match.group(1) if venue_match else None
                            
                            if venue_part and date_param:
                                # Create a more reliable direct URL that should work when logged in
                                direct_url = f"https://clubspark.lta.org.uk/{venue_part}/Booking/BookByDate#?date={date_param}"
                                logger.info(f"Created direct booking URL: {direct_url}")
                            
                            # Send notification with both URLs
                            slot_info = {
                                "date": date_str,
                                "court": court_name,
                                "start_time": start_time,
                                "end_time": end_time,
                                "booking_url": direct_url or booking_url
                            }
                            
                            # Add booking instructions to the message
                            slot_info["additional_message"] = (
                                f"To book this court:\n"
                                f"1. Log in to ClubSpark first\n"
                                f"2. Then click the booking link\n"
                                f"3. Find the {court_name} court at {start_time}"
                            )
                            
                            notification_sent = send_pushover_notification(slot_info)
                            if notification_sent:
                                logger.info("Notification sent successfully. Stopping search as we found a matching slot.")
                                # Stop processing more slots after finding a match and sending notification
                                return
                            
                        except Exception as e:
                            logger.error(f"Error processing booking details: {str(e)}")
                            # If we couldn't process the booking details, try to get the current URL anyway
                            try:
                                booking_url = page.url
                                logger.info(f"Fallback to current URL: {booking_url}")
                                
                                # Send notification with the current URL as fallback
                                slot_info = {
                                    "date": date_str,
                                    "court": court_name,
                                    "start_time": start_time,
                                    "end_time": end_time,
                                    "booking_url": booking_url,
                                    "additional_message": "Please log in to ClubSpark first before using this link."
                                }
                                
                                notification_sent = send_pushover_notification(slot_info)
                                if notification_sent:
                                    logger.info("Notification sent with fallback URL. Stopping search.")
                                    return
                            except Exception as inner_e:
                                logger.error(f"Error with fallback notification: {str(inner_e)}")
                        
                        # Go back to the availability page to check other slots if we didn't return earlier
                        page.goto(url, wait_until="networkidle")
                        
                        # Wait for the booking calendar to reload
                        try:
                            page.wait_for_selector(".booking-sheet", timeout=30000)
                            logger.info("Booking calendar reloaded successfully")
                        except Exception as e:
                            logger.warning(f"Booking calendar not reloaded after returning to availability page: {str(e)}")
                            # Add a small delay to give the page more time to load
                            page.wait_for_timeout(5000)
                
                except Exception as e:
                    logger.error(f"Error processing slot: {str(e)}")
                    # Continue with next slot
                    page.goto(url, wait_until="networkidle")
        
        except Exception as e:
            logger.error(f"Error checking court availability: {str(e)}")
            
        finally:
            if 'browser' in locals():
                browser.close()
            logger.info("Completed court availability check")

if __name__ == "__main__":
    check_court_availability() 