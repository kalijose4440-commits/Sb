from __future__ import annotations

from typing import Any, cast

import disnake
from disnake.ext import commands
from disnake.interactions.application_command import ApplicationCommandInteraction

from bot.cogs.base_cog import BaseCog
from bot.db.repositories import AutoModRepository


class AutoModCog(BaseCog):
    """Keyword-based automod commands and message filtering listener."""

    @commands.slash_command(name="automod", description="Manage automod keyword rules")
    async def automod(self, interaction: ApplicationCommandInteraction) -> None:
        await interaction.response.send_message(
            "Use an automod subcommand such as `/automod add`.",
            ephemeral=True,
        )

    @automod.sub_command(name="add", description="Add or update an automod keyword")
    @commands.default_member_permissions(manage_guild=True)
    async def add_keyword(
        self,
        interaction: ApplicationCommandInteraction,
        keyword: str = commands.Param(min_length=1, max_length=120),
        action: str = commands.Param(choices=["delete", "warn"], default="delete"),
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        async with self._session_factory() as session:
            repository = AutoModRepository(session)
            row = await repository.add_keyword(interaction.guild_id, keyword.strip(), action)
            await session.commit()

        await interaction.response.send_message(
            f"Automod keyword saved: `{row.keyword}` -> `{row.action}` (id `{row.id}`).",
            ephemeral=True,
        )

    @automod.sub_command(name="remove", description="Remove an automod keyword")
    @commands.default_member_permissions(manage_guild=True)
    async def remove_keyword(
        self,
        interaction: ApplicationCommandInteraction,
        keyword: str = commands.Param(min_length=1, max_length=120),
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        async with self._session_factory() as session:
            repository = AutoModRepository(session)
            deleted = await repository.remove_keyword(interaction.guild_id, keyword.strip())
            await session.commit()

        if not deleted:
            await interaction.response.send_message("Keyword not found.", ephemeral=True)
            return

        await interaction.response.send_message(f"Removed automod keyword `{keyword}`.", ephemeral=True)

    @automod.sub_command(name="toggle", description="Enable or disable a keyword rule by ID")
    @commands.default_member_permissions(manage_guild=True)
    async def toggle_keyword(
        self,
        interaction: ApplicationCommandInteraction,
        keyword_id: int,
        enabled: bool,
    ) -> None:
        async with self._session_factory() as session:
            repository = AutoModRepository(session)
            row = await repository.set_keyword_enabled(keyword_id, enabled)
            await session.commit()

        if row is None:
            await interaction.response.send_message("Keyword rule not found.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Keyword `{row.keyword}` is now `{'enabled' if row.enabled else 'disabled'}`.",
            ephemeral=True,
        )

    @automod.sub_command(name="list", description="List automod keywords for this guild")
    @commands.default_member_permissions(manage_guild=True)
    async def list_keywords(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        async with self._session_factory() as session:
            repository = AutoModRepository(session)
            rows = await repository.list_keywords(interaction.guild_id)

        if not rows:
            await interaction.response.send_message("No automod keywords configured.", ephemeral=True)
            return

        lines = [
            f"`#{row.id}` `{row.keyword}` -> `{row.action}` ({'on' if row.enabled else 'off'})"
            for row in rows[:25]
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @commands.Cog.listener("on_message")
    async def on_message(self, message: disnake.Message) -> None:
        if message.guild is None or message.author.bot or not message.content:
            return

        async with self._session_factory() as session:
            repository = AutoModRepository(session)
            matches = await repository.find_matching_keywords(message.guild.id, message.content)

        if not matches:
            return

        rule = matches[0]
        if rule.action == "delete":
            try:
                await message.delete()
            except disnake.HTTPException:
                return

            await message.channel.send(
                f"{message.author.mention}, your message was removed by automod.",
                delete_after=8,
            )
            return

        await message.channel.send(
            f"{message.author.mention}, your message triggered blocked keyword `{rule.keyword}`.",
            delete_after=8,
        )


def setup(bot: commands.InteractionBot) -> None:
    bridge = cast(Any, bot).bridge
    bot.add_cog(AutoModCog(bot=bot, session_factory=bridge.session_factory))
