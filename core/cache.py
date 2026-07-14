import json
import os
import time
from core.logger import logger

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CACHE_FILE = os.path.join(DATA_DIR, "cache.json")


def _default_cache():
    return {"modrinth": {}}


def load_cache():
    try:
        if not os.path.exists(CACHE_FILE):
            return _default_cache()
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed loading caching storage file: {e}")
        return _default_cache()


def save_cache(data):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed writing cache serialization payload to disk: {e}")


def get_cached(slug, key, ttl):
    cache = load_cache()
    entry = cache["modrinth"].get(slug)

    if not entry:
        return None

    if time.time() > entry["expires"]:
        return None

    return entry.get(key)


def set_cached(slug, key, value, ttl):
    try:
        cache = load_cache()

        if slug not in cache["modrinth"]:
            cache["modrinth"][slug] = {}

        cache["modrinth"][slug][key] = value
        cache["modrinth"][slug]["expires"] = time.time() + ttl

        save_cache(cache)
    except Exception as e:
        logger.error(f"Failed setting cache metrics for project {slug}: {e}")