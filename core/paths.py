import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"

CONFIG_PATH = BASE_DIR / "config.json"
STORAGE_PATH = DATA_DIR / "storage.db"  # Pointing to the new SQLite database
CACHE_PATH = DATA_DIR / "cache.json"

def initialize_environment():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

initialize_environment()
