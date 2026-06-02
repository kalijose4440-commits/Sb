from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import GuildSettings


class GuildSettingsRepository:
    """Data access boundary for guild settings."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_guild_id(self, guild_id: int) -> GuildSettings | None:
        statement = select(GuildSettings).where(GuildSettings.guild_id == guild_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        guild_id: int,
        *,
        prefix: str | None = None,
        status: str | None = None,
        default_prefix: str = "!",
        default_status: str = "online",
    ) -> GuildSettings:
        row = await self.get_by_guild_id(guild_id)
        if row is None:
            row = GuildSettings(
                guild_id=guild_id,
                prefix=prefix or default_prefix,
                status=status or default_status,
            )
            self._session.add(row)
        else:
            if prefix is not None:
                row.prefix = prefix
            if status is not None:
                row.status = status

        await self._session.flush()
        return row

    async def upsert_prefix(self, guild_id: int, prefix: str, *, default_status: str = "online") -> GuildSettings:
        return await self.upsert(guild_id, prefix=prefix, default_status=default_status)

    async def upsert_status(self, guild_id: int, status: str, *, default_prefix: str = "!") -> GuildSettings:
        return await self.upsert(guild_id, status=status, default_prefix=default_prefix)
