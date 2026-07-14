import asyncio
from core.logger import logger
from core.storage import load_storage, save_storage
from services.modrinth import get_versions


def start_updater(bot, config):
    bot.loop.create_task(updater_loop(bot, config))
    logger.info("Mod update checks scheduler registered and running correctly.")


async def updater_loop(bot, config):
    await bot.wait_until_ready()
    interval = config.get("check_interval_seconds", 300)

    while not bot.is_closed():
        try:
            logger.info("Starting background modpack update verification sequence...")
            await run_update_cycle(bot, config)
            logger.info("Background update checks complete. Sleep cycle initiated.")
        except Exception as e:
            logger.error(f"Exception encountered inside update verification loop: {e}")

        await asyncio.sleep(interval)


async def run_update_cycle(bot, config):
    data = await load_storage()
    guilds = data.get("guilds", {})

    for guild_id, guild_data in guilds.items():
        mods = guild_data.get("mods", [])
        default_channel_id = guild_data.get("default_channel")

        for mod in mods:
            slug = mod["slug"]
            try:
                # Modrinth Fetch
                versions = await get_versions(slug)
                if not versions:
                    continue

                newest_version = versions[0]
                newest_version_id = newest_version["id"]
                newest_version_number = newest_version["version_number"]

                # If this is the initial scan or the version changed
                if mod.get("last_version") != newest_version_id:
                    if mod.get("last_version") is not None:
                        # Log and notify the discord channel about the update
                        logger.info(
                            f"Update detected for '{mod['title']}'! Old: {mod.get('last_version')}, New: {newest_version_number}")
                        await notify_guild(bot, guild_id, default_channel_id, mod, newest_version)

                    mod["last_version"] = newest_version_id
            except Exception as api_err:
                logger.error(f"Modrinth API failure checking updates for {slug}: {api_err}")

    await save_storage(data)


async def notify_guild(bot, guild_id, default_channel_id, mod, version_data):
    try:
        channel_id = mod.get("channel_id") or default_channel_id
        if not channel_id:
            return

        channel = bot.get_channel(int(channel_id))
        if not channel:
            return

        embed = discord.Embed(
            title=f"Update Detected: {mod['title']}",
            description=f"New version **{version_data['version_number']}** is now available!",
            url=f"https://modrinth.com/project/{mod['slug']}",
            color=discord.Color.green()
        )
        await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Failed to post update notification to guild {guild_id}: {e}")