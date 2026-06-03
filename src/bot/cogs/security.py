from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, cast

import disnake
from disnake.ext import commands, tasks
from disnake.interactions.application_command import ApplicationCommandInteraction
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.cogs.base_cog import BaseCog
from bot.core.response_style import build_standard_embed
from bot.core.security import should_emit_alert, update_join_window, utc_now
from bot.db.repositories import RaidProtectionRepository


class SecurityCog(BaseCog):
    """Anti-raid controls with alerting and optional automated mitigation."""

    def __init__(
        self,
        bot: commands.InteractionBot,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        super().__init__(bot=bot, session_factory=session_factory)
        self._join_windows: dict[int, deque[datetime]] = defaultdict(deque)
        self._ban_windows: dict[int, deque[datetime]] = defaultdict(deque)
        self._channel_delete_windows: dict[int, deque[datetime]] = defaultdict(deque)
        self._anti_nuke_enabled: dict[int, bool] = defaultdict(lambda: True)
        self._last_alert_at: dict[int, datetime] = {}
        self._mitigation_release_loop.start()

    def cog_unload(self) -> None:
        self._mitigation_release_loop.cancel()

    @commands.slash_command(name="security", description="Manage raid and security controls")
    async def security(self, interaction: ApplicationCommandInteraction) -> None:
        await self.send_subcommand_help(
            interaction,
            group_name="security",
            slash_examples=[
                "security status",
                "security configure",
                "security enable",
                "security disable",
                "security antinuke",
                "security antinuke",
            ],
            prefix_examples=[
                "security status",
                "security configure",
                "security enable",
                "security disable",
            ],
        )

    @security.sub_command(name="status", description="Show raid protection settings")
    @commands.has_permissions(manage_guild=True)
    async def status(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
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
        mitigation_until = (
            f"<t:{int(row.mitigation_active_until.timestamp())}:R>"
            if row.mitigation_active_until is not None
            else "inactive"
        )
        await interaction.response.send_message(
            f"Security is **{'enabled' if row.enabled else 'disabled'}**\n"
            f"Threshold: `{row.join_threshold}` joins / `{row.window_seconds}s`\n"
            f"Alert channel: {alert_channel}\n"
            f"Mitigation: `{row.mitigation_action}` for `{row.mitigation_duration_seconds}s`\n"
            f"Mitigation active until: {mitigation_until}\n"
            f"Last trigger: {last_triggered}",
            ephemeral=True,
        )

    @security.sub_command(
        name="configure", description="Configure raid burst detection and mitigation"
    )
    @commands.has_permissions(manage_guild=True)
    async def configure(
        self,
        interaction: ApplicationCommandInteraction,
        join_threshold: int = commands.Param(default=8, ge=3, le=100),
        window_seconds: int = commands.Param(default=30, ge=10, le=600),
        alert_channel: disnake.TextChannel | None = None,
        mitigation_action: str = commands.Param(
            default="none",
            choices=["none", "verification_high"],
        ),
        mitigation_duration_minutes: int = commands.Param(default=15, ge=1, le=240),
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
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
                mitigation_action=mitigation_action,
                mitigation_duration_seconds=mitigation_duration_minutes * 60,
            )
            await session.commit()

        await interaction.response.send_message(
            f"Security configured: {join_threshold} joins in {window_seconds}s, "
            f"mitigation `{mitigation_action}` for {mitigation_duration_minutes}m.",
            ephemeral=True,
        )

    @security.sub_command(name="enable", description="Enable raid detection alerts")
    @commands.has_permissions(manage_guild=True)
    async def enable(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        async with self._session_factory() as session:
            repository = RaidProtectionRepository(session)
            await repository.upsert_config(interaction.guild_id, enabled=True)
            await session.commit()

        await interaction.response.send_message("Raid detection enabled.", ephemeral=True)

    @security.sub_command(name="disable", description="Disable raid detection alerts")
    @commands.has_permissions(manage_guild=True)
    async def disable(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        async with self._session_factory() as session:
            repository = RaidProtectionRepository(session)
            await repository.upsert_config(interaction.guild_id, enabled=False)
            await session.commit()

        await interaction.response.send_message("Raid detection disabled.", ephemeral=True)


    @security.sub_command(name="antinuke", description="Toggle anti-nuke runtime protection")
    @commands.has_permissions(manage_guild=True)
    async def antinuke(self, interaction: ApplicationCommandInteraction, enabled: bool) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        self._anti_nuke_enabled[interaction.guild_id] = enabled
        await interaction.response.send_message(
            f"Anti-nuke runtime guard {'enabled' if enabled else 'disabled'}.",
            ephemeral=True,
        )

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

        mitigation_note = await self._apply_mitigation(guild, config, now)

        alert_channel = self._resolve_alert_channel(guild, config.alert_channel_id)
        if alert_channel is not None:
            embed = build_standard_embed(
                (
                    f"Detected **{join_count} joins** in the last **{config.window_seconds}s**.\n"
                    "Review new accounts and consider temporary gatekeeping."
                ),
                title="Security alert: join burst detected",
            )
            embed.add_field(name="Threshold", value=str(config.join_threshold), inline=True)
            embed.add_field(name="Newest member", value=member.mention, inline=True)
            embed.add_field(name="Mitigation", value=mitigation_note, inline=False)
            try:
                await alert_channel.send(embed=embed)
            except disnake.HTTPException:
                pass

        async with self._session_factory() as session:
            repository = RaidProtectionRepository(session)
            await repository.mark_triggered(guild.id, now)
            await session.commit()

    @commands.Cog.listener("on_member_ban")
    async def on_member_ban(
        self,
        guild: disnake.Guild,
        _user: disnake.User | disnake.Member,
    ) -> None:
        await self._check_mass_action(guild, action="member_ban")

    @commands.Cog.listener("on_guild_channel_delete")
    async def on_guild_channel_delete(self, channel: disnake.abc.GuildChannel) -> None:
        await self._check_mass_action(channel.guild, action="channel_delete")

    async def _check_mass_action(self, guild: disnake.Guild, *, action: str) -> None:
        if not self._anti_nuke_enabled[guild.id]:
            return

        window = (
            self._ban_windows[guild.id]
            if action == "member_ban"
            else self._channel_delete_windows[guild.id]
        )
        now = utc_now()
        count = update_join_window(window, now, window_seconds=20)
        if count < 3:
            return

        async with self._session_factory() as session:
            repository = RaidProtectionRepository(session)
            config = await repository.get_config(guild.id)

        if config is None or not config.enabled:
            return

        mitigation_note = await self._apply_mitigation(guild, config, now)
        alert_channel = self._resolve_alert_channel(guild, config.alert_channel_id)
        if alert_channel is not None:
            embed = build_standard_embed(
                (
                    f"Detected burst `{action}` activity: **{count}** events in 20s.\n"
                    "Automatic mitigation flow has been evaluated."
                ),
                title="Security alert: anti-nuke trigger",
            )
            embed.add_field(name="Action", value=action, inline=True)
            embed.add_field(name="Count", value=str(count), inline=True)
            embed.add_field(name="Mitigation", value=mitigation_note, inline=False)
            try:
                await alert_channel.send(embed=embed)
            except disnake.HTTPException:
                return

    async def _apply_mitigation(
        self,
        guild: disnake.Guild,
        config,
        now: datetime,
    ) -> str:
        if config.mitigation_action != "verification_high":
            return "No automatic mitigation configured."

        previous_level = guild.verification_level.value
        target_level = disnake.VerificationLevel.highest

        if guild.verification_level != target_level:
            try:
                await guild.edit(
                    verification_level=target_level,
                    reason="Automatic anti-raid mitigation",
                )
            except disnake.HTTPException:
                return "Failed to apply verification-level mitigation."

        active_until = now + timedelta(seconds=config.mitigation_duration_seconds)
        async with self._session_factory() as session:
            repository = RaidProtectionRepository(session)
            await repository.mark_mitigation_started(
                guild.id,
                previous_verification_level=previous_level,
                active_until=active_until,
            )
            await session.commit()

        return f"Raised verification to highest until <t:{int(active_until.timestamp())}:R>."

    @tasks.loop(seconds=30)
    async def _mitigation_release_loop(self) -> None:
        now = utc_now()

        async with self._session_factory() as session:
            repository = RaidProtectionRepository(session)
            due_rows = await repository.due_mitigation_releases(now)

        for row in due_rows:
            guild = self.bot.get_guild(row.guild_id)
            if guild is not None and row.previous_verification_level is not None:
                try:
                    previous_level = disnake.VerificationLevel(row.previous_verification_level)
                    await guild.edit(
                        verification_level=previous_level,
                        reason="Automatic anti-raid mitigation release",
                    )
                except (ValueError, disnake.HTTPException):
                    pass

            async with self._session_factory() as session:
                repository = RaidProtectionRepository(session)
                await repository.clear_mitigation(row.guild_id)
                await session.commit()

            alert_channel = self._resolve_alert_channel(guild, row.alert_channel_id)
            if alert_channel is not None:
                try:
                    await alert_channel.send(
                        "Automatic anti-raid mitigation has been released.",
                    )
                except disnake.HTTPException:
                    pass

    @_mitigation_release_loop.before_loop
    async def _before_release_loop(self) -> None:
        await self.bot.wait_until_ready()

    def _resolve_alert_channel(
        self,
        guild: disnake.Guild | None,
        alert_channel_id: int | None,
    ) -> disnake.TextChannel | None:
        if guild is None:
            return None

        if alert_channel_id is not None:
            candidate = guild.get_channel(alert_channel_id)
            if isinstance(candidate, disnake.TextChannel):
                return candidate

        if isinstance(guild.system_channel, disnake.TextChannel):
            return guild.system_channel
        return None


def setup(bot: commands.InteractionBot) -> None:
    bridge = cast(Any, bot).bridge
    bot.add_cog(SecurityCog(bot=bot, session_factory=bridge.session_factory))
