# Tennis Court Booking Automation

This application automatically checks for available tennis courts at London Fields Park and sends notifications via Pushover when courts matching specific time preferences are found.

## Deployment on Render

1. Create a new Render account if you don't have one: https://render.com
2. Create a new Web Service
3. Connect your GitHub repository
4. Use the following settings:
   - **Build Command**: `pip install -r requirements.txt && python -m playwright install chromium`
   - **Start Command**: `gunicorn server:app --timeout 120`

5. Add the following environment variables:
   - `PUSHOVER_USER_KEY`: Your Pushover user key
   - `PUSHOVER_API_TOKEN`: Your Pushover API token

## Local Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   python -m playwright install chromium
   ```

2. Create a `.env` file with your Pushover credentials:
   ```
   PUSHOVER_USER_KEY=your_user_key
   PUSHOVER_API_TOKEN=your_api_token
   ```

3. Run the application:
   ```
   python server.py
   ```

## Endpoints

- `/`: Health check endpoint
- `/run-check`: Manually trigger a court availability check 