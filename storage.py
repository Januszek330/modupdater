# storage.py
import json

FILENAME = "storage.json"

def load_storage():
    try:
        with open(FILENAME, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_storage(data):
    with open(FILENAME, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
