from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from disnake.ext import commands

from bot.core.response_style import build_standard_embed

_UNSUPPORTED_PREFIX_KWARGS = {
    "ephemeral",
}


def _sanitize_prefix_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Remove interaction-only kwargs before proxying to prefix send APIs."""

    payload = dict(kwargs)
    for key in _UNSUPPORTED_PREFIX_KWARGS:
        payload.pop(key, None)
    return payload


@dataclass(slots=True)
class PrefixFollowupAdapter:
    ctx: commands.Context

    async def send(self, content: str | None = None, **kwargs):
        payload = _sanitize_prefix_kwargs(kwargs)
        if content is not None and "embed" not in payload and "embeds" not in payload:
            payload["embed"] = build_standard_embed(str(content))
            content = None
        return await self.ctx.send(content=content, **payload)


class PrefixResponseAdapter:
    def __init__(self, ctx: commands.Context) -> None:
        self._ctx = ctx
        self._done = False

    def is_done(self) -> bool:
        return self._done

    async def send_message(self, content: str | None = None, **kwargs):
        payload = _sanitize_prefix_kwargs(kwargs)
        if content is not None and "embed" not in payload and "embeds" not in payload:
            payload["embed"] = build_standard_embed(str(content))
            content = None
        self._done = True
        return await self._ctx.send(content=content, **payload)

    async def defer(self, **_kwargs) -> None:
        self._done = True
        await self._ctx.trigger_typing()


class PrefixInteractionAdapter:
    """Lightweight interaction-like adapter so slash logic can be reused by prefix commands."""

    def __init__(self, ctx: commands.Context) -> None:
        self._ctx = ctx
        self.response = PrefixResponseAdapter(ctx)
        self.followup = PrefixFollowupAdapter(ctx)

    @property
    def guild(self):
        return self._ctx.guild

    @property
    def guild_id(self) -> int | None:
        if self._ctx.guild is None:
            return None
        return self._ctx.guild.id

    @property
    def author(self):
        return self._ctx.author

    @property
    def channel(self):
        return self._ctx.channel

    @property
    def channel_id(self) -> int | None:
        if self._ctx.channel is None:
            return None
        return self._ctx.channel.id

    @property
    def application_command(self):
        return None

    async def edit_original_response(self, content: str | None = None, **kwargs):
        payload = _sanitize_prefix_kwargs(kwargs)
        if content is not None and "embed" not in payload and "embeds" not in payload:
            payload["embed"] = build_standard_embed(str(content))
            content = None
        return await self._ctx.send(content=content, **payload)
