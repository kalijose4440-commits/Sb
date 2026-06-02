from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.api.schemas import GuildSettingsRead, GuildSettingsUpdate
from bot.bridge.state import BridgeState
from bot.db.repositories import GuildSettingsRepository

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


def _bridge_from_request(request: Request) -> BridgeState:
    return request.app.state.bridge  # type: ignore[no-any-return]


def _session_factory_from_request(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.session_factory  # type: ignore[no-any-return]


@router.get("/{guild_id}", response_model=GuildSettingsRead)
async def get_guild_settings(guild_id: int, request: Request) -> GuildSettingsRead:
    bridge = _bridge_from_request(request)
    session_factory = _session_factory_from_request(request)

    async with session_factory() as session:
        repository = GuildSettingsRepository(session)
        row = await repository.get_by_guild_id(guild_id)
        if row is None:
            row = await repository.upsert(
                guild_id,
                default_prefix=bridge.default_prefix,
                default_status=bridge.default_status,
            )
            await session.commit()

    await bridge.publish_prefix_change(guild_id=guild_id, prefix=row.prefix)
    await bridge.publish_status_change(guild_id=guild_id, status=row.status)
    return GuildSettingsRead.model_validate(row, from_attributes=True)


@router.patch("/{guild_id}", response_model=GuildSettingsRead)
async def patch_guild_settings(guild_id: int, payload: GuildSettingsUpdate, request: Request) -> GuildSettingsRead:
    bridge = _bridge_from_request(request)
    session_factory = _session_factory_from_request(request)

    async with session_factory() as session:
        repository = GuildSettingsRepository(session)
        row = await repository.upsert(
            guild_id,
            prefix=payload.prefix,
            status=payload.status,
            default_prefix=bridge.default_prefix,
            default_status=bridge.default_status,
        )
        await session.commit()

    if payload.prefix is not None:
        await bridge.publish_prefix_change(guild_id=guild_id, prefix=payload.prefix)
    if payload.status is not None:
        await bridge.publish_status_change(guild_id=guild_id, status=payload.status)

    return GuildSettingsRead.model_validate(row, from_attributes=True)


@router.delete("/{guild_id}", status_code=204)
async def reset_guild_settings(guild_id: int, request: Request) -> None:
    session_factory = _session_factory_from_request(request)

    async with session_factory() as session:
        repository = GuildSettingsRepository(session)
        row = await repository.get_by_guild_id(guild_id)
        if row is None:
            raise HTTPException(status_code=404, detail="guild settings not found")
        await session.delete(row)
        await session.commit()
