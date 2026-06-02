from __future__ import annotations

import disnake
from disnake.ext import commands

from bot.cogs.base_cog import BaseCog


class AdminCog(BaseCog):
    """Configuration commands for guild administrators."""

    @commands.slash_command(name="settings", description="View or update guild bot settings")
    async def settings(self, interaction: disnake.ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        settings = await self.get_guild_settings(interaction.guild_id)
        await interaction.response.send_message(
            f"Current settings -> prefix: `{settings.prefix}` | status: `{settings.status}`",
            ephemeral=True,
        )

    @commands.slash_command(name="setprefix", description="Update command prefix for this guild")
    @commands.default_member_permissions(manage_guild=True)
    async def setprefix(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        prefix: str = commands.Param(min_length=1, max_length=16),
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        settings = await self.update_prefix(interaction.guild_id, prefix)
        await interaction.response.send_message(f"Updated prefix to `{settings.prefix}`.", ephemeral=True)

    @commands.slash_command(name="setstatus", description="Update status label for this guild")
    @commands.default_member_permissions(manage_guild=True)
    async def setstatus(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        status: str = commands.Param(min_length=1, max_length=64),
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        settings = await self.update_status(interaction.guild_id, status)
        await interaction.response.send_message(f"Updated status to `{settings.status}`.", ephemeral=True)


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(AdminCog(bot=bot, session_factory=bot.bridge.session_factory))
