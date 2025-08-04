# modupdater
🛠️ Mod Update Checker Bot
A private Discord bot that monitors Minecraft mods for updates on CurseForge, Modrinth, and MrCrayfish. It automatically posts notifications in a Discord channel when new versions are detected.

✨ Features
Checks mods on:

CurseForge (via official API or Playwright fallback)

Modrinth (via official API)

MrCrayfish's Mod List (via HTML scraping)

Supports filtering by Minecraft versions and mod loaders

Scheduled update checks every 5 minutes

Lightweight and extensible design

🧰 Requirements
Python 3.11+

Playwright (for fallback when CurseForge API is unavailable)

A Discord bot token

Optional: CurseForge API Key

📦 Installation
Clone the repository

git clone https://github.com/yourusername/mod-update-checker-bot.git
cd mod-update-checker-bot

Install dependencies

pip install -r requirements.txt
playwright install

Configure config.json

{
  "discord_token": "YOUR_DISCORD_BOT_TOKEN",
  "curseforge_api_key": "YOUR_CURSEFORGE_API_KEY",
  "check_interval": 300,
  "channel_id": "YOUR_CHANNEL_ID"
}

Run the bot

python bot.py

🛡 License
This project is licensed under the MIT License.

🙋 FAQ
Q: Do I need a CurseForge API key?
A: It's recommended. If not provided, the bot uses Playwright to scrape data as a fallback.

Q: Can I make it public?
A: Sure, but be aware of CurseForge’s API Terms.
