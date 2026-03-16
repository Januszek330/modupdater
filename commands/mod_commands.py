import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from core.storage import load_storage, save_storage
from services.modrinth import get_project, get_versions, normalize_slug


class ModCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, config: dict):
        self.bot = bot
        self.config = config
        self.bot.dev_id = config["owner_id"]

    # -------------------------
    # Permission Checks
    # -------------------------

    def mod_only(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.manage_guild

    def dev_only(interaction: discord.Interaction) -> bool:
        return interaction.user.id == interaction.client.dev_id

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction, error):
        if isinstance(error, app_commands.CheckFailure):
            msg = "You don't have permission to use this command."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)

    # -------------------------
    # ADD
    # -------------------------

    @app_commands.command(name="add", description="Track a Modrinth project.")
    @app_commands.describe(
        project="Slug or Modrinth URL",
        mc_versions="Comma separated MC versions (optional)",
        loaders="Comma separated loaders (optional)",
        release_type="release, beta or alpha (optional)",
        channel="Custom update channel (optional)"
    )
    async def add(
            self,
            interaction: discord.Interaction,
            project: str,
            mc_versions: Optional[str] = None,
            loaders: Optional[str] = None,
            release_type: Optional[str] = "release",
            channel: Optional[discord.TextChannel] = None
    ):
        await interaction.response.defer()

        project_data = await get_project(project)
        if not project_data:
            return await interaction.followup.send("Project not found.", ephemeral=True)

        data = await load_storage()
        gid = str(interaction.guild.id)

        data.setdefault(gid, {"mods": []})
        mods = data[gid]["mods"]

        slug = project_data["slug"]

        if any(m["slug"] == slug for m in mods):
            return await interaction.followup.send("Already tracked.", ephemeral=True)

        parsed_mc = []
        parsed_loaders = []

        if mc_versions:
            parsed_mc = [v.strip() for v in mc_versions.split(",") if v.strip()]

        if loaders:
            parsed_loaders = [l.strip().lower() for l in loaders.split(",") if l.strip()]

        if release_type not in ["release", "beta", "alpha"]:
            release_type = "release"

        mods.append({
            "slug": slug,
            "title": project_data["title"],
            "project_type": project_data["project_type"],
            "mc_versions": parsed_mc,
            "loaders": parsed_loaders,
            "release_type": release_type,
            "last_version": None,
            "channel_id": channel.id if channel else None
        })

        await save_storage(data)

        await interaction.followup.send(
            f"Now tracking **{project_data['title']}**."
        )

    @app_commands.command(name="forcecheck", description="Force an update check.")
    @app_commands.check(dev_only)
    async def forcecheck(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        from core.updater import run_update_cycle
        await run_update_cycle(self.bot, self.config)
        await interaction.followup.send("Update check complete.", ephemeral=True)

    @app_commands.command(name="setrole", description="Set update ping role.")
    @app_commands.check(mod_only)
    async def setrole(self, interaction: discord.Interaction, role: discord.Role):
        data = await load_storage()
        gid = str(interaction.guild.id)

        data.setdefault(gid, {"mods": []})
        data[gid]["role_id"] = role.id

        await save_storage(data)
        await interaction.response.send_message("Role set.", ephemeral=True)

    @app_commands.command(name="setchannel", description="Set default update channel.")
    @app_commands.check(mod_only)
    async def setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        data = await load_storage()
        gid = str(interaction.guild.id)

        data.setdefault(gid, {"mods": []})
        data[gid]["default_channel"] = channel.id

        await save_storage(data)
        await interaction.response.send_message("Default channel set.", ephemeral=True)

    @app_commands.command(name="backup", description="Create a backup.")
    @app_commands.check(dev_only)
    async def backup(self, interaction: discord.Interaction):
        import os
        import shutil
        from datetime import datetime

        await interaction.response.defer(ephemeral=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        folder = os.path.join("backups", timestamp)

        os.makedirs(folder, exist_ok=True)

        shutil.copy("storage.json", os.path.join(folder, "storage.json"))
        shutil.copy("config.json", os.path.join(folder, "config.json"))

        await interaction.followup.send(f"Backup created: `{folder}`", ephemeral=True)

    @app_commands.command(name="info", description="Show bot info.")
    async def info(self, interaction: discord.Interaction):
        data = await load_storage()
        total_mods = sum(len(g.get("mods", [])) for g in data.values())

        embed = discord.Embed(
            title="ModCheck Info",
            color=discord.Color.blue()
        )

        embed.add_field(name="Version", value=self.config["info"]["version"])
        embed.add_field(name="Owner", value=f"<@{self.bot.dev_id}>")
        embed.add_field(name="Tracked Mods", value=str(total_mods))
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)))

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="edit", description="Edit a tracked mod.")
    async def edit(
            self,
            interaction: discord.Interaction,
            project: str,
            mc_versions: Optional[str] = None,
            loaders: Optional[str] = None,
            release_type: Optional[str] = None,
            channel: Optional[discord.TextChannel] = None
    ):
        slug = normalize_slug(project)

        data = await load_storage()
        gid = str(interaction.guild.id)

        mods = data.get(gid, {}).get("mods", [])

        mod = next((m for m in mods if m["slug"] == slug), None)

        if not mod:
            return await interaction.response.send_message(
                "Mod not found.",
                ephemeral=True
            )

        if mc_versions is not None:
            mod["mc_versions"] = [v.strip() for v in mc_versions.split(",") if v.strip()]

        if loaders is not None:
            mod["loaders"] = [l.strip().lower() for l in loaders.split(",") if l.strip()]

        if release_type in ["release", "beta", "alpha"]:
            mod["release_type"] = release_type

        if channel is not None:
            mod["channel_id"] = channel.id

        await save_storage(data)

        await interaction.response.send_message("Mod updated.", ephemeral=True)

    # -------------------------
    # REMOVE
    # -------------------------

    @app_commands.command(name="remove", description="Stop tracking a project.")
    async def remove(self, interaction: discord.Interaction, project: str):
        slug = normalize_slug(project)

        data = await load_storage()
        gid = str(interaction.guild.id)

        if gid not in data or not data[gid].get("mods"):
            return await interaction.response.send_message(
                "No mods tracked.",
                ephemeral=True
            )

        mods = data[gid]["mods"]
        new_mods = [m for m in mods if m["slug"] != slug]

        if len(mods) == len(new_mods):
            return await interaction.response.send_message(
                "Mod not found.",
                ephemeral=True
            )

        data[gid]["mods"] = new_mods
        await save_storage(data)

        await interaction.response.send_message(
            f"Stopped tracking `{slug}`.",
            ephemeral=True
        )

    # -------------------------
    # LIST
    # -------------------------

    @app_commands.command(name="list", description="List tracked projects.")
    async def list_projects(
        self,
        interaction: discord.Interaction,
        project_type: Optional[str] = None,
        loader: Optional[str] = None,
        mc_version: Optional[str] = None
    ):
        data = await load_storage()
        gid = str(interaction.guild.id)

        if gid not in data or not data[gid].get("mods"):
            return await interaction.response.send_message(
                "No mods tracked.",
                ephemeral=True
            )

        mods = data[gid]["mods"]

        if project_type:
            mods = [m for m in mods if m["project_type"] == project_type]

        if loader:
            mods = [m for m in mods if loader in m["loaders"]]

        if mc_version:
            mods = [m for m in mods if mc_version in m["mc_versions"]]

        if not mods:
            return await interaction.response.send_message(
                "No matching mods found.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="Tracked Mods",
            color=discord.Color.blue()
        )

        for mod in mods:
            versions = await get_versions(mod["slug"])
            newest = versions[0]["version_number"] if versions else "Unknown"

            embed.add_field(
                name=mod["title"],
                value=(
                    f"Slug: `{mod['slug']}`\n"
                    f"Link: https://modrinth.com/project/{mod['slug']}\n"
                    f"MC: {', '.join(mod['mc_versions']) or 'Any'}\n"
                    f"Loaders: {', '.join(mod['loaders']) or 'Any'}\n"
                    f"Newest: `{newest}`"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed)
