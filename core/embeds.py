import discord


def build_update_embed(
    name: str,
    version: str,
    game_versions: list[str],
    loaders: list[str],
    url: str,
    project_type: str = "mod",
    version_type: str = "release"
) -> discord.Embed:

    embed = discord.Embed(
        title=f"{name} updated!",
        description=f"New version: `{version}`",
        color=discord.Color.green()
    )

    embed.add_field(name="Type", value=project_type.capitalize(), inline=True)
    embed.add_field(name="Release", value=version_type.capitalize(), inline=True)
    embed.add_field(
        name="Minecraft",
        value=", ".join(game_versions) if game_versions else "N/A",
        inline=False
    )
    embed.add_field(
        name="Loaders",
        value=", ".join(loaders) if loaders else "N/A",
        inline=False
    )
    embed.add_field(name="Link", value=url, inline=False)

    embed.set_footer(text="ModUpdater")

    return embed
