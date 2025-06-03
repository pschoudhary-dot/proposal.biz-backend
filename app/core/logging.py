"""
Logging configuration for the Proposal Biz application.
"""
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.core.config import settings


class CustomFormatter(logging.Formatter):
    """
    Custom formatter with colored output for console logging.
    """
    # ANSI color codes
    GREY = "\x1b[38;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    # Format strings for different log levels
    FORMATS = {
        logging.DEBUG: f"{GREY}[%(asctime)s] [%(levelname)s] %(name)s: %(message)s{RESET}",
        logging.INFO: f"{GREEN}[%(asctime)s] [%(levelname)s] %(name)s: %(message)s{RESET}",
        logging.WARNING: f"{YELLOW}[%(asctime)s] [%(levelname)s] %(name)s: %(message)s{RESET}",
        logging.ERROR: f"{RED}[%(asctime)s] [%(levelname)s] %(name)s: %(message)s{RESET}",
        logging.CRITICAL: f"{BOLD_RED}[%(asctime)s] [%(levelname)s] %(name)s: %(message)s{RESET}",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging():
    """
    Set up logging for the application.
    
    Creates a logs directory if it doesn't exist and configures both console
    and file logging with appropriate formatters.
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Create a unique log file for each run
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"proposal_biz_{current_time}.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CustomFormatter())
    console_handler.setLevel(logging.INFO)
    
    # File handler with detailed output
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10485760,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    file_handler.setLevel(logging.DEBUG)
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Create a logger for the application
    logger = logging.getLogger("proposal_biz")
    
    # Log startup message
    logger.info(f"Starting {settings.PROJECT_NAME}")
    logger.info(f"Log file: {log_file}")
    
    return logger

# Create the application logger
logger = setup_logging()