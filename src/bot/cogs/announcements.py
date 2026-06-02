from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import disnake
from disnake.ext import commands, tasks
from disnake.interactions.application_command import ApplicationCommandInteraction
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.cogs.base_cog import BaseCog
from bot.db.repositories import AnnouncementRepository


class AnnouncementCog(BaseCog):
    """Recurring announcement commands and scheduler loop."""

    def __init__(
        self,
        bot: commands.InteractionBot,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        super().__init__(bot=bot, session_factory=session_factory)
        settings = cast(Any, bot).settings
        self._announcement_loop.change_interval(seconds=settings.announcement_poll_seconds)
        self._announcement_loop.start()

    def cog_unload(self) -> None:
        self._announcement_loop.cancel()

    @commands.slash_command(name="announce", description="Manage recurring announcements")
    async def announce(self, interaction: ApplicationCommandInteraction) -> None:
        await interaction.response.send_message(
            "Use an announce subcommand such as `/announce create`.",
            ephemeral=True,
        )

    @announce.sub_command(name="create", description="Create a repeating announcement")
    @commands.has_permissions(manage_guild=True)
    async def create(
        self,
        interaction: ApplicationCommandInteraction,
        channel: disnake.TextChannel,
        interval_minutes: int = commands.Param(ge=1, le=10080),
        content: str = commands.Param(min_length=1, max_length=1900),
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        async with self._session_factory() as session:
            repository = AnnouncementRepository(session)
            row = await repository.create_announcement(
                guild_id=interaction.guild_id,
                channel_id=channel.id,
                content=content,
                interval_minutes=interval_minutes,
            )
            await session.commit()

        await interaction.response.send_message(
            (
                f"Announcement `#{row.id}` created for {channel.mention} "
                f"every `{interval_minutes}` min."
            ),
            ephemeral=True,
        )

    @announce.sub_command(name="toggle", description="Enable or disable an announcement")
    @commands.has_permissions(manage_guild=True)
    async def toggle(
        self,
        interaction: ApplicationCommandInteraction,
        announcement_id: int,
        enabled: bool,
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        async with self._session_factory() as session:
            repository = AnnouncementRepository(session)
            row = await repository.set_enabled(interaction.guild_id, announcement_id, enabled)
            await session.commit()

        if row is None:
            await interaction.response.send_message("Announcement not found.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Announcement `#{announcement_id}` is now {'enabled' if enabled else 'disabled'}.",
            ephemeral=True,
        )

    @announce.sub_command(name="list", description="List recurring announcements")
    @commands.has_permissions(manage_guild=True)
    async def list_announcements(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        async with self._session_factory() as session:
            repository = AnnouncementRepository(session)
            rows = await repository.list_announcements(interaction.guild_id)

        if not rows:
            await interaction.response.send_message(
                "No recurring announcements configured.",
                ephemeral=True,
            )
            return

        lines = [
            f"`#{row.id}` <#{row.channel_id}> every `{row.interval_minutes}`m "
            f"next: <t:{int(row.next_run_at.timestamp())}:R> ({'on' if row.enabled else 'off'})"
            for row in rows[:20]
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @announce.sub_command(name="runnow", description="Trigger an announcement immediately")
    @commands.has_permissions(manage_guild=True)
    async def run_now(
        self, interaction: ApplicationCommandInteraction, announcement_id: int
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        async with self._session_factory() as session:
            repository = AnnouncementRepository(session)
            row = await repository.get_announcement(interaction.guild_id, announcement_id)
            if row is None:
                await interaction.response.send_message("Announcement not found.", ephemeral=True)
                return

            channel = self.bot.get_channel(row.channel_id)
            if not isinstance(channel, disnake.TextChannel):
                await interaction.response.send_message(
                    "Configured channel is unavailable.",
                    ephemeral=True,
                )
                return

            await channel.send(row.content)
            now = datetime.now(UTC)
            next_run_at = now + timedelta(minutes=row.interval_minutes)
            await repository.mark_ran(
                row.id,
                last_run_at=now,
                next_run_at=next_run_at,
            )
            await session.commit()

        await interaction.response.send_message("Announcement sent.", ephemeral=True)

    @tasks.loop(seconds=30)
    async def _announcement_loop(self) -> None:
        now = datetime.now(UTC)

        async with self._session_factory() as session:
            repository = AnnouncementRepository(session)
            due_rows = await repository.due_announcements(now)
            if not due_rows:
                return

            for row in due_rows:
                channel = self.bot.get_channel(row.channel_id)
                if isinstance(channel, disnake.TextChannel):
                    try:
                        await channel.send(row.content)
                    except disnake.HTTPException:
                        continue

                next_run_at = now + timedelta(minutes=row.interval_minutes)
                await repository.mark_ran(
                    row.id,
                    last_run_at=now,
                    next_run_at=next_run_at,
                )

            await session.commit()

    @_announcement_loop.before_loop
    async def _before_loop(self) -> None:
        await self.bot.wait_until_ready()


def setup(bot: commands.InteractionBot) -> None:
    bridge = cast(Any, bot).bridge
    bot.add_cog(AnnouncementCog(bot=bot, session_factory=bridge.session_factory))
