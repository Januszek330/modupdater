import logging
import os
from logging.handlers import RotatingFileHandler

# Resolve absolute paths from project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

LOG_FILE = os.path.join(DATA_DIR, "bot.log")

# Setup clean log formatting
FORMATTER = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Root level logger configuration
logger = logging.getLogger("ModCheck")
logger.setLevel(logging.INFO)

# Avoid duplicate logs if handlers already attached (hot-reloads)
if not logger.handlers:
    # Console stream output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(FORMATTER)
    logger.addHandler(console_handler)

    # 5MB Rotated output file stream
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(FORMATTER)
    logger.addHandler(file_handler)

logger.info("Logging infrastructure initialized correctly.")