from __future__ import annotations

from typing import Any, cast

import disnake
from disnake.ext import commands
from disnake.interactions.application_command import ApplicationCommandInteraction
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.cogs.base_cog import BaseCog
from bot.db.repositories import CommandAclRepository, normalize_command_name


class AclDenied(commands.CheckFailure):
    """Raised when ACL denies a slash command execution."""

    def __init__(self, command_name: str) -> None:
        super().__init__(f"ACL denied for command: {command_name}")
        self.command_name = command_name


class AclCog(BaseCog):
    """Role-based slash-command allow-list management and enforcement."""

    def __init__(
        self,
        bot: commands.InteractionBot,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        super().__init__(bot=bot, session_factory=session_factory)
        self.bot.add_app_command_check(self._acl_check, slash_commands=True)

    def cog_unload(self) -> None:
        self.bot.remove_app_command_check(self._acl_check, slash_commands=True)

    @commands.slash_command(name="acl", description="Manage role-based command allow-list rules")
    async def acl(self, interaction: ApplicationCommandInteraction) -> None:
        await interaction.response.send_message(
            "Use an ACL subcommand such as `/acl allow`.",
            ephemeral=True,
        )

    @acl.sub_command(name="allow", description="Allow a role to use a slash command")
    @commands.default_member_permissions(manage_guild=True)
    async def allow(
        self,
        interaction: ApplicationCommandInteraction,
        command_name: str,
        role: disnake.Role,
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        if not command_name.strip() or len(command_name.strip()) > 120:
            await interaction.response.send_message(
                "Command name must be between 1 and 120 characters.",
                ephemeral=True,
            )
            return

        normalized = normalize_command_name(command_name)
        async with self._session_factory() as session:
            repository = CommandAclRepository(session)
            await repository.allow_role(
                guild_id=interaction.guild_id,
                command_name=normalized,
                role_id=role.id,
            )
            await session.commit()

        await interaction.response.send_message(
            f"Role {role.mention} may now use `{normalized}`.",
            ephemeral=True,
        )

    @acl.sub_command(name="revoke", description="Revoke a role's ACL allow-list entry")
    @commands.default_member_permissions(manage_guild=True)
    async def revoke(
        self,
        interaction: ApplicationCommandInteraction,
        command_name: str,
        role: disnake.Role,
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        if not command_name.strip() or len(command_name.strip()) > 120:
            await interaction.response.send_message(
                "Command name must be between 1 and 120 characters.",
                ephemeral=True,
            )
            return

        normalized = normalize_command_name(command_name)
        async with self._session_factory() as session:
            repository = CommandAclRepository(session)
            removed = await repository.revoke_role(
                guild_id=interaction.guild_id,
                command_name=normalized,
                role_id=role.id,
            )
            await session.commit()

        if not removed:
            await interaction.response.send_message(
                "No matching ACL rule found.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"Removed ACL allow-list entry for {role.mention} on `{normalized}`.",
            ephemeral=True,
        )

    @acl.sub_command(name="list", description="List ACL rules for this guild")
    @commands.default_member_permissions(manage_guild=True)
    async def list_rules(
        self,
        interaction: ApplicationCommandInteraction,
        command_name: str | None = None,
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        async with self._session_factory() as session:
            repository = CommandAclRepository(session)
            rows = await repository.list_rules(
                guild_id=interaction.guild_id,
                command_name=command_name,
            )

        if not rows:
            await interaction.response.send_message(
                "No ACL rules configured for this scope.",
                ephemeral=True,
            )
            return

        lines = [f"`{row.command_name}` -> <@&{row.role_id}>" for row in rows[:30]]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    async def _acl_check(self, interaction: ApplicationCommandInteraction) -> bool:
        if interaction.guild_id is None:
            return True

        command = interaction.application_command
        if command is None:
            return True

        command_name = normalize_command_name(command.qualified_name)
        if command_name == "acl" or command_name.startswith("acl "):
            return True

        member = interaction.author if isinstance(interaction.author, disnake.Member) else None
        if member is not None and (
            member.guild_permissions.administrator or member.guild_permissions.manage_guild
        ):
            return True

        async with self._session_factory() as session:
            repository = CommandAclRepository(session)
            role_ids = await repository.role_ids_for_command(interaction.guild_id, command_name)

        if not role_ids:
            return True

        if member is None:
            raise AclDenied(command_name)

        member_role_ids = {role.id for role in member.roles}
        if member_role_ids.intersection(role_ids):
            return True

        raise AclDenied(command_name)

    @commands.Cog.listener("on_slash_command_error")
    async def on_slash_command_error(
        self,
        interaction: ApplicationCommandInteraction,
        error: commands.CommandError,
    ) -> None:
        original = getattr(error, "original", error)
        if not isinstance(original, AclDenied):
            return

        message = (
            "You are not allowed to run this command. "
            f"Required ACL command target: `{original.command_name}`."
        )
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


def setup(bot: commands.InteractionBot) -> None:
    bridge = cast(Any, bot).bridge
    bot.add_cog(AclCog(bot=bot, session_factory=bridge.session_factory))
