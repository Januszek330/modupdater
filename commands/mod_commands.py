import os
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from core.logger import logger, LOG_FILE
from core.storage import load_storage, save_storage
from services.modrinth import get_project, get_versions, normalize_slug, search_projects

# Centralized help configuration mapping
HELP_COMMANDS = {
    "add": {
        "title": "/add",
        "description": "Track a new Modrinth project in this guild with dynamic name lookup.",
        "usage": "/add project:<name_or_slug_or_url> [mc_versions:<versions>] [loaders:<loaders>] [release_type:<type>] [channel:<channel>]",
        "permissions": "None (Everyone)",
        "example": "/add project:create-aeronautics mc_versions:1.20.1 loaders:forge,neoforge"
    },
    "edit": {
        "title": "/edit",
        "description": "Edit filtering and text channel settings of an actively tracked mod.",
        "usage": "/edit project:<slug> [mc_versions:<versions>] [loaders:<loaders>] [release_type:<type>] [channel:<channel>]",
        "permissions": "None (Everyone)",
        "example": "/edit project:create-aeronautics mc_versions:1.21.1"
    },
    "remove": {
        "title": "/remove",
        "description": "Stop tracking a project and delete it from local server monitoring.",
        "usage": "/remove project:<slug>",
        "permissions": "None (Everyone)",
        "example": "/remove project:create-aeronautics"
    },
    "list": {
        "title": "/list",
        "description": "List all actively tracked modpack projects in the current server.",
        "usage": "/list [project_type:<type>] [loader:<loader>] [mc_version:<version>]",
        "permissions": "None (Everyone)",
        "example": "/list loader:neoforge mc_version:1.21.1"
    },
    "setrole": {
        "title": "/setrole",
        "description": "[Mod Only] Sets the selected role to be mentioned when a mod updates.",
        "usage": "/setrole role:<role>",
        "permissions": "Manage Guild (Moderator)",
        "example": "/setrole role:@ModpackPing"
    },
    "setchannel": {
        "title": "/setchannel",
        "description": "[Mod Only] Sets the default text channel where update notifications are sent.",
        "usage": "/setchannel channel:<channel>",
        "permissions": "Manage Guild (Moderator)",
        "example": "/setchannel channel:#game-updates"
    },
    "info": {
        "title": "/info",
        "description": "Show system operational logs, tracked stats, and software versions.",
        "usage": "/info",
        "permissions": "None (Everyone)",
        "example": "/info"
    },
    "backup": {
        "title": "/backup",
        "description": "[Dev Only] Creates a backup of config and storage files.",
        "usage": "/backup",
        "permissions": "Bot Developer Only",
        "example": "/backup"
    },
    "forcecheck": {
        "title": "/forcecheck",
        "description": "[Dev Only] Force and execute update scan loops instantly.",
        "usage": "/forcecheck",
        "permissions": "Bot Developer Only",
        "example": "/forcecheck"
    },
    "log": {
        "title": "/log",
        "description": "[Dev Only] Saves current log records and forwards `bot.log` straight to your DMs.",
        "usage": "/log",
        "permissions": "Bot Developer Only",
        "example": "/log"
    },
    "shutdown": {
        "title": "/shutdown",
        "description": "[Dev Only] Saves current logs and safely shuts down bot operations.",
        "usage": "/shutdown",
        "permissions": "Bot Developer Only",
        "example": "/shutdown"
    }
}


class ModCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, config: dict):
        self.bot = bot
        self.config = config

    # -------------------------
    # Permission Checks
    # -------------------------

    def mod_only(interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.manage_guild

    def dev_only(interaction: discord.Interaction) -> bool:
        return interaction.user.id == interaction.client.dev_id

    # -------------------------
    # Autocomplete Helpers
    # -------------------------

    async def _project_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str
    ) -> list[app_commands.Choice[str]]:
        try:
            data = await load_storage()
            gid = str(interaction.guild.id)
            mods = data.get("guilds", {}).get(gid, {}).get("mods", [])

            choices = []
            for mod in mods:
                title = mod.get("title", "")
                slug = mod.get("slug", "")

                if current.lower() in title.lower() or current.lower() in slug.lower():
                    choices.append(app_commands.Choice(name=title, value=slug))

            return choices[:25]
        except Exception as e:
            logger.error(f"Error occurred during project autocomplete resolution: {e}")
            return []

    async def _add_project_search_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str
    ) -> list[app_commands.Choice[str]]:
        try:
            if not current.strip():
                return []

            hits = await search_projects(current)
            choices = []
            for hit in hits:
                title = hit.get("title", "")
                slug = hit.get("slug", "")

                # Format to "Title (slug)" and keep strictly below Discord's 100 char name limit
                display_name = f"{title} ({slug})"
                if len(display_name) > 100:
                    display_name = title[:95] + "..."

                choices.append(app_commands.Choice(name=display_name, value=slug))
            return choices[:25]
        except Exception as e:
            logger.error(f"Error handling add project dynamic search autocomplete: {e}")
            return []

    async def _help_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str
    ) -> list[app_commands.Choice[str]]:
        choices = []
        for cmd_name in HELP_COMMANDS.keys():
            if current.lower() in cmd_name.lower():
                choices.append(app_commands.Choice(name=f"/{cmd_name}", value=cmd_name))
        return choices[:25]

    # -------------------------
    # System Level Event Hooks
    # -------------------------

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: app_commands.Command):
        logger.info(
            f"User {interaction.user} (ID: {interaction.user.id}) "
            f"executed command: /{command.name} in guild (ID: {interaction.guild_id})"
        )

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            msg = "❌ You do not possess the clearance/permissions required to execute this command."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        else:
            logger.error(f"Unhandled system exceptions encountered on Slash tree: {error}")

    # -------------------------
    # SLASH COMMANDS
    # -------------------------

    @app_commands.command(name="help", description="Lists all available commands or details on a specific command.")
    @app_commands.describe(command="The command you want more detailed syntax and information on (optional)")
    async def help_command(self, interaction: discord.Interaction, command: Optional[str] = None):
        if not command:
            embed = discord.Embed(
                title="ModCheck Command Help Information",
                description="Use `/help command:<name>` for granular arguments, options, and usage examples.",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="📋 General Tracker Commands",
                value=(
                    "**`/add`** - Track a new Modrinth project.\n"
                    "**`/edit`** - Edit details/filters for a tracked mod.\n"
                    "**`/remove`** - Stop tracking a mod.\n"
                    "**`/list`** - List all tracked projects in the server.\n"
                    "**`/info`** - Show bot details and status parameters."
                ),
                inline=False
            )

            embed.add_field(
                name="🛡️ Moderator Commands",
                value=(
                    "**`/setrole`** - [Mod Only] Sets the selected role to be mentioned when a mod updates.\n"
                    "**`/setchannel`** - [Mod Only] Sets the default notification channel."
                ),
                inline=False
            )

            embed.add_field(
                name="🛠️ Developer Utility Commands",
                value=(
                    "**`/backup`** - [Dev Only] Creates a backup of config and storage files.\n"
                    "**`/forcecheck`** - [Dev Only] Force and execute update scan loops instantly.\n"
                    "**`/log`** - [Dev Only] Saves log records and forwards `bot.log` straight to your DMs.\n"
                    "**`/shutdown`** - [Dev Only] Saves current logs and safely shuts down bot operations."
                ),
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            cmd_key = command.lower().strip().replace("/", "")
            if cmd_key not in HELP_COMMANDS:
                await interaction.response.send_message(
                    content=f"❌ Command key `{command}` was not recognized. Please choose an option from the autocomplete list.",
                    ephemeral=True
                )
                return

            cmd_info = HELP_COMMANDS[cmd_key]
            embed = discord.Embed(
                title=f"Command Syntax Detail: {cmd_info['title']}",
                description=cmd_info['description'],
                color=discord.Color.green()
            )
            embed.add_field(name="How to Use", value=f"`{cmd_info['usage']}`", inline=False)
            embed.add_field(name="Clearance Level", value=cmd_info['permissions'], inline=True)
            embed.add_field(name="Example Command", value=f"`{cmd_info['example']}`", inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @help_command.autocomplete("command")
    async def help_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._help_autocomplete(interaction, current)

    @app_commands.command(name="shutdown",
                          description="[Dev Only] Saves current logs and safely shuts down bot operations.")
    @app_commands.check(dev_only)
    async def shutdown(self, interaction: discord.Interaction):
        logger.warning(f"Process shutdown sequence executed directly by bot developer.")
        await interaction.response.send_message("Shutting down...", ephemeral=True)
        await self.bot.close()

    @app_commands.command(name="log",
                          description="[Dev Only] Saves current log records and forwards bot.log straight to your DMs.")
    @app_commands.check(dev_only)
    async def log_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not os.path.exists(LOG_FILE):
            logger.error(f"Target log file requested but physically missing from data path: {LOG_FILE}")
            return await interaction.followup.send("No log file currently exists on storage.", ephemeral=True)

        try:
            user = await self.bot.fetch_user(self.bot.dev_id)
            await user.send(
                content="Here is your requested debug interface log:",
                file=discord.File(LOG_FILE, filename="bot.log")
            )
            await interaction.followup.send("Log file has been successfully sent to your DMs!", ephemeral=True)
        except discord.Forbidden:
            logger.error(f"Permission Block: Failed to execute log file DM. Developer has DMs blocked.")
            await interaction.followup.send("Process failed. Direct Messaging blocked. Please open your DMs.",
                                            ephemeral=True)
        except Exception as e:
            logger.error(f"Error handling /log request dispatch: {e}")
            await interaction.followup.send("Fatal error dispatching file stream.", ephemeral=True)

    @app_commands.command(name="add", description="Track a Modrinth project.")
    @app_commands.describe(
        project="Start typing the project name to search Modrinth...",
        mc_versions="Comma separated MC versions (optional)",
        loaders="Comma separated loaders (optional)",
        release_type="Release stream filter level",
        channel="Custom update channel (optional)"
    )
    @app_commands.choices(release_type=[
        app_commands.Choice(name="Release", value="release"),
        app_commands.Choice(name="Beta", value="beta"),
        app_commands.Choice(name="Alpha", value="alpha")
    ])
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
            return await interaction.followup.send("❌ Project not found on Modrinth.", ephemeral=True)

        data = await load_storage()
        gid = str(interaction.guild.id)

        data.setdefault("guilds", {})
        data["guilds"].setdefault(gid, {"mods": []})
        mods = data["guilds"][gid]["mods"]

        slug = project_data["slug"]

        if any(m["slug"] == slug for m in mods):
            return await interaction.followup.send("⚠️ This project is already tracked on this server.", ephemeral=True)

        parsed_mc = [v.strip() for v in mc_versions.split(",") if v.strip()] if mc_versions else []
        parsed_loaders = [l.strip().lower() for l in loaders.split(",") if l.strip()] if loaders else []

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
        await interaction.followup.send(f"Now tracking **{project_data['title']}**.")

    @add.autocomplete("project")
    async def add_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._add_project_search_autocomplete(interaction, current)

    @app_commands.command(name="edit", description="Edit details or update filters for a tracked mod.")
    @app_commands.describe(
        project="Pick a mod currently tracked in this guild",
        mc_versions="Comma separated MC versions (optional)",
        loaders="Comma separated loaders (optional)",
        release_type="Release stream filter level",
        channel="Custom update channel (optional)"
    )
    @app_commands.choices(release_type=[
        app_commands.Choice(name="Release", value="release"),
        app_commands.Choice(name="Beta", value="beta"),
        app_commands.Choice(name="Alpha", value="alpha")
    ])
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

        mods = data.get("guilds", {}).get(gid, {}).get("mods", [])
        mod = next((m for m in mods if m["slug"] == slug), None)

        if not mod:
            return await interaction.response.send_message("❌ Tracked mod not found in this server.", ephemeral=True)

        if mc_versions is not None:
            mod["mc_versions"] = [v.strip() for v in mc_versions.split(",") if v.strip()]

        if loaders is not None:
            mod["loaders"] = [l.strip().lower() for l in loaders.split(",") if l.strip()]

        if release_type is not None:
            mod["release_type"] = release_type

        if channel is not None:
            mod["channel_id"] = channel.id

        await save_storage(data)
        await interaction.response.send_message(
            f"✅ Tracked configurations updated successfully for **{mod['title']}**.", ephemeral=True)

    @edit.autocomplete("project")
    async def edit_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._project_autocomplete(interaction, current)

    @app_commands.command(name="remove", description="Stop tracking a project.")
    @app_commands.describe(project="Pick a mod currently tracked in this guild")
    async def remove(self, interaction: discord.Interaction, project: str):
        slug = normalize_slug(project)

        data = await load_storage()
        gid = str(interaction.guild.id)

        if "guilds" not in data or gid not in data["guilds"] or not data["guilds"][gid].get("mods"):
            return await interaction.response.send_message("No mods tracked in this server.", ephemeral=True)

        mods = data["guilds"][gid]["mods"]
        new_mods = [m for m in mods if m["slug"] != slug]

        if len(mods) == len(new_mods):
            return await interaction.response.send_message("Mod target was not registered.", ephemeral=True)

        data["guilds"][gid]["mods"] = new_mods
        await save_storage(data)

        await interaction.response.send_message(f"Stopped tracking project `{slug}`.", ephemeral=True)

    @remove.autocomplete("project")
    async def remove_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self._project_autocomplete(interaction, current)

    @app_commands.command(name="forcecheck", description="[Dev Only] Force and execute update scan loops instantly.")
    @app_commands.check(dev_only)
    async def forcecheck(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        from core.updater import run_update_cycle
        await run_update_cycle(self.bot, self.config)
        await interaction.followup.send("Update check execution cycle forced complete.", ephemeral=True)

    @app_commands.command(name="setrole",
                          description="[Mod Only] Sets the selected role to be mentioned when a mod updates.")
    @app_commands.check(mod_only)
    async def setrole(self, interaction: discord.Interaction, role: discord.Role):
        data = await load_storage()
        gid = str(interaction.guild.id)

        data.setdefault("guilds", {})
        data["guilds"].setdefault(gid, {"mods": []})
        data["guilds"][gid]["role_id"] = role.id

        await save_storage(data)
        await interaction.response.send_message(f"Update ping role configuration set to: **{role.name}**",
                                                ephemeral=True)

    @app_commands.command(name="setchannel", description="[Mod Only] Sets the default notification channel.")
    @app_commands.check(mod_only)
    async def setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        data = await load_storage()
        gid = str(interaction.guild.id)

        data.setdefault("guilds", {})
        data["guilds"].setdefault(gid, {"mods": []})
        data["guilds"][gid]["default_channel"] = channel.id

        await save_storage(data)
        await interaction.response.send_message(f"Default notification channel set to: {channel.mention}",
                                                ephemeral=True)

    @app_commands.command(name="backup", description="[Dev Only] Creates a backup of config and storage files.")
    @app_commands.check(dev_only)
    async def backup(self, interaction: discord.Interaction):
        import shutil
        from datetime import datetime

        await interaction.response.defer(ephemeral=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(project_root, "data")
        folder = os.path.join(project_root, "backups", timestamp)

        os.makedirs(folder, exist_ok=True)

        shutil.copy(os.path.join(data_dir, "storage.json"), os.path.join(folder, "storage.json"))
        shutil.copy(os.path.join(project_root, "config.json"), os.path.join(folder, "config.json"))

        await interaction.followup.send(f"Backup created: `{folder}`", ephemeral=True)

    @app_commands.command(name="info", description="Show bot info.")
    async def info(self, interaction: discord.Interaction):
        data = await load_storage()
        total_mods = sum(len(g.get("mods", [])) for g in data.get("guilds", {}).values() if isinstance(g, dict))

        embed = discord.Embed(
            title="ModCheck Status Interface",
            color=discord.Color.blue()
        )

        embed.add_field(name="Version ID", value=self.config["info"]["version"])
        embed.add_field(name="Developer", value=f"<@{self.bot.dev_id}>")
        embed.add_field(name="Tracked Mods Globally", value=str(total_mods))
        embed.add_field(name="Active Guilds", value=str(len(self.bot.guilds)))

        await interaction.response.send_message(embed=embed)

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

        if "guilds" not in data or gid not in data["guilds"] or not data["guilds"][gid].get("mods"):
            return await interaction.response.send_message("No mods currently tracked in this server.", ephemeral=True)

        mods = data["guilds"][gid]["mods"]

        if project_type:
            mods = [m for m in mods if m["project_type"] == project_type]

        if loader:
            mods = [m for m in mods if loader in m["loaders"]]

        if mc_version:
            mods = [m for m in mods if mc_version in m["mc_versions"]]

        if not mods:
            return await interaction.response.send_message("No mods matching the applied filters were found.",
                                                           ephemeral=True)

        embed = discord.Embed(
            title="Tracked Server Modpack Projects",
            color=discord.Color.blue()
        )

        for mod in mods:
            versions = await get_versions(mod["slug"])
            newest = versions[0]["version_number"] if versions else "Unknown"

            embed.add_field(
                name=mod["title"],
                value=(
                    f"Slug: `{mod['slug']}`\n"
                    f"URL: https://modrinth.com/project/{mod['slug']}\n"
                    f"Versions: {', '.join(mod['mc_versions']) or 'Any'}\n"
                    f"Loaders: {', '.join(mod['loaders']) or 'Any'}\n"
                    f"Latest Release: `{newest}`"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed)