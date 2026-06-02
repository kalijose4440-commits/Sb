from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from disnake.ext import commands

from bot.api.schemas import GuildSettingsRead
from bot.bridge.state import BridgeState, GuildSettingsSnapshot
from bot.db.repositories import GuildSettingsRepository


class BaseCog(commands.Cog):
    """Base Cog template showing DB persistence and API bridge interaction."""

    def __init__(self, bot: commands.InteractionBot, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.bot = bot
        self._session_factory = session_factory

    @property
    def bridge(self) -> BridgeState:
        return self.bot.bridge  # type: ignore[no-any-return]

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

    async def get_runtime_snapshot(self, guild_id: int) -> GuildSettingsSnapshot:
        """Read the latest in-memory value propagated by the dashboard API."""

        return await self.bridge.get_or_load_settings(guild_id)
