import json
import os
import time

CACHE_FILE = "cache.json"


def _default_cache():
    return {"modrinth": {}}


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return _default_cache()

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_cached(slug, key, ttl):
    cache = load_cache()
    entry = cache["modrinth"].get(slug)

    if not entry:
        return None

    if time.time() > entry["expires"]:
        return None

    return entry.get(key)


def set_cached(slug, key, value, ttl):
    cache = load_cache()

    if slug not in cache["modrinth"]:
        cache["modrinth"][slug] = {}

    cache["modrinth"][slug][key] = value
    cache["modrinth"][slug]["expires"] = time.time() + ttl

    save_cache(cache)
