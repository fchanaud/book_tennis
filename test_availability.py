#!/usr/bin/env python3

"""
This script allows manual testing of the court availability check
without waiting for the scheduled time.
"""

import os
import logging
from tennis_booking import check_court_availability

# Set up logging for testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting test of court availability check")
    try:
        check_court_availability()
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}") 