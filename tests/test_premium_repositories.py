from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from bot.db.repositories import (
    AnalyticsRepository,
    AnnouncementRepository,
    AutoModRepository,
    CommandAclRepository,
    MusicConfigRepository,
    RaidProtectionRepository,
    ReactionRoleRepository,
    TicketRepository,
    WelcomeRepository,
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
        welcome_repo = WelcomeRepository(session)
        raid_repo = RaidProtectionRepository(session)
        music_repo = MusicConfigRepository(session)
        acl_repo = CommandAclRepository(session)

        rule = await automod.add_keyword(guild_id=1, keyword="spoiler", action="delete")
        assert rule.keyword == "spoiler"
        matches = await automod.find_matching_keywords(1, "this contains spoiler text")
        assert len(matches) == 1

        ticket = await ticket_repo.create_ticket(1, 101, 202, "Need help")
        assert ticket.status == "open"
        escalated = await ticket_repo.escalate_ticket(
            101,
            priority="critical",
            escalated_role_id=999,
        )
        assert escalated is not None
        assert escalated.priority == "critical"
        assert escalated.escalated is True

        transcript = await ticket_repo.create_transcript(
            ticket_id=ticket.id,
            guild_id=1,
            channel_id=101,
            generated_by_user_id=202,
            content="sample transcript",
        )
        assert transcript.ticket_id == ticket.id
        assert (
            len(await ticket_repo.list_transcripts_for_ticket(guild_id=1, ticket_id=ticket.id)) == 1
        )

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

        welcome = await welcome_repo.upsert_config(
            guild_id=1,
            channel_id=321,
            enabled=True,
            message_template="Welcome {mention}!",
        )
        assert welcome.channel_id == 321
        assert welcome.enabled is True

        raid = await raid_repo.upsert_config(
            guild_id=1,
            enabled=True,
            join_threshold=6,
            window_seconds=20,
            alert_channel_id=321,
            mitigation_action="verification_high",
            mitigation_duration_seconds=600,
        )
        assert raid.enabled is True
        assert raid.join_threshold == 6
        assert raid.window_seconds == 20
        assert raid.mitigation_action == "verification_high"

        active_until = datetime.now(UTC) + timedelta(minutes=5)
        await raid_repo.mark_mitigation_started(
            guild_id=1,
            previous_verification_level=1,
            active_until=active_until,
        )
        due_releases = await raid_repo.due_mitigation_releases(
            datetime.now(UTC) + timedelta(minutes=6)
        )
        assert any(row.guild_id == 1 for row in due_releases)
        await raid_repo.clear_mitigation(1)
        assert (await raid_repo.get_config(1)).mitigation_active_until is None

        await raid_repo.mark_triggered(guild_id=1, triggered_at=datetime.now(UTC))
        assert (await raid_repo.get_config(1)).last_triggered_at is not None


        music = await music_repo.upsert_config(
            guild_id=1,
            default_volume=75,
            autoplay=True,
            max_queue_size=180,
        )
        assert music.default_volume == 75
        assert music.autoplay is True
        assert music.max_queue_size == 180

        await acl_repo.allow_role(guild_id=1, command_name="ticket open", role_id=500)
        await acl_repo.allow_role(guild_id=1, command_name="ticket open", role_id=600)
        role_ids = await acl_repo.role_ids_for_command(1, "ticket open")
        assert sorted(role_ids) == [500, 600]
        assert await acl_repo.revoke_role(guild_id=1, command_name="ticket open", role_id=500)

        await analytics_repo.record_usage(
            guild_id=1,
            channel_id=2,
            user_id=3,
            command_name="ticket open",
        )
        await analytics_repo.record_usage(
            guild_id=1,
            channel_id=2,
            user_id=3,
            command_name="ticket open",
        )
        await analytics_repo.record_usage(guild_id=1, channel_id=2, user_id=4, command_name="ping")

        top_commands = await analytics_repo.top_commands(guild_id=1, limit=5)
        assert top_commands[0][0] == "ticket open"
        assert top_commands[0][1] == 2

        await session.commit()

    await engine.dispose()
