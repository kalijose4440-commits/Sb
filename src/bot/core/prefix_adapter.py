from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import disnake
from disnake.ext import commands

from bot.core.i18n import normalize_language, translate_runtime_text
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


async def _resolved_locale(ctx: commands.Context) -> str:
    bot = getattr(ctx, "bot", None)
    bridge = getattr(bot, "bridge", None)
    guild = getattr(ctx, "guild", None)
    if guild is None or bridge is None:
        settings = getattr(bot, "settings", None)
        default_language = "en"
        if settings is not None:
            default_language = getattr(settings, "default_language", default_language)
        return normalize_language(default_language)

    try:
        snapshot = await bridge.get_or_load_settings(guild.id)
        return normalize_language(getattr(snapshot, "language", "en"))
    except Exception:
        logger = getattr(bot, "logger", None)
        if logger is not None:
            logger.exception(
                "prefix_locale_resolution_failed",
                extra={"guild_id": guild.id},
            )
        return "en"


def _translate_embed(embed: disnake.Embed, locale: str) -> disnake.Embed:
    data = embed.to_dict()

    if isinstance(data.get("title"), str):
        data["title"] = translate_runtime_text(locale, data["title"])
    if isinstance(data.get("description"), str):
        data["description"] = translate_runtime_text(locale, data["description"])

    footer = data.get("footer")
    if isinstance(footer, dict) and isinstance(footer.get("text"), str):
        footer["text"] = translate_runtime_text(locale, footer["text"])

    fields = data.get("fields")
    if isinstance(fields, list):
        for field in fields:
            if isinstance(field, dict):
                if isinstance(field.get("name"), str):
                    field["name"] = translate_runtime_text(locale, field["name"])
                if isinstance(field.get("value"), str):
                    field["value"] = translate_runtime_text(locale, field["value"])

    return disnake.Embed.from_dict(data)


async def _localize_payload(
    ctx: commands.Context,
    content: str | None,
    payload: dict[str, Any],
) -> tuple[str | None, dict[str, Any]]:
    locale = await _resolved_locale(ctx)

    localized_content = (
        translate_runtime_text(locale, content)
        if isinstance(content, str)
        else content
    )

    localized_payload = dict(payload)

    embed = localized_payload.get("embed")
    if isinstance(embed, disnake.Embed):
        localized_payload["embed"] = _translate_embed(embed, locale)

    embeds = localized_payload.get("embeds")
    if isinstance(embeds, list):
        localized_payload["embeds"] = [
            _translate_embed(embed, locale) if isinstance(embed, disnake.Embed) else embed
            for embed in embeds
        ]

    if isinstance(localized_payload.get("content"), str):
        localized_payload["content"] = translate_runtime_text(locale, localized_payload["content"])

    return localized_content, localized_payload


@dataclass(slots=True)
class PrefixFollowupAdapter:
    ctx: commands.Context

    async def send(self, content: str | None = None, **kwargs):
        payload = _sanitize_prefix_kwargs(kwargs)
        content, payload = await _localize_payload(self.ctx, content, payload)
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
        content, payload = await _localize_payload(self._ctx, content, payload)
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
        content, payload = await _localize_payload(self._ctx, content, payload)
        if content is not None and "embed" not in payload and "embeds" not in payload:
            payload["embed"] = build_standard_embed(str(content))
            content = None
        return await self._ctx.send(content=content, **payload)
