import sqlite3
import json
import os
from core.logger import logger

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_FILE = os.path.join(DATA_DIR, "storage.db")

def get_db_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guilds (
            guild_id TEXT PRIMARY KEY,
            channel_id INTEGER,
            role_id INTEGER,
            default_channel INTEGER,
            mods TEXT
        )
    """)

    # Set default settings
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('max_mods_per_guild', '1000')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('storage_version', '1')")
    conn.commit()
    conn.close()

# Initialize DB on import to make sure schemas are up to date
init_db()

async def load_storage():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Load Settings
        cursor.execute("SELECT key, value FROM settings")
        settings_rows = cursor.fetchall()
        settings = {}
        for row in settings_rows:
            try:
                settings[row['key']] = int(row['value'])
            except ValueError:
                settings[row['key']] = row['value']

        # Load Guilds
        cursor.execute("SELECT guild_id, channel_id, role_id, default_channel, mods FROM guilds")
        guild_rows = cursor.fetchall()
        guilds = {}
        for row in guild_rows:
            guilds[row['guild_id']] = {
                "channel_id": row['channel_id'],
                "role_id": row['role_id'],
                "default_channel": row['default_channel'],
                "mods": json.loads(row['mods']) if row['mods'] else []
            }

        conn.close()

        return {
            "storage_version": settings.get("storage_version", 1),
            "guilds": guilds,
            "settings": {
                "max_mods_per_guild": settings.get("max_mods_per_guild", 1000)
            }
        }
    except Exception as e:
        logger.error(f"SQLite reading error inside load_storage wrapper: {e}")
        return {
            "storage_version": 1,
            "guilds": {},
            "settings": {"max_mods_per_guild": 1000}
        }

async def save_storage(data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Save Settings
        if "settings" in data:
            for k, v in data["settings"].items():
                cursor.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (k, str(v))
                )

        # Save Guilds
        guilds = data.get("guilds", {})

        # Remove deleted guilds
        if guilds:
            placeholders = ",".join("?" for _ in guilds.keys())
            cursor.execute(f"DELETE FROM guilds WHERE guild_id NOT IN ({placeholders})", list(guilds.keys()))
        else:
            cursor.execute("DELETE FROM guilds")

        for gid, gdata in guilds.items():
            cursor.execute(
                """
                INSERT OR REPLACE INTO guilds (guild_id, channel_id, role_id, default_channel, mods)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    gid,
                    gdata.get("channel_id"),
                    gdata.get("role_id"),
                    gdata.get("default_channel"),
                    json.dumps(gdata.get("mods", []))
                )
            )

        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"SQLite writing error inside save_storage wrapper: {e}")
