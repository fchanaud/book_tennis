# Tennis Court Booking Automation

This application automatically checks for available tennis courts at London Fields Park and sends notifications via Pushover when courts matching specific time preferences are found.

## Deployment on Render

1. Create a new Render account if you don't have one: https://render.com
2. Create a new Web Service
3. Connect your GitHub repository
4. Use the following settings:
   - **Environment**: Python
   - **Build Command**: `./build.sh`
   - **Start Command**: `./start.sh`

5. Add the following environment variables:
   - `PUSHOVER_USER_KEY`: Your Pushover user key
   - `PUSHOVER_API_TOKEN`: Your Pushover API token
   - `PYTHONPATH`: `.`
   - `PORT`: `10000`
   - `PYTHON_VERSION`: `3.11.0`

## Troubleshooting Render Deployment

If you experience issues with the Render deployment:

1. Ensure the build.sh and start.sh scripts are executable
   ```
   git update-index --chmod=+x build.sh
   git update-index --chmod=+x start.sh
   ```

2. Check the deployment logs for specific errors
3. If gunicorn is not found, try updating the start command to:
   ```
   python -m gunicorn server:app --timeout 120 --bind 0.0.0.0:$PORT
   ```

4. Make sure the proper Python version is set in both runtime.txt and the PYTHON_VERSION environment variable

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