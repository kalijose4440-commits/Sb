from __future__ import annotations

from typing import Any, cast

from disnake.ext import commands
from disnake.interactions.application_command import ApplicationCommandInteraction

from bot.cogs.base_cog import BaseCog
from bot.db.repositories import AnalyticsRepository


class AnalyticsCog(BaseCog):
    """Captures and displays command analytics for premium insights."""

    @commands.Cog.listener("on_slash_command_completion")
    async def on_slash_command_completion(self, interaction: ApplicationCommandInteraction) -> None:
        command_name = "unknown"
        if interaction.application_command is not None:
            command_name = interaction.application_command.qualified_name

        async with self._session_factory() as session:
            repository = AnalyticsRepository(session)
            await repository.record_usage(
                guild_id=interaction.guild_id,
                channel_id=interaction.channel_id,
                user_id=interaction.author.id,
                command_name=command_name,
            )
            await session.commit()

    @commands.slash_command(name="analytics", description="View command usage analytics")
    async def analytics(self, interaction: ApplicationCommandInteraction) -> None:
        await self.send_subcommand_help(
            interaction,
            group_name="analytics",
            slash_examples=["analytics topcommands", "analytics topusers"],
            prefix_examples=["analytics topcommands", "analytics topusers"],
        )

    @analytics.sub_command(name="topcommands", description="Show most-used commands")
    @commands.has_permissions(manage_guild=True)
    async def top_commands(
        self,
        interaction: ApplicationCommandInteraction,
        limit: int = commands.Param(default=10, ge=1, le=25),
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        async with self._session_factory() as session:
            repository = AnalyticsRepository(session)
            rows = await repository.top_commands(interaction.guild_id, limit=limit)

        if not rows:
            await interaction.response.send_message("No analytics data yet.", ephemeral=True)
            return

        lines = [
            f"`{idx}.` `{name}` - **{uses}** uses" for idx, (name, uses) in enumerate(rows, start=1)
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @analytics.sub_command(name="topusers", description="Show top command users")
    @commands.has_permissions(manage_guild=True)
    async def top_users(
        self,
        interaction: ApplicationCommandInteraction,
        limit: int = commands.Param(default=10, ge=1, le=25),
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        async with self._session_factory() as session:
            repository = AnalyticsRepository(session)
            rows = await repository.top_users(interaction.guild_id, limit=limit)

        if not rows:
            await interaction.response.send_message("No analytics data yet.", ephemeral=True)
            return

        lines = [
            f"`{idx}.` <@{user_id}> - **{uses}** commands"
            for idx, (user_id, uses) in enumerate(rows, start=1)
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


def setup(bot: commands.InteractionBot) -> None:
    bridge = cast(Any, bot).bridge
    bot.add_cog(AnalyticsCog(bot=bot, session_factory=bridge.session_factory))
