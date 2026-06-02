from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from disnake.ext import commands, tasks

from bot.core.presence import (
    build_activity,
    parse_presence_template,
    render_presence_text,
)


class PresenceCog(commands.Cog):
    """Rotates rich activity presence based on configurable templates."""

    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot
        settings = cast(Any, bot).settings
        raw_templates = settings.presence_templates
        self._templates = [parse_presence_template(raw) for raw in raw_templates]
        self._index = 0

        self._presence_loop.change_interval(seconds=settings.presence_rotation_seconds)
        self._presence_loop.start()

    def cog_unload(self) -> None:
        self._presence_loop.cancel()

    @tasks.loop(seconds=120)
    async def _presence_loop(self) -> None:
        if not self._templates:
            return

        template = self._templates[self._index % len(self._templates)]
        self._index += 1

        guild_count = len(self.bot.guilds)
        member_count = sum(guild.member_count or 0 for guild in self.bot.guilds)
        started_at = getattr(self.bot, "started_at", datetime.now(UTC))
        uptime_seconds = int((datetime.now(UTC) - started_at).total_seconds())

        rendered_text = render_presence_text(
            template.text,
            guild_count=guild_count,
            member_count=member_count,
            uptime_seconds=uptime_seconds,
        )
        activity = build_activity(template.activity_type, rendered_text)
        await self.bot.change_presence(status=template.status, activity=activity)

    @_presence_loop.before_loop
    async def _before_loop(self) -> None:
        await self.bot.wait_until_ready()


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(PresenceCog(bot=bot))
