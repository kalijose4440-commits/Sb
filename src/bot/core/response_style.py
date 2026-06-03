from __future__ import annotations

# mypy: ignore-errors
from datetime import UTC, datetime
from typing import Any

import disnake

_PATCH_INSTALLED = False


def build_standard_embed(
    description: str,
    *,
    title: str = "ODF 1.0",
    color: disnake.Color | None = None,
) -> disnake.Embed:
    """Build a polished default embed used for bot command responses."""

    embed = disnake.Embed(
        title=title,
        description=description,
        color=color or disnake.Color.dark_blue(),
        timestamp=datetime.now(UTC),
    )
    return embed


def _coerce_embed_payload(
    content: str | None,
    kwargs: dict[str, Any],
    *,
    force_public: bool,
) -> tuple[str | None, dict[str, Any]]:
    payload = dict(kwargs)

    if force_public:
        payload["ephemeral"] = False

    if content is not None and "embed" not in payload and "embeds" not in payload:
        payload["embed"] = build_standard_embed(str(content))
        content = None

    return content, payload


def install_interaction_response_style_patch() -> None:
    """Patch interaction responses to default to public embed-style output."""

    global _PATCH_INSTALLED
    if _PATCH_INSTALLED:
        return

    interaction_response_cls = disnake.InteractionResponse
    interaction_cls = disnake.Interaction
    webhook_cls = disnake.Webhook

    original_send_message = interaction_response_cls.send_message
    original_edit_original_response = interaction_cls.edit_original_response
    original_webhook_send = webhook_cls.send

    async def patched_send_message(self, content=None, *args, **kwargs):
        coerced_content, payload = _coerce_embed_payload(content, kwargs, force_public=True)
        return await original_send_message(self, coerced_content, *args, **payload)

    async def patched_edit_original_response(self, content=None, *args, **kwargs):
        coerced_content, payload = _coerce_embed_payload(content, kwargs, force_public=False)
        return await original_edit_original_response(self, coerced_content, *args, **payload)

    async def patched_webhook_send(self, content=None, *args, **kwargs):
        coerced_content, payload = _coerce_embed_payload(content, kwargs, force_public=True)
        return await original_webhook_send(self, coerced_content, *args, **payload)

    interaction_response_cls.send_message = patched_send_message
    interaction_cls.edit_original_response = patched_edit_original_response
    webhook_cls.send = patched_webhook_send

    _PATCH_INSTALLED = True
