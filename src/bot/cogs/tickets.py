from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import disnake
from disnake.ext import commands
from disnake.interactions.application_command import ApplicationCommandInteraction

from bot.cogs.base_cog import BaseCog
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
            f"Ticket created: {channel.mention}", ephemeral=True
        )

    @ticket.sub_command(name="close", description="Close the current ticket channel")
    async def close_ticket(
        self,
        interaction: ApplicationCommandInteraction,
        archive: bool = commands.Param(default=True),
    ) -> None:
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "This command can only be used in a server ticket channel.",
                ephemeral=True,
            )
            return

        async with self._session_factory() as session:
            repository = TicketRepository(session)
            row = await repository.get_by_channel_id(interaction.channel.id)
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

            closed = await repository.close_ticket(interaction.channel.id)
            await session.commit()

        if closed is None:
            await interaction.response.send_message("Unable to close ticket.", ephemeral=True)
            return

        channel = cast(disnake.TextChannel, interaction.channel)
        if archive:
            owner = interaction.guild.get_member(closed.owner_id)
            if owner is not None:
                await channel.set_permissions(owner, view_channel=False, send_messages=False)
            timestamp = int(datetime.now(UTC).timestamp())
            await channel.edit(name=f"closed-{timestamp}")

        await interaction.response.send_message("Ticket closed.", ephemeral=True)

    @ticket.sub_command(name="add", description="Grant ticket access to a member")
    @commands.default_member_permissions(manage_channels=True)
    async def add_member(
        self,
        interaction: ApplicationCommandInteraction,
        member: disnake.Member,
    ) -> None:
        if interaction.channel is None:
            await interaction.response.send_message("Run this in a ticket channel.", ephemeral=True)
            return

        async with self._session_factory() as session:
            repository = TicketRepository(session)
            row = await repository.get_by_channel_id(interaction.channel.id)

        if row is None:
            await interaction.response.send_message(
                "This channel is not a tracked ticket.", ephemeral=True
            )
            return

        channel = cast(disnake.TextChannel, interaction.channel)
        await channel.set_permissions(member, view_channel=True, send_messages=True)
        await interaction.response.send_message(
            f"Added {member.mention} to this ticket.", ephemeral=True
        )

    @ticket.sub_command(name="remove", description="Revoke ticket access from a member")
    @commands.default_member_permissions(manage_channels=True)
    async def remove_member(
        self,
        interaction: ApplicationCommandInteraction,
        member: disnake.Member,
    ) -> None:
        if interaction.channel is None:
            await interaction.response.send_message("Run this in a ticket channel.", ephemeral=True)
            return

        async with self._session_factory() as session:
            repository = TicketRepository(session)
            row = await repository.get_by_channel_id(interaction.channel.id)

        if row is None:
            await interaction.response.send_message(
                "This channel is not a tracked ticket.", ephemeral=True
            )
            return

        channel = cast(disnake.TextChannel, interaction.channel)
        await channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(
            f"Removed {member.mention} from this ticket.",
            ephemeral=True,
        )

    @ticket.sub_command(name="list", description="List currently open tickets")
    @commands.default_member_permissions(manage_channels=True)
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
            f"`#{row.id}` <#{row.channel_id}> owner: <@{row.owner_id}> subject: {row.subject}"
            for row in rows[:20]
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


def setup(bot: commands.InteractionBot) -> None:
    bridge = cast(Any, bot).bridge
    bot.add_cog(TicketCog(bot=bot, session_factory=bridge.session_factory))
