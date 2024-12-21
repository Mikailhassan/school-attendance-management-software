import logging
from logging.handlers import RotatingFileHandler
import os

# Define log directory and file
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, 'app.log')

# Create a logger
logger = logging.getLogger("SchoolAttendanceLogger")
logger.setLevel(logging.DEBUG)

# Create a file handler that logs messages to a file, with rotation after 5MB
file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
file_handler.setLevel(logging.DEBUG)

# Create a console handler to output logs to the console as well
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create log formatters for both console and file
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

