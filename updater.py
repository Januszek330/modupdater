import asyncio
import discord
import json
from storage import load_storage, save_storage
from checkers import check_mod_updates

async def check_for_updates(bot):
    while True:
        print("[DEBUG] Running update check loop")
        data = load_storage()

        for gid, info in data.items():
            mods = info.get("mods", [])
            for i, mod in enumerate(mods):
                result = await check_mod_updates(mod)
                print(f"[DEBUG] Checked mod: {mod['url']}, result: {result}")

                if result:
                    channel = bot.get_channel(mod["channel_id"])
                    if not channel:
                        print(f"[WARNING] Channel ID {mod['channel_id']} not found.")
                        continue

                    with open('config.json') as f:
                        cfg = json.load(f)
                    template = cfg.get("template", "{mod_name} has updated! {url}")
                    role = discord.utils.get(channel.guild.roles, name="updates")
                    ping = f"<@&{role.id}>" if role else ""

                    msg = template.replace("{mod_name}", result["mod_name"]) \
                                  .replace("{platform}", result["platform"]) \
                                  .replace("{version}", result["version"]) \
                                  .replace("{url}", result["url"]) \
                                  .replace("<@&ROLE_ID>", ping)

                    print(f"[DEBUG] Sending message: {msg}")
                    await channel.send(msg)

                    # ✅ Save the new version to memory
                    data[gid]["mods"][i]["last_version"] = result["version"]

        save_storage(data)
        print("[DEBUG] Storage updated.")
        await asyncio.sleep(300)  # Check every 5 minutes

async def setup(bot):
    async def start_background_task():
        await bot.wait_until_ready()
        asyncio.create_task(check_for_updates(bot))

    bot.startup_task = start_background_task
