from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AutoModKeywordCreate(BaseModel):
    keyword: str = Field(min_length=1, max_length=120)
    action: str = Field(default="delete", pattern="^(delete|warn)$")


class AutoModKeywordRead(BaseModel):
    id: int
    guild_id: int
    keyword: str
    action: str
    enabled: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnnouncementCreate(BaseModel):
    channel_id: int
    content: str = Field(min_length=1, max_length=1900)
    interval_minutes: int = Field(ge=1, le=10080)


class AnnouncementToggle(BaseModel):
    enabled: bool


class AnnouncementRead(BaseModel):
    id: int
    guild_id: int
    channel_id: int
    content: str
    interval_minutes: int
    next_run_at: datetime
    enabled: bool
    last_run_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ReactionRoleCreate(BaseModel):
    channel_id: int
    message_id: int
    emoji: str = Field(min_length=1, max_length=128)
    role_id: int


class ReactionRoleRead(BaseModel):
    id: int
    guild_id: int
    channel_id: int
    message_id: int
    emoji: str
    role_id: int

    model_config = ConfigDict(from_attributes=True)


class TicketRead(BaseModel):
    id: int
    guild_id: int
    channel_id: int
    owner_id: int
    subject: str
    status: str
    priority: str
    escalated: bool
    escalated_role_id: int | None
    escalated_at: datetime | None
    created_at: datetime
    closed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TicketEscalationUpdate(BaseModel):
    priority: str = Field(default="high", pattern="^(low|normal|high|critical)$")
    escalated_role_id: int | None = None


class TicketTranscriptRead(BaseModel):
    id: int
    ticket_id: int
    guild_id: int
    channel_id: int
    generated_by_user_id: int
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WelcomeConfigUpdate(BaseModel):
    channel_id: int | None = None
    enabled: bool | None = None
    message_template: str | None = Field(default=None, min_length=1, max_length=1800)


class WelcomeConfigRead(BaseModel):
    guild_id: int
    channel_id: int | None
    enabled: bool
    message_template: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RaidProtectionConfigUpdate(BaseModel):
    enabled: bool | None = None
    join_threshold: int | None = Field(default=None, ge=3, le=100)
    window_seconds: int | None = Field(default=None, ge=10, le=600)
    alert_channel_id: int | None = None
    mitigation_action: str | None = Field(default=None, pattern="^(none|verification_high)$")
    mitigation_duration_seconds: int | None = Field(default=None, ge=60, le=14400)


class RaidProtectionConfigRead(BaseModel):
    guild_id: int
    enabled: bool
    join_threshold: int
    window_seconds: int
    alert_channel_id: int | None
    mitigation_action: str
    mitigation_duration_seconds: int
    mitigation_active_until: datetime | None
    previous_verification_level: int | None
    last_triggered_at: datetime | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AclRuleWrite(BaseModel):
    command_name: str = Field(min_length=1, max_length=120)
    role_id: int


class AclRuleRead(BaseModel):
    id: int
    guild_id: int
    command_name: str
    role_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)



class MusicConfigUpdate(BaseModel):
    default_volume: int | None = Field(default=None, ge=1, le=200)
    autoplay: bool | None = None
    max_queue_size: int | None = Field(default=None, ge=1, le=500)


class MusicConfigRead(BaseModel):
    guild_id: int
    default_volume: int
    autoplay: bool
    max_queue_size: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
