from __future__ import annotations

from datetime import UTC

import disnake


async def build_text_transcript(channel: disnake.TextChannel, *, limit: int = 500) -> str:
    """Build a plain-text transcript from recent channel history."""

    lines = [
        f"Transcript for #{channel.name} ({channel.id})",
        f"Guild: {channel.guild.name} ({channel.guild.id})",
        "-" * 72,
    ]

    async for message in channel.history(limit=limit, oldest_first=True):
        timestamp = message.created_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        content = message.clean_content.strip()

        if message.attachments:
            attachment_urls = ", ".join(attachment.url for attachment in message.attachments)
            content = f"{content} [attachments: {attachment_urls}]".strip()

        if not content:
            if message.embeds:
                content = "[embed]"
            else:
                content = "[no text content]"

        lines.append(f"[{timestamp}] {message.author} ({message.author.id}): {content}")

    return "\n".join(lines)
