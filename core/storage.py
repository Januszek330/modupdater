import json
import os

STORAGE_FILE = "storage.json"
CURRENT_VERSION = 1


def _default_structure():
    return {
        "storage_version": CURRENT_VERSION,
        "guilds": {},
        "settings": {
            "max_mods_per_guild": 1000
        }
    }


async def load_storage():
    if not os.path.exists(STORAGE_FILE):
        data = _default_structure()
        await save_storage(data)
        return data

    with open(STORAGE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Migration check
    if "storage_version" not in data:
        data = await _migrate_legacy(data)

    return data


async def save_storage(data):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


async def _migrate_legacy(old_data):
    new_data = _default_structure()

    for key, value in old_data.items():
        if key.isdigit():
            new_data["guilds"][key] = value

    await save_storage(new_data)
    return new_data
