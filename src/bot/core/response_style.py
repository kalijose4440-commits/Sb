from __future__ import annotations

# mypy: ignore-errors
from typing import Any

import disnake

_PATCH_INSTALLED = False


def build_standard_embed(description: str, *, title: str = "Bot") -> disnake.Embed:
    """Build a default embed used for command responses."""

    embed = disnake.Embed(
        title=title,
        description=description,
        color=disnake.Color.blurple(),
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

    if (
        content is not None
        and "embed" not in payload
        and "embeds" not in payload
    ):
        payload["embed"] = build_standard_embed(str(content))
        content = None

    return content, payload


def install_interaction_response_style_patch() -> None:
    """Patch interaction responses to default to public embed-style output."""

    global _PATCH_INSTALLED
    if _PATCH_INSTALLED:
        return

    original_send_message = disnake.InteractionResponse.send_message
    original_edit_original_response = disnake.Interaction.edit_original_response
    original_webhook_send = disnake.Webhook.send

    async def patched_send_message(
        self: disnake.InteractionResponse,
        content=None,
        *args,
        **kwargs,
    ):
        coerced_content, payload = _coerce_embed_payload(
            content,
            kwargs,
            force_public=True,
        )
        return await original_send_message(self, coerced_content, *args, **payload)

    async def patched_edit_original_response(
        self: disnake.Interaction,
        content=None,
        *args,
        **kwargs,
    ):
        coerced_content, payload = _coerce_embed_payload(
            content,
            kwargs,
            force_public=False,
        )
        return await original_edit_original_response(self, coerced_content, *args, **payload)

    async def patched_webhook_send(self: disnake.Webhook, content=None, *args, **kwargs):
        coerced_content, payload = _coerce_embed_payload(
            content,
            kwargs,
            force_public=True,
        )
        return await original_webhook_send(self, coerced_content, *args, **payload)

    disnake.InteractionResponse.send_message = patched_send_message
    disnake.Interaction.edit_original_response = patched_edit_original_response
    disnake.Webhook.send = patched_webhook_send

    _PATCH_INSTALLED = True
