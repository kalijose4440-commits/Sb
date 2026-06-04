from __future__ import annotations

from bot.core.presence import parse_presence_template, render_presence_text


def test_parse_presence_template_understands_activity_and_status() -> None:
    parsed = parse_presence_template("watching::{users} members::idle")

    assert parsed.activity_type == "watching"
    assert parsed.text == "{users} members"
    assert parsed.status.name == "idle"


def test_render_presence_text_populates_placeholders() -> None:
    rendered = render_presence_text(
        "Serving {guilds} guilds and {users} users for {uptime}",
        guild_count=12,
        member_count=345,
        uptime_seconds=3600,
    )

    assert "12" in rendered
    assert "345" in rendered
    assert "1h" in rendered
