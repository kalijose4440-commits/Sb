from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.repositories import GuildSettingsRepository


@dataclass(slots=True)
class GuildSettingsSnapshot:
    guild_id: int
    prefix: str
    status: str


@dataclass(slots=True)
class BridgeEvent:
    guild_id: int
    field: Literal["prefix", "status"]
    value: str


class BridgeState:
    """In-memory bridge for real-time dashboard-to-bot synchronization."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        default_prefix: str = "!",
        default_status: str = "online",
    ) -> None:
        self.session_factory = session_factory
        self.default_prefix = default_prefix
        self.default_status = default_status
        self._cache: dict[int, GuildSettingsSnapshot] = {}
        self._listeners: set[asyncio.Queue[BridgeEvent]] = set()
        self._lock = asyncio.Lock()

    async def get_or_load_settings(self, guild_id: int) -> GuildSettingsSnapshot:
        cached = self._cache.get(guild_id)
        if cached is not None:
            return cached

        async with self.session_factory() as session:
            repository = GuildSettingsRepository(session)
            row = await repository.get_by_guild_id(guild_id)

        if row is None:
            snapshot = GuildSettingsSnapshot(
                guild_id=guild_id,
                prefix=self.default_prefix,
                status=self.default_status,
            )
        else:
            snapshot = GuildSettingsSnapshot(
                guild_id=row.guild_id,
                prefix=row.prefix,
                status=row.status,
            )

        async with self._lock:
            self._cache[guild_id] = snapshot
        return snapshot

    async def publish_prefix_change(self, guild_id: int, prefix: str) -> None:
        await self._update_and_publish(guild_id=guild_id, field="prefix", value=prefix)

    async def publish_status_change(self, guild_id: int, status: str) -> None:
        await self._update_and_publish(guild_id=guild_id, field="status", value=status)

    async def register_listener(self) -> asyncio.Queue[BridgeEvent]:
        queue: asyncio.Queue[BridgeEvent] = asyncio.Queue()
        async with self._lock:
            self._listeners.add(queue)
        return queue

    async def unregister_listener(self, queue: asyncio.Queue[BridgeEvent]) -> None:
        async with self._lock:
            self._listeners.discard(queue)

    async def _update_and_publish(
        self, *, guild_id: int, field: Literal["prefix", "status"], value: str
    ) -> None:
        async with self._lock:
            current = self._cache.get(guild_id)
            if current is None:
                current = GuildSettingsSnapshot(
                    guild_id=guild_id,
                    prefix=self.default_prefix,
                    status=self.default_status,
                )

            if field == "prefix":
                current.prefix = value
            else:
                current.status = value

            self._cache[guild_id] = current
            listeners = tuple(self._listeners)

        event = BridgeEvent(guild_id=guild_id, field=field, value=value)
        for listener in listeners:
            listener.put_nowait(event)
