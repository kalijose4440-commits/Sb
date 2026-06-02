from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.api.premium_schemas import (
    AnnouncementCreate,
    AnnouncementRead,
    AnnouncementToggle,
    AutoModKeywordCreate,
    AutoModKeywordRead,
    RaidProtectionConfigRead,
    RaidProtectionConfigUpdate,
    ReactionRoleCreate,
    ReactionRoleRead,
    TicketRead,
    WelcomeConfigRead,
    WelcomeConfigUpdate,
)
from bot.db.repositories import (
    AnnouncementRepository,
    AutoModRepository,
    RaidProtectionRepository,
    ReactionRoleRepository,
    TicketRepository,
    WelcomeRepository,
)

router = APIRouter(prefix="/api/v1/premium", tags=["premium"])


def _session_factory_from_request(
    request: Request,
) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], request.app.state.session_factory)


@router.get("/{guild_id}/automod/keywords", response_model=list[AutoModKeywordRead])
async def list_automod_keywords(guild_id: int, request: Request) -> list[AutoModKeywordRead]:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = AutoModRepository(session)
        rows = await repository.list_keywords(guild_id)
    return [AutoModKeywordRead.model_validate(row, from_attributes=True) for row in rows]


@router.post("/{guild_id}/automod/keywords", response_model=AutoModKeywordRead)
async def add_automod_keyword(
    guild_id: int,
    payload: AutoModKeywordCreate,
    request: Request,
) -> AutoModKeywordRead:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = AutoModRepository(session)
        row = await repository.add_keyword(guild_id, payload.keyword, payload.action)
        await session.commit()
    return AutoModKeywordRead.model_validate(row, from_attributes=True)


@router.delete("/{guild_id}/automod/keywords/{keyword}", status_code=204)
async def remove_automod_keyword(guild_id: int, keyword: str, request: Request) -> None:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = AutoModRepository(session)
        deleted = await repository.remove_keyword(guild_id, keyword)
        if not deleted:
            raise HTTPException(status_code=404, detail="keyword not found")
        await session.commit()


@router.get("/{guild_id}/announcements", response_model=list[AnnouncementRead])
async def list_announcements(guild_id: int, request: Request) -> list[AnnouncementRead]:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = AnnouncementRepository(session)
        rows = await repository.list_announcements(guild_id)
    return [AnnouncementRead.model_validate(row, from_attributes=True) for row in rows]


@router.post("/{guild_id}/announcements", response_model=AnnouncementRead)
async def create_announcement(
    guild_id: int,
    payload: AnnouncementCreate,
    request: Request,
) -> AnnouncementRead:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = AnnouncementRepository(session)
        row = await repository.create_announcement(
            guild_id=guild_id,
            channel_id=payload.channel_id,
            content=payload.content,
            interval_minutes=payload.interval_minutes,
        )
        await session.commit()
    return AnnouncementRead.model_validate(row, from_attributes=True)


@router.patch("/{guild_id}/announcements/{announcement_id}", response_model=AnnouncementRead)
async def toggle_announcement(
    guild_id: int,
    announcement_id: int,
    payload: AnnouncementToggle,
    request: Request,
) -> AnnouncementRead:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = AnnouncementRepository(session)
        row = await repository.set_enabled(guild_id, announcement_id, payload.enabled)
        if row is None:
            raise HTTPException(status_code=404, detail="announcement not found")
        await session.commit()
    return AnnouncementRead.model_validate(row, from_attributes=True)


@router.get("/{guild_id}/reaction-roles", response_model=list[ReactionRoleRead])
async def list_reaction_roles(guild_id: int, request: Request) -> list[ReactionRoleRead]:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = ReactionRoleRepository(session)
        rows = await repository.list_bindings(guild_id)
    return [ReactionRoleRead.model_validate(row, from_attributes=True) for row in rows]


@router.post("/{guild_id}/reaction-roles", response_model=ReactionRoleRead)
async def upsert_reaction_role(
    guild_id: int,
    payload: ReactionRoleCreate,
    request: Request,
) -> ReactionRoleRead:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = ReactionRoleRepository(session)
        row = await repository.upsert_binding(
            guild_id=guild_id,
            channel_id=payload.channel_id,
            message_id=payload.message_id,
            emoji=payload.emoji,
            role_id=payload.role_id,
        )
        await session.commit()
    return ReactionRoleRead.model_validate(row, from_attributes=True)


@router.delete("/{guild_id}/reaction-roles/{message_id}/{emoji}", status_code=204)
async def remove_reaction_role(
    guild_id: int,
    message_id: int,
    emoji: str,
    request: Request,
) -> None:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = ReactionRoleRepository(session)
        deleted = await repository.remove_binding(message_id, emoji)
        if not deleted:
            raise HTTPException(status_code=404, detail="reaction role binding not found")
        await session.commit()


@router.get("/{guild_id}/tickets/open", response_model=list[TicketRead])
async def list_open_tickets(guild_id: int, request: Request) -> list[TicketRead]:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = TicketRepository(session)
        rows = await repository.list_open_tickets(guild_id)
    return [TicketRead.model_validate(row, from_attributes=True) for row in rows]


@router.get("/{guild_id}/welcome", response_model=WelcomeConfigRead)
async def get_welcome_config(guild_id: int, request: Request) -> WelcomeConfigRead:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = WelcomeRepository(session)
        row = await repository.get_config(guild_id)
        if row is None:
            row = await repository.upsert_config(guild_id)
            await session.commit()
        await session.refresh(row)
        response = WelcomeConfigRead.model_validate(row, from_attributes=True)
    return response


@router.patch("/{guild_id}/welcome", response_model=WelcomeConfigRead)
async def patch_welcome_config(
    guild_id: int,
    payload: WelcomeConfigUpdate,
    request: Request,
) -> WelcomeConfigRead:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = WelcomeRepository(session)
        row = await repository.upsert_config(
            guild_id,
            channel_id=payload.channel_id,
            enabled=payload.enabled,
            message_template=payload.message_template,
        )
        await session.commit()
        await session.refresh(row)
        response = WelcomeConfigRead.model_validate(row, from_attributes=True)
    return response


@router.get("/{guild_id}/security", response_model=RaidProtectionConfigRead)
async def get_security_config(guild_id: int, request: Request) -> RaidProtectionConfigRead:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = RaidProtectionRepository(session)
        row = await repository.get_config(guild_id)
        if row is None:
            row = await repository.upsert_config(guild_id)
            await session.commit()
        await session.refresh(row)
        response = RaidProtectionConfigRead.model_validate(row, from_attributes=True)
    return response


@router.patch("/{guild_id}/security", response_model=RaidProtectionConfigRead)
async def patch_security_config(
    guild_id: int,
    payload: RaidProtectionConfigUpdate,
    request: Request,
) -> RaidProtectionConfigRead:
    session_factory = _session_factory_from_request(request)
    async with session_factory() as session:
        repository = RaidProtectionRepository(session)
        row = await repository.upsert_config(
            guild_id,
            enabled=payload.enabled,
            join_threshold=payload.join_threshold,
            window_seconds=payload.window_seconds,
            alert_channel_id=payload.alert_channel_id,
        )
        await session.commit()
        await session.refresh(row)
        response = RaidProtectionConfigRead.model_validate(row, from_attributes=True)
    return response
