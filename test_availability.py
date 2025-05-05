#!/usr/bin/env python3

"""
This script allows manual testing of the court availability check
without waiting for the scheduled time.
"""

import logging
from tennis_booking import check_court_availability

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test.log')
    ]
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting manual test of court availability check")
    check_court_availability()
    logger.info("Manual test completed") 