from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import disnake
from disnake.ext import commands
from disnake.interactions.application_command import ApplicationCommandInteraction


@dataclass(slots=True)
class WarningRecord:
    moderator_id: int
    reason: str
    created_at: datetime


class ModerationCog(commands.Cog):
    """Moderation commands with explicit permission guards and clear feedback."""

    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot
        self._warning_log: dict[tuple[int, int], list[WarningRecord]] = defaultdict(list)

    @commands.slash_command(
        name="purge",
        description="Delete a batch of recent messages from this channel",
    )
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(
        self,
        interaction: ApplicationCommandInteraction,
        amount: int = commands.Param(gt=0, le=100),
    ) -> None:
        if interaction.channel is None or not isinstance(interaction.channel, disnake.TextChannel):
            await interaction.response.send_message(
                "Use this command in a text channel.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.edit_original_response(content=f"Deleted `{len(deleted)}` messages.")

    @commands.slash_command(name="kick", description="Kick a member from the server")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: ApplicationCommandInteraction,
        member: disnake.Member,
        reason: str = commands.Param(default="No reason provided", max_length=200),
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        me = interaction.guild.me
        if me is None or member.top_role >= me.top_role:
            await interaction.response.send_message(
                "I cannot kick this member because their role is higher or equal to mine.",
                ephemeral=True,
            )
            return

        await member.kick(reason=f"{interaction.author}: {reason}")
        await interaction.response.send_message(f"Kicked {member.mention}.", ephemeral=True)

    @commands.slash_command(name="ban", description="Ban a member from the server")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: ApplicationCommandInteraction,
        member: disnake.Member,
        reason: str = commands.Param(default="No reason provided", max_length=200),
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        me = interaction.guild.me
        if me is None or member.top_role >= me.top_role:
            await interaction.response.send_message(
                "I cannot ban this member because their role is higher or equal to mine.",
                ephemeral=True,
            )
            return

        await interaction.guild.ban(member, reason=f"{interaction.author}: {reason}")
        await interaction.response.send_message(f"Banned {member.mention}.", ephemeral=True)

    @commands.slash_command(name="tempban", description="Temporarily ban a member")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def tempban(
        self,
        interaction: ApplicationCommandInteraction,
        member: disnake.Member,
        duration_minutes: int = commands.Param(default=60, ge=1, le=10080),
        reason: str = commands.Param(default="No reason provided", max_length=200),
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        await interaction.guild.ban(member, reason=f"{interaction.author}: {reason}")
        unban_at = datetime.now(UTC) + timedelta(minutes=duration_minutes)

        await interaction.response.send_message(
            f"Temporarily banned {member.mention} until <t:{int(unban_at.timestamp())}:R>.",
            ephemeral=True,
        )

        async def _unban_later() -> None:
            await disnake.utils.sleep_until(unban_at)
            try:
                await interaction.guild.unban(
                    disnake.Object(id=member.id),
                    reason="Temporary ban expired",
                )
            except disnake.HTTPException:
                return

        self.bot.loop.create_task(_unban_later())

    @commands.slash_command(name="unban", description="Unban a user by their user ID")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(
        self,
        interaction: ApplicationCommandInteraction,
        user_id: int,
        reason: str = commands.Param(default="No reason provided", max_length=200),
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        user_obj = disnake.Object(id=user_id)
        try:
            await interaction.guild.unban(user_obj, reason=f"{interaction.author}: {reason}")
        except disnake.NotFound:
            await interaction.response.send_message(
                "That user is not currently banned.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(f"Unbanned user `{user_id}`.", ephemeral=True)

    @commands.slash_command(name="timeout", description="Timeout a member for moderation")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: ApplicationCommandInteraction,
        member: disnake.Member,
        duration_minutes: int = commands.Param(default=10, ge=1, le=40320),
        reason: str = commands.Param(default="No reason provided", max_length=200),
    ) -> None:
        until = datetime.now(UTC) + timedelta(minutes=duration_minutes)
        await member.timeout(until, reason=f"{interaction.author}: {reason}")
        await interaction.response.send_message(
            f"Timed out {member.mention} for `{duration_minutes}` minute(s).",
            ephemeral=True,
        )

    @commands.slash_command(name="untimeout", description="Remove timeout from a member")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def untimeout(
        self,
        interaction: ApplicationCommandInteraction,
        member: disnake.Member,
        reason: str = commands.Param(default="No reason provided", max_length=200),
    ) -> None:
        await member.timeout(None, reason=f"{interaction.author}: {reason}")
        await interaction.response.send_message(
            f"Removed timeout from {member.mention}.",
            ephemeral=True,
        )

    @commands.slash_command(name="warn", description="Issue a moderation warning to a member")
    @commands.has_permissions(moderate_members=True)
    async def warn(
        self,
        interaction: ApplicationCommandInteraction,
        member: disnake.Member,
        reason: str = commands.Param(default="No reason provided", max_length=300),
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        key = (interaction.guild_id, member.id)
        self._warning_log[key].append(
            WarningRecord(
                moderator_id=interaction.author.id,
                reason=reason,
                created_at=datetime.now(UTC),
            )
        )
        warning_count = len(self._warning_log[key])
        await interaction.response.send_message(
            f"Warned {member.mention}. Total warnings: `{warning_count}`.",
            ephemeral=True,
        )

    @commands.slash_command(name="warnings", description="View warning history for a member")
    @commands.has_permissions(moderate_members=True)
    async def warnings(
        self,
        interaction: ApplicationCommandInteraction,
        member: disnake.Member,
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        records = self._warning_log.get((interaction.guild_id, member.id), [])
        if not records:
            await interaction.response.send_message(
                f"No warnings recorded for {member.mention}.",
                ephemeral=True,
            )
            return

        lines = [
            (
                f"`#{index}` by <@{record.moderator_id}> "
                f"(<t:{int(record.created_at.timestamp())}:R>) - {record.reason}"
            )
            for index, record in enumerate(records[-10:], start=1)
        ]
        await interaction.response.send_message(
            "
".join(lines),
            ephemeral=True,
        )


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(ModerationCog(bot=bot))
