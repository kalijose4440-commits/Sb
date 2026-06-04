from __future__ import annotations


def render_welcome_message(template: str, *, guild_name: str, user_name: str, mention: str) -> str:
    """Render welcome templates with common placeholders."""

    return (
        template.replace("{guild}", guild_name)
        .replace("{user}", user_name)
        .replace("{mention}", mention)
    )
