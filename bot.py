import asyncio
import json
import os
import discord
from discord.ext import commands

from core.logger import logger
from commands.mod_commands import ModCommands
from core.updater import start_updater

# Resolve absolute directory to prevent execution directory mismatch errors
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    logger.info("Configuration loaded successfully from config.json")
except Exception as e:
    logger.error(f"Failed to load configuration file at path: {CONFIG_PATH}. Error: {e}")
    raise e


class ModBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            application_id=config["application_id"],
            help_command=None
        )
        self.dev_id = config["owner_id"]

    async def setup_hook(self):
        logger.info("Initializing system-wide setup hook...")

        # Load Cogs
        await self.add_cog(ModCommands(self, config))
        logger.info("Command module 'ModCommands' loaded successfully.")

        guild = discord.Object(id=config["guild_id"])

        # Sync command tree
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        logger.info(f"Slash command tree successfully synchronized to testing Guild ID: {config['guild_id']}.")

        # Spin up background updater loops
        start_updater(self, config)

    async def on_ready(self):
        logger.info(f"Bot successfully connected to Discord! Logged in as user: {self.user} (ID: {self.user.id})")

    async def close(self):
        logger.info("Initiating websocket gateway shutdown and cleaning resources...")
        await super().close()
        logger.info("Bot cleanly shut down. Process terminated safely.")


bot = ModBot()

if __name__ == "__main__":
    logger.info("Starting up the ModCheck bot process...")
    try:
        asyncio.run(bot.start(config["token"]))
    except Exception as e:
        logger.critical(f"Fatal process exception encountered on execution loop: {e}")