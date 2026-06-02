from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any, cast

import disnake
from disnake.ext import commands
from disnake.interactions.application_command import ApplicationCommandInteraction

from bot.cogs.base_cog import BaseCog
from bot.core.transcripts import build_text_transcript
from bot.db.repositories import TicketRepository


class TicketCog(BaseCog):
    """Ticket command workflows for premium support operations."""

    @commands.slash_command(name="ticket", description="Manage support tickets")
    async def ticket(self, interaction: ApplicationCommandInteraction) -> None:
        await interaction.response.send_message(
            "Use a ticket subcommand such as `/ticket open` or `/ticket close`.",
            ephemeral=True,
        )

    @ticket.sub_command(name="open", description="Open a support ticket")
    async def open_ticket(
        self,
        interaction: ApplicationCommandInteraction,
        subject: str = commands.Param(min_length=3, max_length=120),
    ) -> None:
        if interaction.guild is None or interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        async with self._session_factory() as session:
            repository = TicketRepository(session)
            existing = await repository.get_open_by_owner(
                guild_id=interaction.guild_id,
                owner_id=interaction.author.id,
            )
            if existing is not None:
                await interaction.response.send_message(
                    f"You already have an open ticket: <#{existing.channel_id}>",
                    ephemeral=True,
                )
                return

        guild = interaction.guild
        category = disnake.utils.get(guild.categories, name="Tickets")
        if category is None:
            category = await guild.create_category("Tickets", reason="Create ticket category")

        ticket_owner = interaction.author
        overwrites: dict[disnake.Role | disnake.Member, disnake.PermissionOverwrite] = {
            guild.default_role: disnake.PermissionOverwrite(view_channel=False),
            cast(disnake.Member, ticket_owner): disnake.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
            ),
        }
        if guild.me is not None:
            overwrites[guild.me] = disnake.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
            )

        safe_name = "".join(
            ch for ch in ticket_owner.display_name.lower() if ch.isalnum() or ch == "-"
        )
        channel = await guild.create_text_channel(
            name=f"ticket-{safe_name[:18] or ticket_owner.id}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket opened by {ticket_owner}",
        )

        async with self._session_factory() as session:
            repository = TicketRepository(session)
            await repository.create_ticket(
                guild_id=interaction.guild_id,
                channel_id=channel.id,
                owner_id=ticket_owner.id,
                subject=subject,
            )
            await session.commit()

        await channel.send(
            f"{ticket_owner.mention} thanks for opening a ticket.\n"
            f"**Subject:** {subject}\n"
            "A team member will assist you shortly.",
        )
        await interaction.response.send_message(
            f"Ticket created: {channel.mention}",
            ephemeral=True,
        )

    @ticket.sub_command(name="close", description="Close the current ticket channel")
    async def close_ticket(
        self,
        interaction: ApplicationCommandInteraction,
        archive: bool = commands.Param(default=True),
        generate_transcript: bool = commands.Param(default=True),
    ) -> None:
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "This command can only be used in a server ticket channel.",
                ephemeral=True,
            )
            return

        channel = cast(disnake.TextChannel, interaction.channel)

        async with self._session_factory() as session:
            repository = TicketRepository(session)
            row = await repository.get_by_channel_id(channel.id)
            if row is None or row.status != "open":
                await interaction.response.send_message(
                    "This channel is not an open ticket.",
                    ephemeral=True,
                )
                return

            is_owner = row.owner_id == interaction.author.id
            has_manage_channels = bool(
                isinstance(interaction.author, disnake.Member)
                and interaction.author.guild_permissions.manage_channels
            )
            if not is_owner and not has_manage_channels:
                await interaction.response.send_message(
                    "Only the ticket owner or staff can close this ticket.",
                    ephemeral=True,
                )
                return

        await interaction.response.defer(ephemeral=True)

        transcript_content: str | None = None
        if generate_transcript:
            transcript_content = await build_text_transcript(channel, limit=1000)

        async with self._session_factory() as session:
            repository = TicketRepository(session)
            closed = await repository.close_ticket(channel.id)
            if closed is None:
                await interaction.edit_original_response(content="Unable to close ticket.")
                return

            if transcript_content is not None:
                await repository.create_transcript(
                    ticket_id=closed.id,
                    guild_id=closed.guild_id,
                    channel_id=closed.channel_id,
                    generated_by_user_id=interaction.author.id,
                    content=transcript_content,
                )

            await session.commit()

        if transcript_content is not None:
            transcript_bytes = transcript_content.encode("utf-8")
            transcript_file = disnake.File(
                io.BytesIO(transcript_bytes),
                filename=f"ticket-{closed.id}-transcript.txt",
            )
            try:
                await channel.send("Ticket transcript snapshot:", file=transcript_file)
            except disnake.HTTPException:
                pass

        if archive:
            owner = interaction.guild.get_member(closed.owner_id)
            if owner is not None:
                await channel.set_permissions(owner, view_channel=False, send_messages=False)
            timestamp = int(datetime.now(UTC).timestamp())
            await channel.edit(name=f"closed-{timestamp}")

        await interaction.edit_original_response(content="Ticket closed.")

    @ticket.sub_command(name="escalate", description="Escalate a ticket to a higher priority")
    @commands.has_permissions(manage_channels=True)
    async def escalate(
        self,
        interaction: ApplicationCommandInteraction,
        priority: str = commands.Param(
            default="high",
            choices=["low", "normal", "high", "critical"],
        ),
        notify_role: disnake.Role | None = None,
    ) -> None:
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "Run this inside an open ticket channel.",
                ephemeral=True,
            )
            return

        channel = cast(disnake.TextChannel, interaction.channel)
        await interaction.response.defer(ephemeral=True)

        role_id = notify_role.id if notify_role is not None else None
        async with self._session_factory() as session:
            repository = TicketRepository(session)
            row = await repository.escalate_ticket(
                channel.id,
                priority=priority,
                escalated_role_id=role_id,
            )
            if row is None or row.status != "open":
                await interaction.edit_original_response(content="This is not an active ticket.")
                return
            await session.commit()

        mention = notify_role.mention if notify_role is not None else "Staff"
        try:
            await channel.send(
                f"{mention} ticket escalated to **{priority}** priority "
                f"by {interaction.author.mention}."
            )
        except disnake.HTTPException:
            pass

        await interaction.edit_original_response(
            content=f"Ticket escalated to `{priority}` priority.",
        )

    @ticket.sub_command(name="transcript", description="Generate and send a transcript snapshot")
    async def transcript(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "Run this in a ticket channel.",
                ephemeral=True,
            )
            return

        channel = cast(disnake.TextChannel, interaction.channel)

        async with self._session_factory() as session:
            repository = TicketRepository(session)
            ticket = await repository.get_by_channel_id(channel.id)
            if ticket is None:
                await interaction.response.send_message(
                    "This channel is not a tracked ticket.",
                    ephemeral=True,
                )
                return

            is_owner = ticket.owner_id == interaction.author.id
            has_manage_channels = bool(
                isinstance(interaction.author, disnake.Member)
                and interaction.author.guild_permissions.manage_channels
            )
            if not is_owner and not has_manage_channels:
                await interaction.response.send_message(
                    "Only the ticket owner or staff can export transcripts.",
                    ephemeral=True,
                )
                return

        await interaction.response.defer(ephemeral=True)

        transcript_content = await build_text_transcript(channel, limit=1000)
        async with self._session_factory() as session:
            repository = TicketRepository(session)
            await repository.create_transcript(
                ticket_id=ticket.id,
                guild_id=ticket.guild_id,
                channel_id=ticket.channel_id,
                generated_by_user_id=interaction.author.id,
                content=transcript_content,
            )
            await session.commit()

        transcript_file = disnake.File(
            io.BytesIO(transcript_content.encode("utf-8")),
            filename=f"ticket-{ticket.id}-transcript.txt",
        )
        await interaction.followup.send(
            content="Transcript generated.",
            file=transcript_file,
            ephemeral=True,
        )

    @ticket.sub_command(name="add", description="Grant ticket access to a member")
    @commands.has_permissions(manage_channels=True)
    async def add_member(
        self,
        interaction: ApplicationCommandInteraction,
        member: disnake.Member,
    ) -> None:
        if interaction.channel is None:
            await interaction.response.send_message(
                "Run this in a ticket channel.",
                ephemeral=True,
            )
            return

        async with self._session_factory() as session:
            repository = TicketRepository(session)
            row = await repository.get_by_channel_id(interaction.channel.id)

        if row is None:
            await interaction.response.send_message(
                "This channel is not a tracked ticket.",
                ephemeral=True,
            )
            return

        channel = cast(disnake.TextChannel, interaction.channel)
        await channel.set_permissions(member, view_channel=True, send_messages=True)
        await interaction.response.send_message(
            f"Added {member.mention} to this ticket.",
            ephemeral=True,
        )

    @ticket.sub_command(name="remove", description="Revoke ticket access from a member")
    @commands.has_permissions(manage_channels=True)
    async def remove_member(
        self,
        interaction: ApplicationCommandInteraction,
        member: disnake.Member,
    ) -> None:
        if interaction.channel is None:
            await interaction.response.send_message(
                "Run this in a ticket channel.",
                ephemeral=True,
            )
            return

        async with self._session_factory() as session:
            repository = TicketRepository(session)
            row = await repository.get_by_channel_id(interaction.channel.id)

        if row is None:
            await interaction.response.send_message(
                "This channel is not a tracked ticket.",
                ephemeral=True,
            )
            return

        channel = cast(disnake.TextChannel, interaction.channel)
        await channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(
            f"Removed {member.mention} from this ticket.",
            ephemeral=True,
        )

    @ticket.sub_command(name="list", description="List currently open tickets")
    @commands.has_permissions(manage_channels=True)
    async def list_tickets(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        async with self._session_factory() as session:
            repository = TicketRepository(session)
            rows = await repository.list_open_tickets(interaction.guild_id)

        if not rows:
            await interaction.response.send_message("No open tickets.", ephemeral=True)
            return

        lines = [
            f"`#{row.id}` <#{row.channel_id}> owner: <@{row.owner_id}> "
            f"priority: `{row.priority}` escalated: `{row.escalated}`"
            for row in rows[:20]
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


def setup(bot: commands.InteractionBot) -> None:
    bridge = cast(Any, bot).bridge
    bot.add_cog(TicketCog(bot=bot, session_factory=bridge.session_factory))
