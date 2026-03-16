# modupdater 
Mod Update Checker
A private Discord bot that monitors Minecraft mods for updates on Modrinth. It automatically posts notifications in a Discord channel when new versions are detected.

Features
Checks mods on:
Modrinth (via official API)

Supports filtering by Minecraft versions and mod loaders

Scheduled update checks every 5 minutes

Lightweight and extensible design

Requirements
Python 3.11+

Playwright (for fallback when CurseForge API is unavailable)

A Discord bot token

Optional: CurseForge API Key

Installation
Clone the repository

git clone https://github.com/yourusername/mod-update-checker-bot.git
cd mod-update-checker-bot

Install dependencies

pip install -r requirements.txt
playwright install

Configure config.json

Run the bot

python bot.py

License
This project is licensed under the MIT License.
