from __future__ import annotations

from typing import Any, cast

import disnake
from disnake.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.api.schemas import GuildSettingsRead
from bot.bridge.state import BridgeState, GuildSettingsSnapshot
from bot.db.repositories import GuildSettingsRepository


class BaseCog(commands.Cog):
    """Base Cog template showing DB persistence and API bridge interaction."""

    def __init__(
        self,
        bot: commands.InteractionBot,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self.bot = bot
        self._session_factory = session_factory

    @property
    def bridge(self) -> BridgeState:
        bridge = getattr(self.bot, "bridge", None)
        if bridge is None:
            raise RuntimeError("BridgeState is not attached to this bot instance")
        return cast(BridgeState, bridge)

    async def get_guild_settings(self, guild_id: int) -> GuildSettingsRead:
        """Read settings from PostgreSQL and return an API-friendly schema."""

        async with self._session_factory() as session:
            repository = GuildSettingsRepository(session)
            row = await repository.upsert(
                guild_id,
                default_prefix=self.bridge.default_prefix,
                default_status=self.bridge.default_status,
            )
            await session.commit()

        await self.bridge.publish_prefix_change(guild_id=guild_id, prefix=row.prefix)
        await self.bridge.publish_status_change(guild_id=guild_id, status=row.status)
        return GuildSettingsRead.model_validate(row, from_attributes=True)

    async def update_prefix(self, guild_id: int, prefix: str) -> GuildSettingsRead:
        """Persist a prefix update and publish it through the API bridge in real-time."""

        async with self._session_factory() as session:
            repository = GuildSettingsRepository(session)
            row = await repository.upsert_prefix(
                guild_id=guild_id,
                prefix=prefix,
                default_status=self.bridge.default_status,
            )
            await session.commit()

        await self.bridge.publish_prefix_change(guild_id=guild_id, prefix=prefix)
        return GuildSettingsRead.model_validate(row, from_attributes=True)

    async def update_status(self, guild_id: int, status: str) -> GuildSettingsRead:
        """Persist a status update and publish it through the API bridge in real-time."""

        async with self._session_factory() as session:
            repository = GuildSettingsRepository(session)
            row = await repository.upsert_status(
                guild_id=guild_id,
                status=status,
                default_prefix=self.bridge.default_prefix,
            )
            await session.commit()

        await self.bridge.publish_status_change(guild_id=guild_id, status=status)
        return GuildSettingsRead.model_validate(row, from_attributes=True)


    async def send_subcommand_help(
        self,
        interaction,
        *,
        group_name: str,
        slash_examples: list[str],
        prefix_examples: list[str],
    ) -> None:
        """Send a unified group help embed with slash and prefix usage."""

        prefix = self.bridge.default_prefix
        guild_id = getattr(interaction, "guild_id", None)
        if guild_id is not None:
            snapshot = await self.bridge.get_or_load_settings(guild_id)
            prefix = snapshot.prefix

        prefix_lines = "\n".join(f"- `{prefix}{example}`" for example in prefix_examples)

        embed = disnake.Embed(
            title=f"{group_name.title()} commands",
            description="Pick one of the subcommands below.",
            color=disnake.Color.blurple(),
        )
        bot_settings = cast(Any, self.bot).settings
        if getattr(bot_settings, "enable_slash_commands", False):
            slash_lines = "\n".join(f"- `/{example}`" for example in slash_examples)
            embed.add_field(name="Slash", value=slash_lines, inline=False)
        embed.add_field(name="Prefix", value=prefix_lines, inline=False)
        await interaction.response.send_message(embed=embed)

    async def get_runtime_snapshot(self, guild_id: int) -> GuildSettingsSnapshot:
        """Read the latest in-memory value propagated by the dashboard API."""

        return await self.bridge.get_or_load_settings(guild_id)
