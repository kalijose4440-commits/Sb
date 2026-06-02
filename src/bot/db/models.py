from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class GuildSettings(Base):
    """Persistent guild-level dashboard settings."""

    __tablename__ = "guild_settings"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, default="!")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="online")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
