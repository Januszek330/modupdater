import asyncio
import json
import discord
from discord.ext import commands

from commands.mod_commands import ModCommands
from core.updater import start_updater


with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)


class ModBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=config["application_id"]
        )

    async def setup_hook(self):
        print("Setup hook running")

        await self.add_cog(ModCommands(self, config))
        print("Cog loaded")

        guild = discord.Object(id=config["guild_id"])

        # 🔥 CRITICAL LINE
        self.tree.copy_global_to(guild=guild)

        # Optional one-time clean reset
        await self.tree.sync(guild=guild)

        print("Guild synced.")
        print("Guild commands:", self.tree.get_commands(guild=guild))

        start_updater(self, config)


bot = ModBot()


if __name__ == "__main__":
    asyncio.run(bot.start(config["token"]))
