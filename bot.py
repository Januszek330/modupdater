import discord
from discord.ext import commands
import json
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

async def load_config():
    with open("config.json") as f:
        return json.load(f)

async def setup_commands(bot):
    from commands import setup as setup_commands_module
    await setup_commands_module(bot)

async def setup_updater(bot):
    from updater import setup as setup_updater_module
    await setup_updater_module(bot)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    if hasattr(bot, "startup_task"):
        try:
            await bot.startup_task()
        except Exception as e:
            print(f"[ERROR] Startup task failed: {e}")

async def main():
    config = await load_config()

    try:
        await setup_commands(bot)
    except Exception as e:
        print(f"[ERROR] Failed to load commands: {e}")

    try:
        await setup_updater(bot)
    except Exception as e:
        print(f"[ERROR] Failed to set up updater: {e}")

    try:
        await bot.start(config["token"])
    except Exception as e:
        print(f"[ERROR] Bot failed to start: {e}")

if __name__ == "__main__":
    asyncio.run(main())
