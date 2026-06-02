from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized runtime configuration loaded from environment variables."""

    discord_token: str = Field(default="replace-with-token")
    database_url: str = Field(
        default="postgresql+asyncpg://bot_user:bot_password@localhost:5432/bot_db"
    )
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = Field(default="INFO")

    default_prefix: str = Field(default="!", min_length=1, max_length=16)
    default_status: str = Field(default="online", min_length=1, max_length=64)
    bot_activity: str = Field(default="Serving your community")

    announcement_poll_seconds: int = Field(default=30, ge=5, le=3600)
    presence_rotation_seconds: int = Field(default=120, ge=20, le=3600)
    presence_templates: tuple[str, ...] = (
        "playing::Helping {guilds} guilds::online",
        "watching::{users} members thrive::online",
        "listening::/ticket open requests::idle",
        "competing::Uptime {uptime}::online",
    )

    cog_extensions: tuple[str, ...] = (
        "bot.cogs.admin",
        "bot.cogs.utility",
        "bot.cogs.moderation",
        "bot.cogs.tickets",
        "bot.cogs.automod",
        "bot.cogs.reaction_roles",
        "bot.cogs.announcements",
        "bot.cogs.analytics",
        "bot.cogs.presence",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.upper()
