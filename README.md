# Tennis Court Booking Automation

This project automates the process of checking for available tennis courts at London Fields Park and sends instant notifications when slots matching your preferences are available.

## Features

- Checks for available tennis courts at London Fields Park (https://clubspark.lta.org.uk/LondonFieldsPark)
- Runs every minute between 9:55 PM and 10:05 PM UK time daily
- Looks for courts available exactly 7 days ahead
- Filters available slots based on specified preferences:
  - Wednesdays between 12:00-14:00 or at 8:00 AM
  - Weekdays after 18:00
  - Any time on weekends (maximum 2 hours)
- Sends instant push notifications to your iPhone with booking URLs using Pushover
- Deployable to Render.com

## Requirements

- Python 3.7+
- Chrome browser (for Selenium WebDriver)
- Pushover account and application (for notifications)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/tennis-booking-automation.git
   cd tennis-booking-automation
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up Pushover:
   - Create an account at https://pushover.net/
   - Create a new application at https://pushover.net/apps/build
   - Note your User Key and API Token

4. Create a `.env` file based on the `env.example` template:
   ```
   cp env.example .env
   ```

5. Edit the `.env` file with your Pushover configuration:
   ```
   PUSHOVER_USER_KEY=your_user_key_here
   PUSHOVER_API_TOKEN=your_api_token_here
   ```

## Usage

### Running Locally

To run the scheduler locally:

```
python scheduler.py
```

This will start the scheduler, which will check for available courts every minute between 9:55 PM and 10:05 PM UK time.

### Running as a Web Application

To run as a Flask web application:

```
python app.py
```

The application will be accessible at `http://localhost:5000`.

## Deployment to Render.com

1. Create a new Web Service on Render.com.
2. Link your GitHub repository.
3. Set the following configuration:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
4. Add environment variables for your Pushover credentials:
   - `PUSHOVER_USER_KEY`
   - `PUSHOVER_API_TOKEN`
5. Deploy the service.

## How It Works

1. At the scheduled time, the script checks the London Fields Park booking website.
2. It looks for available slots matching your preferences.
3. When a matching slot is found, the script clicks on it to get the booking URL.
4. A push notification is sent to your iPhone with the booking URL.
5. You can then tap the notification to complete the booking process immediately.

## Customization

You can customize the time preferences by editing the `PREFERENCES` dictionary in the `tennis_booking.py` file:

```python
PREFERENCES = {
    "wednesday": [(8*60, 8*60+60), (12*60, 14*60)],  # 8:00-9:00 AM or 12:00-14:00
    "weekday": [(18*60, 22*60)],  # After 18:00
    "weekend": [(8*60, 22*60)]  # Any time (max 2 hours)
}
```

## License

MIT
