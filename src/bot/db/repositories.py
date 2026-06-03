from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import (
    AutoModKeyword,
    CommandAclEntry,
    CommandUsageMetric,
    GuildSettings,
    MusicConfig,
    RaidProtectionConfig,
    ReactionRoleBinding,
    ScheduledAnnouncement,
    TicketThread,
    TicketTranscript,
    WelcomeConfig,
)


def normalize_command_name(command_name: str) -> str:
    return command_name.strip().lower()


class GuildSettingsRepository:
    """Data access boundary for guild settings."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_guild_id(self, guild_id: int) -> GuildSettings | None:
        statement = select(GuildSettings).where(GuildSettings.guild_id == guild_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        guild_id: int,
        *,
        prefix: str | None = None,
        status: str | None = None,
        language: str | None = None,
        default_prefix: str = "!",
        default_status: str = "online",
        default_language: str = "en",
    ) -> GuildSettings:
        row = await self.get_by_guild_id(guild_id)
        if row is None:
            row = GuildSettings(
                guild_id=guild_id,
                prefix=prefix or default_prefix,
                status=status or default_status,
                language=language or default_language,
            )
            self._session.add(row)
        else:
            if prefix is not None:
                row.prefix = prefix
            if status is not None:
                row.status = status
            if language is not None:
                row.language = language

        await self._session.flush()
        return row

    async def upsert_prefix(
        self,
        guild_id: int,
        prefix: str,
        *,
        default_status: str = "online",
        default_language: str = "en",
    ) -> GuildSettings:
        return await self.upsert(
            guild_id,
            prefix=prefix,
            default_status=default_status,
            default_language=default_language,
        )

    async def upsert_status(
        self,
        guild_id: int,
        status: str,
        *,
        default_prefix: str = "!",
        default_language: str = "en",
    ) -> GuildSettings:
        return await self.upsert(
            guild_id,
            status=status,
            default_prefix=default_prefix,
            default_language=default_language,
        )

    async def upsert_language(
        self,
        guild_id: int,
        language: str,
        *,
        default_prefix: str = "!",
        default_status: str = "online",
    ) -> GuildSettings:
        return await self.upsert(
            guild_id,
            language=language,
            default_prefix=default_prefix,
            default_status=default_status,
            default_language=language,
        )


class TicketRepository:
    """CRUD operations for ticket channels, escalation, and transcripts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_ticket(
        self,
        guild_id: int,
        channel_id: int,
        owner_id: int,
        subject: str,
    ) -> TicketThread:
        row = TicketThread(
            guild_id=guild_id,
            channel_id=channel_id,
            owner_id=owner_id,
            subject=subject,
            status="open",
            priority="normal",
            escalated=False,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_by_channel_id(self, channel_id: int) -> TicketThread | None:
        statement = select(TicketThread).where(TicketThread.channel_id == channel_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_ticket_id(self, guild_id: int, ticket_id: int) -> TicketThread | None:
        statement = select(TicketThread).where(
            TicketThread.guild_id == guild_id,
            TicketThread.id == ticket_id,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_open_by_owner(self, guild_id: int, owner_id: int) -> TicketThread | None:
        statement = select(TicketThread).where(
            TicketThread.guild_id == guild_id,
            TicketThread.owner_id == owner_id,
            TicketThread.status == "open",
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def close_ticket(self, channel_id: int) -> TicketThread | None:
        row = await self.get_by_channel_id(channel_id)
        if row is None:
            return None

        row.status = "closed"
        row.closed_at = datetime.now(UTC)
        await self._session.flush()
        return row

    async def escalate_ticket(
        self,
        channel_id: int,
        *,
        priority: str,
        escalated_role_id: int | None,
    ) -> TicketThread | None:
        row = await self.get_by_channel_id(channel_id)
        if row is None:
            return None

        row.priority = priority
        row.escalated = True
        row.escalated_role_id = escalated_role_id
        row.escalated_at = datetime.now(UTC)
        await self._session.flush()
        return row

    async def list_open_tickets(self, guild_id: int) -> list[TicketThread]:
        statement = (
            select(TicketThread)
            .where(TicketThread.guild_id == guild_id, TicketThread.status == "open")
            .order_by(desc(TicketThread.created_at))
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def create_transcript(
        self,
        *,
        ticket_id: int,
        guild_id: int,
        channel_id: int,
        generated_by_user_id: int,
        content: str,
    ) -> TicketTranscript:
        row = TicketTranscript(
            ticket_id=ticket_id,
            guild_id=guild_id,
            channel_id=channel_id,
            generated_by_user_id=generated_by_user_id,
            content=content,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_transcripts_for_ticket(
        self,
        *,
        guild_id: int,
        ticket_id: int,
        limit: int = 20,
    ) -> list[TicketTranscript]:
        statement = (
            select(TicketTranscript)
            .where(
                TicketTranscript.guild_id == guild_id,
                TicketTranscript.ticket_id == ticket_id,
            )
            .order_by(desc(TicketTranscript.created_at))
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())


class AutoModRepository:
    """CRUD and matching logic for automod keyword rules."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_keyword(self, guild_id: int, keyword: str, action: str) -> AutoModKeyword:
        statement = select(AutoModKeyword).where(
            AutoModKeyword.guild_id == guild_id,
            AutoModKeyword.keyword == keyword,
        )
        result = await self._session.execute(statement)
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.action = action
            existing.enabled = True
            await self._session.flush()
            return existing

        row = AutoModKeyword(guild_id=guild_id, keyword=keyword, action=action, enabled=True)
        self._session.add(row)
        await self._session.flush()
        return row

    async def remove_keyword(self, guild_id: int, keyword: str) -> bool:
        statement = select(AutoModKeyword).where(
            AutoModKeyword.guild_id == guild_id,
            AutoModKeyword.keyword == keyword,
        )
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        if row is None:
            return False

        await self._session.delete(row)
        await self._session.flush()
        return True

    async def list_keywords(self, guild_id: int) -> list[AutoModKeyword]:
        statement = (
            select(AutoModKeyword)
            .where(AutoModKeyword.guild_id == guild_id)
            .order_by(desc(AutoModKeyword.created_at))
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def set_keyword_enabled(self, keyword_id: int, enabled: bool) -> AutoModKeyword | None:
        statement = select(AutoModKeyword).where(AutoModKeyword.id == keyword_id)
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        if row is None:
            return None

        row.enabled = enabled
        await self._session.flush()
        return row

    async def find_matching_keywords(self, guild_id: int, content: str) -> list[AutoModKeyword]:
        normalized_content = content.lower()
        statement = select(AutoModKeyword).where(
            AutoModKeyword.guild_id == guild_id,
            AutoModKeyword.enabled.is_(True),
        )
        result = await self._session.execute(statement)
        rules = list(result.scalars().all())
        return [rule for rule in rules if rule.keyword.lower() in normalized_content]


class ReactionRoleRepository:
    """Manages emoji-to-role bindings for reaction role workflows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_binding(
        self,
        guild_id: int,
        channel_id: int,
        message_id: int,
        emoji: str,
        role_id: int,
    ) -> ReactionRoleBinding:
        statement = select(ReactionRoleBinding).where(
            ReactionRoleBinding.message_id == message_id,
            ReactionRoleBinding.emoji == emoji,
        )
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        if row is None:
            row = ReactionRoleBinding(
                guild_id=guild_id,
                channel_id=channel_id,
                message_id=message_id,
                emoji=emoji,
                role_id=role_id,
            )
            self._session.add(row)
        else:
            row.guild_id = guild_id
            row.channel_id = channel_id
            row.role_id = role_id

        await self._session.flush()
        return row

    async def remove_binding(self, message_id: int, emoji: str) -> bool:
        statement = select(ReactionRoleBinding).where(
            ReactionRoleBinding.message_id == message_id,
            ReactionRoleBinding.emoji == emoji,
        )
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        if row is None:
            return False

        await self._session.delete(row)
        await self._session.flush()
        return True

    async def list_bindings(self, guild_id: int) -> list[ReactionRoleBinding]:
        statement = (
            select(ReactionRoleBinding)
            .where(ReactionRoleBinding.guild_id == guild_id)
            .order_by(desc(ReactionRoleBinding.created_at))
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_binding_by_payload(
        self,
        message_id: int,
        emoji: str,
    ) -> ReactionRoleBinding | None:
        statement = select(ReactionRoleBinding).where(
            ReactionRoleBinding.message_id == message_id,
            ReactionRoleBinding.emoji == emoji,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()


class AnnouncementRepository:
    """Manages recurring announcement jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_announcement(
        self,
        guild_id: int,
        channel_id: int,
        content: str,
        interval_minutes: int,
    ) -> ScheduledAnnouncement:
        now = datetime.now(UTC)
        next_run_at = now + timedelta(minutes=interval_minutes)
        row = ScheduledAnnouncement(
            guild_id=guild_id,
            channel_id=channel_id,
            content=content,
            interval_minutes=interval_minutes,
            next_run_at=next_run_at,
            enabled=True,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_announcements(self, guild_id: int) -> list[ScheduledAnnouncement]:
        statement = (
            select(ScheduledAnnouncement)
            .where(ScheduledAnnouncement.guild_id == guild_id)
            .order_by(desc(ScheduledAnnouncement.created_at))
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_announcement(
        self,
        guild_id: int,
        announcement_id: int,
    ) -> ScheduledAnnouncement | None:
        statement = select(ScheduledAnnouncement).where(
            ScheduledAnnouncement.guild_id == guild_id,
            ScheduledAnnouncement.id == announcement_id,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def set_enabled(
        self,
        guild_id: int,
        announcement_id: int,
        enabled: bool,
    ) -> ScheduledAnnouncement | None:
        row = await self.get_announcement(guild_id, announcement_id)
        if row is None:
            return None

        row.enabled = enabled
        await self._session.flush()
        return row

    async def due_announcements(self, now: datetime) -> list[ScheduledAnnouncement]:
        statement = (
            select(ScheduledAnnouncement)
            .where(
                ScheduledAnnouncement.enabled.is_(True),
                ScheduledAnnouncement.next_run_at <= now,
            )
            .order_by(ScheduledAnnouncement.next_run_at)
            .limit(50)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def mark_ran(
        self,
        announcement_id: int,
        *,
        last_run_at: datetime,
        next_run_at: datetime,
    ) -> ScheduledAnnouncement | None:
        statement = select(ScheduledAnnouncement).where(ScheduledAnnouncement.id == announcement_id)
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        if row is None:
            return None

        row.last_run_at = last_run_at
        row.next_run_at = next_run_at
        await self._session.flush()
        return row


class AnalyticsRepository:
    """Writes and aggregates command usage metrics."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_usage(
        self,
        *,
        guild_id: int | None,
        channel_id: int | None,
        user_id: int,
        command_name: str,
    ) -> CommandUsageMetric:
        row = CommandUsageMetric(
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            command_name=command_name,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def top_commands(self, guild_id: int, limit: int = 10) -> list[tuple[str, int]]:
        statement = (
            select(CommandUsageMetric.command_name, func.count(CommandUsageMetric.id).label("uses"))
            .where(CommandUsageMetric.guild_id == guild_id)
            .group_by(CommandUsageMetric.command_name)
            .order_by(desc("uses"), CommandUsageMetric.command_name)
            .limit(limit)
        )
        result = await self._session.execute(statement)
        rows = result.all()
        return [(cast(str, name), int(uses)) for name, uses in rows]

    async def top_users(self, guild_id: int, limit: int = 10) -> list[tuple[int, int]]:
        statement = (
            select(CommandUsageMetric.user_id, func.count(CommandUsageMetric.id).label("uses"))
            .where(CommandUsageMetric.guild_id == guild_id)
            .group_by(CommandUsageMetric.user_id)
            .order_by(desc("uses"), CommandUsageMetric.user_id)
            .limit(limit)
        )
        result = await self._session.execute(statement)
        rows = result.all()
        return [(int(user_id), int(uses)) for user_id, uses in rows]


class WelcomeRepository:
    """CRUD access for guild welcome message settings."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_config(self, guild_id: int) -> WelcomeConfig | None:
        statement = select(WelcomeConfig).where(WelcomeConfig.guild_id == guild_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_config(
        self,
        guild_id: int,
        *,
        channel_id: int | None = None,
        enabled: bool | None = None,
        message_template: str | None = None,
        default_template: str = "Welcome {mention} to {guild}!",
    ) -> WelcomeConfig:
        row = await self.get_config(guild_id)
        if row is None:
            row = WelcomeConfig(
                guild_id=guild_id,
                channel_id=channel_id,
                enabled=enabled if enabled is not None else False,
                message_template=message_template or default_template,
            )
            self._session.add(row)
        else:
            if channel_id is not None:
                row.channel_id = channel_id
            if enabled is not None:
                row.enabled = enabled
            if message_template is not None:
                row.message_template = message_template

        await self._session.flush()
        return row


class RaidProtectionRepository:
    """CRUD access for guild raid protection settings and mitigation state."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_config(self, guild_id: int) -> RaidProtectionConfig | None:
        statement = select(RaidProtectionConfig).where(RaidProtectionConfig.guild_id == guild_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_config(
        self,
        guild_id: int,
        *,
        enabled: bool | None = None,
        join_threshold: int | None = None,
        window_seconds: int | None = None,
        alert_channel_id: int | None = None,
        mitigation_action: str | None = None,
        mitigation_duration_seconds: int | None = None,
    ) -> RaidProtectionConfig:
        row = await self.get_config(guild_id)
        if row is None:
            row = RaidProtectionConfig(
                guild_id=guild_id,
                enabled=enabled if enabled is not None else False,
                join_threshold=join_threshold or 8,
                window_seconds=window_seconds or 30,
                alert_channel_id=alert_channel_id,
                mitigation_action=mitigation_action or "none",
                mitigation_duration_seconds=mitigation_duration_seconds or 900,
            )
            self._session.add(row)
        else:
            if enabled is not None:
                row.enabled = enabled
            if join_threshold is not None:
                row.join_threshold = join_threshold
            if window_seconds is not None:
                row.window_seconds = window_seconds
            if alert_channel_id is not None:
                row.alert_channel_id = alert_channel_id
            if mitigation_action is not None:
                row.mitigation_action = mitigation_action
            if mitigation_duration_seconds is not None:
                row.mitigation_duration_seconds = mitigation_duration_seconds

        await self._session.flush()
        return row

    async def mark_triggered(self, guild_id: int, triggered_at: datetime) -> RaidProtectionConfig:
        row = await self.upsert_config(guild_id)
        row.last_triggered_at = triggered_at
        await self._session.flush()
        return row

    async def mark_mitigation_started(
        self,
        guild_id: int,
        *,
        previous_verification_level: int | None,
        active_until: datetime,
    ) -> RaidProtectionConfig:
        row = await self.upsert_config(guild_id)
        row.mitigation_active_until = active_until
        row.previous_verification_level = previous_verification_level
        await self._session.flush()
        return row

    async def clear_mitigation(self, guild_id: int) -> RaidProtectionConfig | None:
        row = await self.get_config(guild_id)
        if row is None:
            return None

        row.mitigation_active_until = None
        row.previous_verification_level = None
        await self._session.flush()
        return row

    async def due_mitigation_releases(self, now: datetime) -> list[RaidProtectionConfig]:
        statement = (
            select(RaidProtectionConfig)
            .where(
                RaidProtectionConfig.mitigation_active_until.is_not(None),
                RaidProtectionConfig.mitigation_active_until <= now,
            )
            .order_by(RaidProtectionConfig.mitigation_active_until)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())


class MusicConfigRepository:
    """CRUD access for guild-level music defaults."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_config(self, guild_id: int) -> MusicConfig | None:
        statement = select(MusicConfig).where(MusicConfig.guild_id == guild_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert_config(
        self,
        guild_id: int,
        *,
        default_volume: int | None = None,
        autoplay: bool | None = None,
        max_queue_size: int | None = None,
    ) -> MusicConfig:
        row = await self.get_config(guild_id)
        if row is None:
            row = MusicConfig(
                guild_id=guild_id,
                default_volume=default_volume if default_volume is not None else 50,
                autoplay=autoplay if autoplay is not None else False,
                max_queue_size=max_queue_size if max_queue_size is not None else 100,
            )
            self._session.add(row)
        else:
            if default_volume is not None:
                row.default_volume = default_volume
            if autoplay is not None:
                row.autoplay = autoplay
            if max_queue_size is not None:
                row.max_queue_size = max_queue_size

        await self._session.flush()
        return row


class CommandAclRepository:
    """Manages role allow-list entries for slash command access control."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def allow_role(
        self,
        *,
        guild_id: int,
        command_name: str,
        role_id: int,
    ) -> CommandAclEntry:
        normalized = normalize_command_name(command_name)
        statement = select(CommandAclEntry).where(
            CommandAclEntry.guild_id == guild_id,
            CommandAclEntry.command_name == normalized,
            CommandAclEntry.role_id == role_id,
        )
        result = await self._session.execute(statement)
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing

        row = CommandAclEntry(
            guild_id=guild_id,
            command_name=normalized,
            role_id=role_id,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def revoke_role(
        self,
        *,
        guild_id: int,
        command_name: str,
        role_id: int,
    ) -> bool:
        normalized = normalize_command_name(command_name)
        statement = select(CommandAclEntry).where(
            CommandAclEntry.guild_id == guild_id,
            CommandAclEntry.command_name == normalized,
            CommandAclEntry.role_id == role_id,
        )
        result = await self._session.execute(statement)
        row = result.scalar_one_or_none()
        if row is None:
            return False

        await self._session.delete(row)
        await self._session.flush()
        return True

    async def list_rules(
        self,
        *,
        guild_id: int,
        command_name: str | None = None,
    ) -> list[CommandAclEntry]:
        statement = select(CommandAclEntry).where(CommandAclEntry.guild_id == guild_id)
        if command_name is not None:
            statement = statement.where(
                CommandAclEntry.command_name == normalize_command_name(command_name)
            )

        statement = statement.order_by(CommandAclEntry.command_name, CommandAclEntry.role_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def role_ids_for_command(self, guild_id: int, command_name: str) -> list[int]:
        statement = select(CommandAclEntry.role_id).where(
            CommandAclEntry.guild_id == guild_id,
            CommandAclEntry.command_name == normalize_command_name(command_name),
        )
        result = await self._session.execute(statement)
        return [int(role_id) for role_id in result.scalars().all()]
