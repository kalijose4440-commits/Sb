from __future__ import annotations

from datetime import UTC, datetime

from bot.cogs.utility import format_uptime
from bot.core.config import Settings


def test_format_uptime_includes_expected_units() -> None:
    started = datetime(2026, 1, 1, tzinfo=UTC)
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    assert format_uptime(started, now=now) == "1d 3h 4m 5s"


def test_default_cogs_include_premium_suite() -> None:
    settings = Settings(discord_token="token", database_url="sqlite+aiosqlite:///tmp/test.db")

    expected = {
        "bot.cogs.admin",
        "bot.cogs.utility",
        "bot.cogs.moderation",
        "bot.cogs.welcome",
        "bot.cogs.security",
        "bot.cogs.acl",
        "bot.cogs.tickets",
        "bot.cogs.automod",
        "bot.cogs.reaction_roles",
        "bot.cogs.announcements",
        "bot.cogs.analytics",
        "bot.cogs.presence",
    }
    assert expected.issubset(set(settings.cog_extensions))
