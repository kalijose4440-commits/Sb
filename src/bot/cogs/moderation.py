from __future__ import annotations

import disnake
from disnake.ext import commands
from disnake.interactions.application_command import ApplicationCommandInteraction


class ModerationCog(commands.Cog):
    """Moderation commands with explicit permission guards and clear feedback."""

    def __init__(self, bot: commands.InteractionBot) -> None:
        self.bot = bot

    @commands.slash_command(
        name="purge",
        description="Delete a batch of recent messages from this channel",
    )
    @commands.default_member_permissions(manage_messages=True)
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
    @commands.default_member_permissions(kick_members=True)
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
    @commands.default_member_permissions(ban_members=True)
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

    @commands.slash_command(name="unban", description="Unban a user by their user ID")
    @commands.default_member_permissions(ban_members=True)
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


def setup(bot: commands.InteractionBot) -> None:
    bot.add_cog(ModerationCog(bot=bot))
