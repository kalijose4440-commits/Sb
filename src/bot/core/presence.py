from __future__ import annotations

from dataclasses import dataclass

import disnake


@dataclass(frozen=True)
class PresenceTemplate:
    """Represents one rotating activity/status frame."""

    activity_type: str
    text: str
    status: disnake.Status


def parse_presence_template(raw: str) -> PresenceTemplate:
    """Parse `activity::text::status` strings into typed templates."""

    parts = [part.strip() for part in raw.split("::")]

    activity_type = "playing"
    text = "Serving your community"
    status_key = "online"

    if len(parts) == 1 and parts[0]:
        text = parts[0]
    elif len(parts) >= 2:
        activity_type = parts[0].lower() or "playing"
        text = parts[1] or text
        if len(parts) >= 3 and parts[2]:
            status_key = parts[2].lower()

    status_map: dict[str, disnake.Status] = {
        "online": disnake.Status.online,
        "idle": disnake.Status.idle,
        "dnd": disnake.Status.dnd,
        "invisible": disnake.Status.invisible,
    }
    status = status_map.get(status_key, disnake.Status.online)

    return PresenceTemplate(activity_type=activity_type, text=text, status=status)


def format_uptime_short(total_seconds: int) -> str:
    """Render uptime in a compact `Xd Yh Zm` style."""

    days, rem = divmod(max(total_seconds, 0), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _seconds = divmod(rem, 60)

    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def render_presence_text(
    text_template: str,
    *,
    guild_count: int,
    member_count: int,
    uptime_seconds: int,
) -> str:
    """Render runtime placeholders used in activity text templates."""

    return (
        text_template.replace("{guilds}", str(guild_count))
        .replace("{users}", str(member_count))
        .replace("{uptime}", format_uptime_short(uptime_seconds))
    )


def build_activity(activity_type: str, text: str) -> disnake.BaseActivity:
    """Create a Discord activity object from a normalized type string."""

    normalized = activity_type.lower().strip()
    if normalized == "watching":
        return disnake.Activity(type=disnake.ActivityType.watching, name=text)
    if normalized == "listening":
        return disnake.Activity(type=disnake.ActivityType.listening, name=text)
    if normalized == "competing":
        return disnake.Activity(type=disnake.ActivityType.competing, name=text)

    return disnake.Game(name=text)
