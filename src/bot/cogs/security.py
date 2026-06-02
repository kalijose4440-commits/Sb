from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime
from typing import Any, cast

import disnake
from disnake.ext import commands
from disnake.interactions.application_command import ApplicationCommandInteraction

from bot.cogs.base_cog import BaseCog
from bot.core.security import should_emit_alert, update_join_window, utc_now
from bot.db.repositories import RaidProtectionRepository


class SecurityCog(BaseCog):
    """Basic anti-raid controls and member-join burst detection."""

    def __init__(self, bot: commands.InteractionBot, session_factory) -> None:
        super().__init__(bot=bot, session_factory=session_factory)
        self._join_windows: dict[int, deque[datetime]] = defaultdict(deque)
        self._last_alert_at: dict[int, datetime] = {}

    @commands.slash_command(name="security", description="Manage raid and security controls")
    async def security(self, interaction: ApplicationCommandInteraction) -> None:
        await interaction.response.send_message(
            "Use a security subcommand such as `/security status`.",
            ephemeral=True,
        )

    @security.sub_command(name="status", description="Show raid protection settings")
    @commands.default_member_permissions(manage_guild=True)
    async def status(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        async with self._session_factory() as session:
            repository = RaidProtectionRepository(session)
            row = await repository.get_config(interaction.guild_id)

        if row is None:
            await interaction.response.send_message(
                "Security config not set. Run `/security configure` first.",
                ephemeral=True,
            )
            return

        alert_channel = f"<#{row.alert_channel_id}>" if row.alert_channel_id else "system channel"
        last_triggered = (
            f"<t:{int(row.last_triggered_at.timestamp())}:R>"
            if row.last_triggered_at is not None
            else "never"
        )
        await interaction.response.send_message(
            f"Security is **{'enabled' if row.enabled else 'disabled'}**\n"
            f"Threshold: `{row.join_threshold}` joins / `{row.window_seconds}s`\n"
            f"Alert channel: {alert_channel}\n"
            f"Last trigger: {last_triggered}",
            ephemeral=True,
        )

    @security.sub_command(name="configure", description="Configure raid burst detection thresholds")
    @commands.default_member_permissions(manage_guild=True)
    async def configure(
        self,
        interaction: ApplicationCommandInteraction,
        join_threshold: int = commands.Param(default=8, ge=3, le=100),
        window_seconds: int = commands.Param(default=30, ge=10, le=600),
        alert_channel: disnake.TextChannel | None = None,
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        alert_channel_id = alert_channel.id if alert_channel is not None else None
        async with self._session_factory() as session:
            repository = RaidProtectionRepository(session)
            await repository.upsert_config(
                interaction.guild_id,
                join_threshold=join_threshold,
                window_seconds=window_seconds,
                alert_channel_id=alert_channel_id,
            )
            await session.commit()

        await interaction.response.send_message(
            f"Security configured: {join_threshold} joins in {window_seconds}s.",
            ephemeral=True,
        )

    @security.sub_command(name="enable", description="Enable raid detection alerts")
    @commands.default_member_permissions(manage_guild=True)
    async def enable(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        async with self._session_factory() as session:
            repository = RaidProtectionRepository(session)
            await repository.upsert_config(interaction.guild_id, enabled=True)
            await session.commit()

        await interaction.response.send_message("Raid detection enabled.", ephemeral=True)

    @security.sub_command(name="disable", description="Disable raid detection alerts")
    @commands.default_member_permissions(manage_guild=True)
    async def disable(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        async with self._session_factory() as session:
            repository = RaidProtectionRepository(session)
            await repository.upsert_config(interaction.guild_id, enabled=False)
            await session.commit()

        await interaction.response.send_message("Raid detection disabled.", ephemeral=True)

    @commands.Cog.listener("on_member_join")
    async def on_member_join(self, member: disnake.Member) -> None:
        guild = member.guild

        async with self._session_factory() as session:
            repository = RaidProtectionRepository(session)
            config = await repository.get_config(guild.id)

        if config is None or not config.enabled:
            return

        now = utc_now()
        join_window = self._join_windows[guild.id]
        join_count = update_join_window(
            join_window,
            now,
            window_seconds=config.window_seconds,
        )

        last_alert = self._last_alert_at.get(guild.id)
        should_alert = should_emit_alert(
            join_count=join_count,
            threshold=config.join_threshold,
            last_alert_at=last_alert,
            now=now,
            cooldown_seconds=config.window_seconds,
        )
        if not should_alert:
            return

        self._last_alert_at[guild.id] = now

        alert_channel: disnake.abc.MessageableChannel | None = None
        if config.alert_channel_id is not None:
            candidate = guild.get_channel(config.alert_channel_id)
            if isinstance(candidate, disnake.TextChannel):
                alert_channel = candidate

        if alert_channel is None:
            alert_channel = guild.system_channel

        if alert_channel is not None:
            embed = disnake.Embed(
                title="Security alert: join burst detected",
                description=(
                    f"Detected **{join_count} joins** in the last **{config.window_seconds}s**.\n"
                    "Review new accounts and consider enabling temporary gatekeeping."
                ),
                color=disnake.Color.red(),
            )
            embed.add_field(name="Threshold", value=str(config.join_threshold), inline=True)
            embed.add_field(name="Newest member", value=member.mention, inline=True)
            try:
                await alert_channel.send(embed=embed)
            except disnake.HTTPException:
                pass

        async with self._session_factory() as session:
            repository = RaidProtectionRepository(session)
            await repository.mark_triggered(guild.id, now)
            await session.commit()


def setup(bot: commands.InteractionBot) -> None:
    bridge = cast(Any, bot).bridge
    bot.add_cog(SecurityCog(bot=bot, session_factory=bridge.session_factory))
