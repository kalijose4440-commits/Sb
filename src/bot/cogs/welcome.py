from __future__ import annotations

from typing import Any, cast

import disnake
from disnake.ext import commands
from disnake.interactions.application_command import ApplicationCommandInteraction

from bot.cogs.base_cog import BaseCog
from bot.core.onboarding import render_welcome_message
from bot.db.repositories import WelcomeRepository


class WelcomeCog(BaseCog):
    """Guild onboarding commands and welcome join listener."""

    @commands.slash_command(name="welcome", description="Configure welcome onboarding messages")
    async def welcome(self, interaction: ApplicationCommandInteraction) -> None:
        await interaction.response.send_message(
            "Use a welcome subcommand such as `/welcome enable`.",
            ephemeral=True,
        )

    @welcome.sub_command(name="status", description="Show current welcome configuration")
    @commands.has_permissions(manage_guild=True)
    async def status(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        async with self._session_factory() as session:
            repository = WelcomeRepository(session)
            row = await repository.get_config(interaction.guild_id)

        if row is None:
            await interaction.response.send_message(
                "Welcome config not set. Use `/welcome setchannel` and `/welcome enable`.",
                ephemeral=True,
            )
            return

        channel = f"<#{row.channel_id}>" if row.channel_id is not None else "not set"
        await interaction.response.send_message(
            f"Welcome is **{'enabled' if row.enabled else 'disabled'}**\n"
            f"Channel: {channel}\n"
            f"Template: `{row.message_template}`",
            ephemeral=True,
        )

    @welcome.sub_command(name="setchannel", description="Set the channel used for welcome messages")
    @commands.has_permissions(manage_guild=True)
    async def set_channel(
        self,
        interaction: ApplicationCommandInteraction,
        channel: disnake.TextChannel,
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        async with self._session_factory() as session:
            repository = WelcomeRepository(session)
            row = await repository.upsert_config(interaction.guild_id, channel_id=channel.id)
            await session.commit()

        await interaction.response.send_message(
            f"Welcome channel set to {channel.mention}. Enabled: {row.enabled}",
            ephemeral=True,
        )

    @welcome.sub_command(name="message", description="Set the welcome message template")
    @commands.has_permissions(manage_guild=True)
    async def set_message(
        self,
        interaction: ApplicationCommandInteraction,
        template: str = commands.Param(min_length=1, max_length=1800),
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        async with self._session_factory() as session:
            repository = WelcomeRepository(session)
            await repository.upsert_config(interaction.guild_id, message_template=template)
            await session.commit()

        await interaction.response.send_message(
            "Welcome template updated. Available placeholders: `{mention}` `{user}` `{guild}`.",
            ephemeral=True,
        )

    @welcome.sub_command(name="enable", description="Enable welcome onboarding messages")
    @commands.has_permissions(manage_guild=True)
    async def enable(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        async with self._session_factory() as session:
            repository = WelcomeRepository(session)
            row = await repository.upsert_config(interaction.guild_id, enabled=True)
            await session.commit()

        if row.channel_id is None:
            await interaction.response.send_message(
                "Welcome enabled, but no channel is set. Run `/welcome setchannel`.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("Welcome messages enabled.", ephemeral=True)

    @welcome.sub_command(name="disable", description="Disable welcome onboarding messages")
    @commands.has_permissions(manage_guild=True)
    async def disable(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        async with self._session_factory() as session:
            repository = WelcomeRepository(session)
            await repository.upsert_config(interaction.guild_id, enabled=False)
            await session.commit()

        await interaction.response.send_message("Welcome messages disabled.", ephemeral=True)

    @welcome.sub_command(name="preview", description="Preview the rendered welcome message")
    @commands.has_permissions(manage_guild=True)
    async def preview(
        self,
        interaction: ApplicationCommandInteraction,
        member: disnake.Member | None = None,
    ) -> None:
        if interaction.guild is None or interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        target = member or interaction.author
        if not isinstance(target, disnake.Member):
            await interaction.response.send_message(
                "Could not resolve a guild member for preview.", ephemeral=True
            )
            return

        async with self._session_factory() as session:
            repository = WelcomeRepository(session)
            row = await repository.get_config(interaction.guild_id)

        template = row.message_template if row is not None else "Welcome {mention} to {guild}!"
        rendered = render_welcome_message(
            template,
            guild_name=interaction.guild.name,
            user_name=target.display_name,
            mention=target.mention,
        )
        await interaction.response.send_message(rendered, ephemeral=True)

    @commands.Cog.listener("on_member_join")
    async def on_member_join(self, member: disnake.Member) -> None:
        guild = member.guild
        async with self._session_factory() as session:
            repository = WelcomeRepository(session)
            row = await repository.get_config(guild.id)

        if row is None or not row.enabled or row.channel_id is None:
            return

        channel = guild.get_channel(row.channel_id)
        if not isinstance(channel, disnake.TextChannel):
            return

        message = render_welcome_message(
            row.message_template,
            guild_name=guild.name,
            user_name=member.display_name,
            mention=member.mention,
        )
        try:
            await channel.send(message)
        except disnake.HTTPException:
            return


def setup(bot: commands.InteractionBot) -> None:
    bridge = cast(Any, bot).bridge
    bot.add_cog(WelcomeCog(bot=bot, session_factory=bridge.session_factory))
