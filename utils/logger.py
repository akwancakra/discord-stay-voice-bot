import logging
import os
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from colorama import init, Fore, Style

# Initialize colorama for Windows and other systems
init(autoreset=True)

# Project Paths
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"

# Ensure logs directory exists
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE = LOGS_DIR / "bot.log"

# Define Log Colors
COLORS = {
    "DEBUG": Fore.BLUE,
    "INFO": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.RED + Style.BRIGHT,
}

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        log_color = COLORS.get(record.levelname, "")
        message = super().format(record)
        if log_color:
            # Color the log level and the message for the console
            levelname_colored = f"{log_color}{record.levelname:<8}{Style.RESET_ALL}"
            message = message.replace(record.levelname, levelname_colored)
        return message

def setup_logger():
    logger = logging.getLogger("StayVoiceBot")
    logger.setLevel(logging.DEBUG)

    # Prevent adding duplicate handlers if logger is configured multiple times
    if logger.handlers:
        return logger

    # Console Handler (Colored)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File Handler (Plain text, rotated by size: 5MB max, keeping 3 backups)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"[Logger Warning] Failed to initialize file logging: {e}")

    return logger

logger = setup_logger()
