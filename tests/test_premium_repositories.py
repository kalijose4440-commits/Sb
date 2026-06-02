from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bot.db.repositories import (
    AnalyticsRepository,
    AnnouncementRepository,
    AutoModRepository,
    ReactionRoleRepository,
    TicketRepository,
)
from bot.db.session import create_engine_and_sessionmaker, init_db


@pytest.mark.asyncio
async def test_premium_repositories_round_trip(tmp_path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'premium_repos.db'}"
    engine, session_factory = create_engine_and_sessionmaker(database_url)
    await init_db(engine)

    async with session_factory() as session:
        automod = AutoModRepository(session)
        ticket_repo = TicketRepository(session)
        reaction_repo = ReactionRoleRepository(session)
        announcement_repo = AnnouncementRepository(session)
        analytics_repo = AnalyticsRepository(session)

        rule = await automod.add_keyword(guild_id=1, keyword="spoiler", action="delete")
        assert rule.keyword == "spoiler"
        matches = await automod.find_matching_keywords(1, "this contains spoiler text")
        assert len(matches) == 1

        ticket = await ticket_repo.create_ticket(1, 101, 202, "Need help")
        assert ticket.status == "open"
        await ticket_repo.close_ticket(101)
        assert (await ticket_repo.get_by_channel_id(101)).status == "closed"

        binding = await reaction_repo.upsert_binding(
            guild_id=1,
            channel_id=777,
            message_id=888,
            emoji="fire",
            role_id=999,
        )
        assert binding.role_id == 999
        assert await reaction_repo.remove_binding(888, "fire") is True

        announcement = await announcement_repo.create_announcement(
            guild_id=1,
            channel_id=777,
            content="hello world",
            interval_minutes=10,
        )
        due = await announcement_repo.due_announcements(datetime.now(UTC) + timedelta(minutes=15))
        assert any(row.id == announcement.id for row in due)

        await analytics_repo.record_usage(guild_id=1, channel_id=2, user_id=3, command_name="ticket open")
        await analytics_repo.record_usage(guild_id=1, channel_id=2, user_id=3, command_name="ticket open")
        await analytics_repo.record_usage(guild_id=1, channel_id=2, user_id=4, command_name="ping")

        top_commands = await analytics_repo.top_commands(guild_id=1, limit=5)
        assert top_commands[0][0] == "ticket open"
        assert top_commands[0][1] == 2

        await session.commit()

    await engine.dispose()
