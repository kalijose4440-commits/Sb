from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta

from bot.core.onboarding import render_welcome_message
from bot.core.security import should_emit_alert, update_join_window


def test_render_welcome_message_replaces_placeholders() -> None:
    rendered = render_welcome_message(
        "Welcome {mention} ({user}) to {guild}!",
        guild_name="ExampleGuild",
        user_name="Alex",
        mention="@Alex",
    )
    assert rendered == "Welcome @Alex (Alex) to ExampleGuild!"


def test_update_join_window_prunes_old_events() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    joins = deque([now - timedelta(seconds=90), now - timedelta(seconds=20)])

    join_count = update_join_window(joins, now, window_seconds=30)

    assert join_count == 2
    assert joins[0] == now - timedelta(seconds=20)


def test_should_emit_alert_respects_threshold_and_cooldown() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert should_emit_alert(
        join_count=12,
        threshold=8,
        last_alert_at=None,
        now=now,
        cooldown_seconds=30,
    )
    assert not should_emit_alert(
        join_count=12,
        threshold=8,
        last_alert_at=now - timedelta(seconds=10),
        now=now,
        cooldown_seconds=30,
    )
