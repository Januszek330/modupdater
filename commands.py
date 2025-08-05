import json
import os
from checkers import normalize_url

STORAGE_FILE = 'storage.json'

VALID_LOADERS = ["forge", "fabric", "neoforge", "quilt", "all"]
VALID_MC_VERSIONS = [
    "1.21.8", "1.21.7", "1.21.6", "1.21.5", "1.21.4", "1.21.3", "1.21.2", "1.21.1", "1.21", "1.20.6", "1.20.5", "1.20.4", "1.20.2", "1.20.1", "1.20", "1.19.4", "1.19.3", "1.19.2", "1.19.1", "1.19",
    "1.18.2", "1.18.1", "1.18", "1.17.1", "1.17", "1.16.5", "1.16.4", "1.16.3", "1.16.2", "1.16.1", "1.16",
    "1.15.2", "1.15.1", "1.15", "1.14.4", "1.14.3", "1.14.2", "1.14.1", "1.14",
    "1.13.2", "1.13.1", "1.13", "1.12.2", "1.12.1", "1.12",
    "1.11.2", "1.11.1", "1.11", "1.10.2", "1.10.1", "1.10",
    "1.9.4", "1.9.2", "1.9", "1.8.9", "1.8.8", "1.8.7", "1.8.1", "1.8",
    "1.7.10", "1.7.2", "all"
]

if not os.path.exists(STORAGE_FILE):
    with open(STORAGE_FILE, 'w') as file:
        json.dump({}, file)

def load_storage():
    with open(STORAGE_FILE, 'r') as file:
        return json.load(file)

def save_storage(data):
    with open(STORAGE_FILE, 'w') as file:
        json.dump(data, file, indent=2)

async def setup(bot):
    @bot.command()
    async def add(ctx, url, mc_versions=None, loaders=None):
        data = load_storage()
        gid = str(ctx.guild.id)
        if gid not in data:
            data[gid] = {"mods": []}

        url = normalize_url(url.strip())

        mc_versions_list = [v.strip().lower() for v in mc_versions.split(',')] if mc_versions else ["all"]
        loaders_list = [l.strip().lower() for l in loaders.split(',')] if loaders else ["all"]

        invalid_loaders = [l for l in loaders_list if l not in VALID_LOADERS]
        if invalid_loaders:
            return await ctx.send(f"Invalid loader(s): {', '.join(invalid_loaders)}\nAllowed: {', '.join(VALID_LOADERS)}")

        invalid_versions = [v for v in mc_versions_list if v not in VALID_MC_VERSIONS]
        if invalid_versions:
            return await ctx.send(f"Invalid Minecraft version(s): {', '.join(invalid_versions)}\nAllowed: {', '.join(VALID_MC_VERSIONS)}")

        existing = data[gid]["mods"]
        already_added = any(
            mod['url'] == url and set(mod['mc_versions']) == set(mc_versions_list) and set(mod['loaders']) == set(loaders_list)
            for mod in existing)
        if already_added:
            return await ctx.send("This mod with those filters is already being tracked.")

        data[gid]["mods"].append({
            "url": url,
            "mc_versions": mc_versions_list,
            "loaders": loaders_list,
            "last_version": None,
            "channel_id": ctx.channel.id
        })

        save_storage(data)
        await ctx.send(f"Added: {url} (MC: {', '.join(mc_versions_list)}, Loaders: {', '.join(loaders_list)})")

    @bot.command()
    async def remove(ctx, url):
        url = normalize_url(url.strip())
        data = load_storage()
        gid = str(ctx.guild.id)
        if gid in data:
            before = len(data[gid]['mods'])
            data[gid]['mods'] = [m for m in data[gid]['mods'] if m['url'] != url]
            after = len(data[gid]['mods'])
            save_storage(data)
            await ctx.send(f"Removed {before - after} mod(s) with that URL.")

    @bot.command(name="listmods")
    async def listmods(ctx):
        data = load_storage()
        gid = str(ctx.guild.id)
        if gid not in data or not data[gid]["mods"]:
            return await ctx.send("No mods are being tracked.")

        msg = "Currently tracked mods:\n"
        for mod in data[gid]["mods"]:
            msg += f"- {mod['url']} (MC: {', '.join(mod['mc_versions'])}, Loaders: {', '.join(mod['loaders'])})\n"

        await ctx.send(msg)
