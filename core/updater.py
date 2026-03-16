import asyncio
from core.storage import load_storage, save_storage
from core.cache import get_cached, set_cached
from services.modrinth import get_versions
from core.embeds import build_update_embed


async def run_update_cycle(bot, config):
    data = await load_storage()
    ttl = config.get("update_interval_minutes", 5) * 60

    for guild_id, guild_data in data["guilds"].items():
        mods = guild_data.get("mods", [])

        for mod in mods:
            slug = mod["slug"]

            versions = get_cached(slug, "versions", ttl)
            if not versions:
                versions = await get_versions(slug)
                if versions:
                    set_cached(slug, "versions", versions, ttl)

            if not versions:
                continue

            latest = versions[0]
            version_number = latest["version_number"]

            if mod.get("last_version") == version_number:
                continue

            mod["last_version"] = version_number

            channel_id = mod.get("channel_id") or guild_data.get("default_channel")
            if not channel_id:
                continue

            channel = bot.get_channel(channel_id)
            if not channel:
                continue

            embed = build_update_embed(
                name=mod["title"],
                version=version_number,
                game_versions=latest.get("game_versions", []),
                loaders=latest.get("loaders", []),
                url=f"https://modrinth.com/project/{slug}",
                project_type=mod["project_type"],
                version_type=latest.get("version_type", "release")
            )

            content = ""
            if guild_data.get("role_id"):
                content = f"<@&{guild_data['role_id']}>"

            await channel.send(content=content, embed=embed)

    await save_storage(data)


async def check_updates(bot, config):
    interval = config.get("update_interval_minutes", 5)

    while True:
        await run_update_cycle(bot, config)
        await asyncio.sleep(interval * 60)


def start_updater(bot, config):
    bot.loop.create_task(check_updates(bot, config))
