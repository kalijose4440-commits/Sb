from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GuildSettingsRead(BaseModel):
    guild_id: int
    prefix: str
    status: str
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class GuildSettingsUpdate(BaseModel):
    prefix: str | None = Field(default=None, min_length=1, max_length=16)
    status: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def require_change(self) -> "GuildSettingsUpdate":
        if self.prefix is None and self.status is None:
            raise ValueError("at least one setting field must be provided")
        return self
