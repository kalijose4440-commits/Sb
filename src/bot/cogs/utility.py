from __future__ import annotations

from datetime import UTC, datetime

import disnake
from disnake.ext import commands

from bot.cogs.base_cog import BaseCog


def format_uptime(started_at: datetime, now: datetime | None = None) -> str:
    """Format bot uptime as a compact human-readable string."""

    reference = now or datetime.now(UTC)
    elapsed = int((reference - started_at).total_seconds())
    days, rem = divmod(elapsed, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


class UtilityCog(BaseCog):
    """High-value informational commands for daily server operations."""

    @commands.slash_command(name="ping", description="Show bot latency and API heartbeat")
    async def ping(self, interaction: disnake.ApplicationCommandInteraction) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! `{latency_ms}ms`", ephemeral=True)

    @commands.slash_command(name="botinfo", description="Show runtime information about this bot")
    async def botinfo(self, interaction: disnake.ApplicationCommandInteraction) -> None:
        guilds = len(self.bot.guilds)
        members = sum(guild.member_count or 0 for guild in self.bot.guilds)
        uptime = format_uptime(self.bot.started_at)

        embed = disnake.Embed(title="Bot Information", color=disnake.Color.blurple())
        embed.add_field(name="Guilds", value=str(guilds), inline=True)
        embed.add_field(name="Members", value=str(members), inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="Uptime", value=uptime, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="serverinfo", description="Display summary information for this server")
    async def serverinfo(self, interaction: disnake.ApplicationCommandInteraction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        guild = interaction.guild
        created = disnake.utils.format_dt(guild.created_at, style="R")
        embed = disnake.Embed(title=f"{guild.name}", color=disnake.Color.green())
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Members", value=str(guild.member_count or 0), inline=True)
        embed.add_field(name="Channels", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Created", value=created, inline=False)

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="userinfo", description="Show profile details for a server member")
    async def userinfo(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        member: disnake.Member | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        target = member or interaction.author
        joined = disnake.utils.format_dt(target.joined_at, style="R") if target.joined_at else "Unknown"
        created = disnake.utils.format_dt(target.created_at, style="R")

        embed = disnake.Embed(title=f"User: {target}", color=disnake.Color.orange())
        embed.add_field(name="ID", value=str(target.id), inline=True)
        embed.add_field(name="Top Role", value=target.top_role.mention, inline=True)
        embed.add_field(name="Created", value=created, inline=False)
        embed.add_field(name="Joined", value=joined, inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="runtime", description="Show real-time runtime settings snapshot for this guild")
    async def runtime(self, interaction: disnake.ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        snapshot = await self.get_runtime_snapshot(interaction.guild_id)
        await interaction.response.send_message(
            f"Runtime snapshot -> prefix: `{snapshot.prefix}` | status: `{snapshot.status}`",
            ephemeral=True,
        )


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(UtilityCog(bot=bot, session_factory=bot.bridge.session_factory))
