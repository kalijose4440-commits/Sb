from __future__ import annotations

from typing import Any, cast

import disnake
from disnake.ext import commands
from disnake.interactions.application_command import ApplicationCommandInteraction

from bot.cogs.base_cog import BaseCog
from bot.db.repositories import ReactionRoleRepository


class ReactionRoleCog(BaseCog):
    """Reaction role configuration and event handlers."""

    @commands.slash_command(name="reactionrole", description="Manage reaction role bindings")
    async def reactionrole(self, interaction: ApplicationCommandInteraction) -> None:
        await interaction.response.send_message(
            "Use a reaction role subcommand such as `/reactionrole bind`.",
            ephemeral=True,
        )

    @reactionrole.sub_command(name="bind", description="Bind an emoji reaction to a role")
    @commands.default_member_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def bind(
        self,
        interaction: ApplicationCommandInteraction,
        channel: disnake.TextChannel,
        message_id: int,
        emoji: str,
        role: disnake.Role,
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        try:
            message = await channel.fetch_message(message_id)
        except disnake.HTTPException:
            await interaction.response.send_message("Could not find that message.", ephemeral=True)
            return

        await message.add_reaction(emoji)

        async with self._session_factory() as session:
            repository = ReactionRoleRepository(session)
            row = await repository.upsert_binding(
                guild_id=interaction.guild_id,
                channel_id=channel.id,
                message_id=message_id,
                emoji=emoji,
                role_id=role.id,
            )
            await session.commit()

        await interaction.response.send_message(
            f"Reaction role set: `{row.emoji}` -> {role.mention}",
            ephemeral=True,
        )

    @reactionrole.sub_command(name="unbind", description="Remove a reaction role binding")
    @commands.default_member_permissions(manage_roles=True)
    async def unbind(
        self,
        interaction: ApplicationCommandInteraction,
        message_id: int,
        emoji: str,
    ) -> None:
        async with self._session_factory() as session:
            repository = ReactionRoleRepository(session)
            deleted = await repository.remove_binding(message_id, emoji)
            await session.commit()

        if not deleted:
            await interaction.response.send_message("Binding not found.", ephemeral=True)
            return

        await interaction.response.send_message("Reaction role binding removed.", ephemeral=True)

    @reactionrole.sub_command(name="list", description="List guild reaction role bindings")
    @commands.default_member_permissions(manage_roles=True)
    async def list_bindings(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        async with self._session_factory() as session:
            repository = ReactionRoleRepository(session)
            rows = await repository.list_bindings(interaction.guild_id)

        if not rows:
            await interaction.response.send_message(
                "No reaction role bindings configured.", ephemeral=True
            )
            return

        lines = [
            f"message `{row.message_id}` emoji `{row.emoji}` -> <@&{row.role_id}>"
            for row in rows[:25]
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @commands.Cog.listener("on_raw_reaction_add")
    async def on_raw_reaction_add(self, payload: disnake.RawReactionActionEvent) -> None:
        if payload.guild_id is None or self.bot.user is None or payload.user_id == self.bot.user.id:
            return

        emoji = str(payload.emoji)
        async with self._session_factory() as session:
            repository = ReactionRoleRepository(session)
            binding = await repository.get_binding_by_payload(payload.message_id, emoji)

        if binding is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        member = payload.member
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except disnake.HTTPException:
                return

        role = guild.get_role(binding.role_id)
        if role is None:
            return

        try:
            await member.add_roles(role, reason="Reaction role binding")
        except disnake.HTTPException:
            return

    @commands.Cog.listener("on_raw_reaction_remove")
    async def on_raw_reaction_remove(self, payload: disnake.RawReactionActionEvent) -> None:
        if payload.guild_id is None or self.bot.user is None or payload.user_id == self.bot.user.id:
            return

        emoji = str(payload.emoji)
        async with self._session_factory() as session:
            repository = ReactionRoleRepository(session)
            binding = await repository.get_binding_by_payload(payload.message_id, emoji)

        if binding is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except disnake.HTTPException:
                return

        role = guild.get_role(binding.role_id)
        if role is None:
            return

        try:
            await member.remove_roles(role, reason="Reaction role binding removed")
        except disnake.HTTPException:
            return


def setup(bot: commands.InteractionBot) -> None:
    bridge = cast(Any, bot).bridge
    bot.add_cog(ReactionRoleCog(bot=bot, session_factory=bridge.session_factory))
