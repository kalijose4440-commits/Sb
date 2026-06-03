from __future__ import annotations

# mypy: ignore-errors
from typing import Any

import disnake
from disnake.ext import commands

from bot.core.error_hints import classify_command_error
from bot.core.prefix_adapter import PrefixInteractionAdapter
from bot.core.response_style import build_standard_embed


class PrefixBridgeCog(commands.Cog):
    """Prefix-command mirrors for slash command workflows."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _interaction(self, ctx: commands.Context) -> PrefixInteractionAdapter:
        return PrefixInteractionAdapter(ctx)

    def _require_cog(self, name: str) -> Any:
        cog = self.bot.get_cog(name)
        if cog is None:
            raise commands.CommandError(f"Required cog `{name}` is not loaded")
        return cog

    async def _resolved_prefix(self, ctx: commands.Context) -> str:
        default_prefix = "!"
        settings = getattr(self.bot, "settings", None)
        if settings is not None:
            default_prefix = getattr(settings, "default_prefix", default_prefix)

        if ctx.guild is None:
            return default_prefix

        bridge = getattr(self.bot, "bridge", None)
        if bridge is None:
            return default_prefix

        snapshot = await bridge.get_or_load_settings(ctx.guild.id)
        return snapshot.prefix or default_prefix

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context, *, category: str | None = None) -> None:
        prefix = await self._resolved_prefix(ctx)
        all_commands = sorted(self.bot.commands, key=lambda command: command.name)
        group_commands = [
            command
            for command in all_commands
            if isinstance(command, commands.Group) and not command.hidden
        ]
        regular_commands = [
            command
            for command in all_commands
            if not isinstance(command, commands.Group) and not command.hidden
        ]

        if category is None:
            embed = build_standard_embed(
                (
                    f"Current prefix: `{prefix}`\n"
                    f"Use `{prefix}help <category>` for detailed subcommand usage."
                ),
                title="Command Dashboard",
            )
            embed.add_field(
                name="Core Commands",
                value="\n".join(f"- `{prefix}{command.name}`" for command in regular_commands)
                or "- None",
                inline=False,
            )

            for group in group_commands:
                subs = sorted(
                    subcommand.name
                    for subcommand in group.commands
                    if not subcommand.hidden
                )
                examples = ", ".join(f"`{prefix}{group.name} {name}`" for name in subs[:2])
                value = (
                    f"Use `{prefix}{group.name} <subcommand>`\n"
                    f"Subcommands: {', '.join(subs) if subs else 'none'}"
                )
                if examples:
                    value += f"\nExamples: {examples}"
                embed.add_field(name=group.name.title(), value=value, inline=False)

            await ctx.send(embed=embed)
            return

        command = self.bot.get_command(category.lower())
        if command is None or command.hidden:
            category_names = ", ".join(group.name for group in group_commands)
            await ctx.send(
                embed=build_standard_embed(
                    (
                        f"Unknown category `{category}`.\n"
                        f"Available categories: {category_names}"
                    ),
                    title="Command Help",
                )
            )
            return

        if isinstance(command, commands.Group):
            sub_lines = [
                f"- `{prefix}{command.name} {subcommand.name}`"
                for subcommand in sorted(command.commands, key=lambda c: c.name)
                if not subcommand.hidden
            ]
            embed = build_standard_embed(
                f"Detailed subcommands for `{command.name}`.",
                title=f"{command.name.title()} Category",
            )
            embed.add_field(
                name="Subcommands",
                value="\n".join(sub_lines) or "- None",
                inline=False,
            )
            await ctx.send(embed=embed)
            return

        await ctx.send(
            embed=build_standard_embed(
                f"Usage: `{prefix}{command.qualified_name}`",
                title=f"{command.name.title()} Command",
            )
        )

    @commands.Cog.listener("on_command_error")
    async def handle_prefix_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
    ) -> None:
        if ctx.command is not None and ctx.command.cog is not self:
            return

        prefix = await self._resolved_prefix(ctx)
        command_name = ctx.command.qualified_name if ctx.command is not None else None
        hint = classify_command_error(error, prefix=prefix, command_name=command_name)
        embed = build_standard_embed(hint.reason, title=hint.title)
        embed.add_field(name="Possible fix", value=hint.possible_fix, inline=False)

        logger = getattr(self.bot, "logger", None)
        if logger is not None:
            log_payload = {
                "category": hint.title,
                "severity": hint.severity,
                "command_name": command_name or "unknown",
                "guild_id": ctx.guild.id if ctx.guild is not None else None,
                "channel_id": ctx.channel.id if ctx.channel is not None else None,
                "user_id": ctx.author.id if ctx.author is not None else None,
            }
            if hint.severity == "error":
                logger.exception("prefix_command_failed", extra=log_payload, exc_info=error)
            else:
                logger.warning("prefix_command_rejected", extra=log_payload)

        await ctx.send(embed=embed)


    @commands.command(name="settings")
    async def settings(self, ctx: commands.Context) -> None:
        cog = self._require_cog("AdminCog")
        await cog.settings(self._interaction(ctx))

    @commands.command(name="setprefix")
    @commands.has_permissions(manage_guild=True)
    async def setprefix(self, ctx: commands.Context, prefix: str) -> None:
        cog = self._require_cog("AdminCog")
        await cog.setprefix(self._interaction(ctx), prefix)

    @commands.command(name="setstatus")
    @commands.has_permissions(manage_guild=True)
    async def setstatus(self, ctx: commands.Context, *, status: str) -> None:
        cog = self._require_cog("AdminCog")
        await cog.setstatus(self._interaction(ctx), status)

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context) -> None:
        cog = self._require_cog("UtilityCog")
        await cog.ping(self._interaction(ctx))

    @commands.command(name="botinfo")
    async def botinfo(self, ctx: commands.Context) -> None:
        cog = self._require_cog("UtilityCog")
        await cog.botinfo(self._interaction(ctx))

    @commands.command(name="serverinfo")
    async def serverinfo(self, ctx: commands.Context) -> None:
        cog = self._require_cog("UtilityCog")
        await cog.serverinfo(self._interaction(ctx))

    @commands.command(name="userinfo")
    async def userinfo(
        self,
        ctx: commands.Context,
        member: disnake.Member | None = None,
    ) -> None:
        cog = self._require_cog("UtilityCog")
        await cog.userinfo(self._interaction(ctx), member)

    @commands.command(name="runtime")
    async def runtime(self, ctx: commands.Context) -> None:
        cog = self._require_cog("UtilityCog")
        await cog.runtime(self._interaction(ctx))

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx: commands.Context, amount: int) -> None:
        cog = self._require_cog("ModerationCog")
        await cog.purge(self._interaction(ctx), amount)

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: commands.Context,
        member: disnake.Member,
        *,
        reason: str = "No reason provided",
    ) -> None:
        cog = self._require_cog("ModerationCog")
        await cog.kick(self._interaction(ctx), member, reason)

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        member: disnake.Member,
        *,
        reason: str = "No reason provided",
    ) -> None:
        cog = self._require_cog("ModerationCog")
        await cog.ban(self._interaction(ctx), member, reason)

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban(
        self,
        ctx: commands.Context,
        user_id: int,
        *,
        reason: str = "No reason provided",
    ) -> None:
        cog = self._require_cog("ModerationCog")
        await cog.unban(self._interaction(ctx), user_id, reason)

    @commands.group(name="welcome", invoke_without_command=True)
    async def welcome_group(self, ctx: commands.Context) -> None:
        await ctx.send(embed=build_standard_embed("Use `welcome <subcommand>`."))

    @welcome_group.command(name="status")
    @commands.has_permissions(manage_guild=True)
    async def welcome_status(self, ctx: commands.Context) -> None:
        cog = self._require_cog("WelcomeCog")
        await cog.status(self._interaction(ctx))

    @welcome_group.command(name="setchannel")
    @commands.has_permissions(manage_guild=True)
    async def welcome_setchannel(self, ctx: commands.Context, channel: disnake.TextChannel) -> None:
        cog = self._require_cog("WelcomeCog")
        await cog.set_channel(self._interaction(ctx), channel)

    @welcome_group.command(name="message")
    @commands.has_permissions(manage_guild=True)
    async def welcome_message(self, ctx: commands.Context, *, template: str) -> None:
        cog = self._require_cog("WelcomeCog")
        await cog.set_message(self._interaction(ctx), template)

    @welcome_group.command(name="enable")
    @commands.has_permissions(manage_guild=True)
    async def welcome_enable(self, ctx: commands.Context) -> None:
        cog = self._require_cog("WelcomeCog")
        await cog.enable(self._interaction(ctx))

    @welcome_group.command(name="disable")
    @commands.has_permissions(manage_guild=True)
    async def welcome_disable(self, ctx: commands.Context) -> None:
        cog = self._require_cog("WelcomeCog")
        await cog.disable(self._interaction(ctx))

    @welcome_group.command(name="preview")
    @commands.has_permissions(manage_guild=True)
    async def welcome_preview(
        self,
        ctx: commands.Context,
        member: disnake.Member | None = None,
    ) -> None:
        cog = self._require_cog("WelcomeCog")
        await cog.preview(self._interaction(ctx), member)

    @commands.group(name="security", invoke_without_command=True)
    async def security_group(self, ctx: commands.Context) -> None:
        await ctx.send(embed=build_standard_embed("Use `security <subcommand>`."))

    @security_group.command(name="status")
    @commands.has_permissions(manage_guild=True)
    async def security_status(self, ctx: commands.Context) -> None:
        cog = self._require_cog("SecurityCog")
        await cog.status(self._interaction(ctx))

    @security_group.command(name="configure")
    @commands.has_permissions(manage_guild=True)
    async def security_configure(
        self,
        ctx: commands.Context,
        join_threshold: int = 8,
        window_seconds: int = 30,
        mitigation_action: str = "none",
        mitigation_duration_minutes: int = 15,
        alert_channel: disnake.TextChannel | None = None,
    ) -> None:
        cog = self._require_cog("SecurityCog")
        await cog.configure(
            self._interaction(ctx),
            join_threshold,
            window_seconds,
            alert_channel,
            mitigation_action,
            mitigation_duration_minutes,
        )

    @security_group.command(name="enable")
    @commands.has_permissions(manage_guild=True)
    async def security_enable(self, ctx: commands.Context) -> None:
        cog = self._require_cog("SecurityCog")
        await cog.enable(self._interaction(ctx))

    @security_group.command(name="disable")
    @commands.has_permissions(manage_guild=True)
    async def security_disable(self, ctx: commands.Context) -> None:
        cog = self._require_cog("SecurityCog")
        await cog.disable(self._interaction(ctx))

    @commands.group(name="acl", invoke_without_command=True)
    async def acl_group(self, ctx: commands.Context) -> None:
        await ctx.send(embed=build_standard_embed("Use `acl <subcommand>`."))

    @acl_group.command(name="allow")
    @commands.has_permissions(manage_guild=True)
    async def acl_allow(
        self,
        ctx: commands.Context,
        role: disnake.Role,
        *,
        command_name: str,
    ) -> None:
        cog = self._require_cog("AclCog")
        await cog.allow(self._interaction(ctx), command_name, role)

    @acl_group.command(name="revoke")
    @commands.has_permissions(manage_guild=True)
    async def acl_revoke(
        self,
        ctx: commands.Context,
        role: disnake.Role,
        *,
        command_name: str,
    ) -> None:
        cog = self._require_cog("AclCog")
        await cog.revoke(self._interaction(ctx), command_name, role)

    @acl_group.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def acl_list(
        self,
        ctx: commands.Context,
        *,
        command_name: str | None = None,
    ) -> None:
        cog = self._require_cog("AclCog")
        await cog.list_rules(self._interaction(ctx), command_name)

    @commands.group(name="ticket", invoke_without_command=True)
    async def ticket_group(self, ctx: commands.Context) -> None:
        await ctx.send(embed=build_standard_embed("Use `ticket <subcommand>`."))

    @ticket_group.command(name="open")
    async def ticket_open(self, ctx: commands.Context, *, subject: str) -> None:
        cog = self._require_cog("TicketCog")
        await cog.open_ticket(self._interaction(ctx), subject)

    @ticket_group.command(name="close")
    async def ticket_close(
        self,
        ctx: commands.Context,
        archive: bool = True,
        generate_transcript: bool = True,
    ) -> None:
        cog = self._require_cog("TicketCog")
        await cog.close_ticket(self._interaction(ctx), archive, generate_transcript)

    @ticket_group.command(name="escalate")
    @commands.has_permissions(manage_channels=True)
    async def ticket_escalate(
        self,
        ctx: commands.Context,
        priority: str = "high",
        notify_role: disnake.Role | None = None,
    ) -> None:
        cog = self._require_cog("TicketCog")
        await cog.escalate(self._interaction(ctx), priority, notify_role)

    @ticket_group.command(name="transcript")
    async def ticket_transcript(self, ctx: commands.Context) -> None:
        cog = self._require_cog("TicketCog")
        await cog.transcript(self._interaction(ctx))

    @ticket_group.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def ticket_add(self, ctx: commands.Context, member: disnake.Member) -> None:
        cog = self._require_cog("TicketCog")
        await cog.add_member(self._interaction(ctx), member)

    @ticket_group.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def ticket_remove(self, ctx: commands.Context, member: disnake.Member) -> None:
        cog = self._require_cog("TicketCog")
        await cog.remove_member(self._interaction(ctx), member)

    @ticket_group.command(name="list")
    @commands.has_permissions(manage_channels=True)
    async def ticket_list(self, ctx: commands.Context) -> None:
        cog = self._require_cog("TicketCog")
        await cog.list_tickets(self._interaction(ctx))

    @commands.group(name="automod", invoke_without_command=True)
    async def automod_group(self, ctx: commands.Context) -> None:
        await ctx.send(embed=build_standard_embed("Use `automod <subcommand>`."))

    @automod_group.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def automod_add(
        self,
        ctx: commands.Context,
        keyword: str,
        action: str = "delete",
    ) -> None:
        cog = self._require_cog("AutoModCog")
        await cog.add_keyword(self._interaction(ctx), keyword, action)

    @automod_group.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def automod_remove(self, ctx: commands.Context, keyword: str) -> None:
        cog = self._require_cog("AutoModCog")
        await cog.remove_keyword(self._interaction(ctx), keyword)

    @automod_group.command(name="toggle")
    @commands.has_permissions(manage_guild=True)
    async def automod_toggle(self, ctx: commands.Context, keyword_id: int, enabled: bool) -> None:
        cog = self._require_cog("AutoModCog")
        await cog.toggle_keyword(self._interaction(ctx), keyword_id, enabled)

    @automod_group.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def automod_list(self, ctx: commands.Context) -> None:
        cog = self._require_cog("AutoModCog")
        await cog.list_keywords(self._interaction(ctx))

    @commands.group(name="reactionrole", invoke_without_command=True)
    async def reactionrole_group(self, ctx: commands.Context) -> None:
        await ctx.send(embed=build_standard_embed("Use `reactionrole <subcommand>`."))

    @reactionrole_group.command(name="bind")
    @commands.has_permissions(manage_roles=True)
    async def reactionrole_bind(
        self,
        ctx: commands.Context,
        channel: disnake.TextChannel,
        message_id: int,
        emoji: str,
        role: disnake.Role,
    ) -> None:
        cog = self._require_cog("ReactionRoleCog")
        await cog.bind(self._interaction(ctx), channel, message_id, emoji, role)

    @reactionrole_group.command(name="unbind")
    @commands.has_permissions(manage_roles=True)
    async def reactionrole_unbind(self, ctx: commands.Context, message_id: int, emoji: str) -> None:
        cog = self._require_cog("ReactionRoleCog")
        await cog.unbind(self._interaction(ctx), message_id, emoji)

    @reactionrole_group.command(name="list")
    @commands.has_permissions(manage_roles=True)
    async def reactionrole_list(self, ctx: commands.Context) -> None:
        cog = self._require_cog("ReactionRoleCog")
        await cog.list_bindings(self._interaction(ctx))

    @commands.group(name="announce", invoke_without_command=True)
    async def announce_group(self, ctx: commands.Context) -> None:
        await ctx.send(embed=build_standard_embed("Use `announce <subcommand>`."))

    @announce_group.command(name="create")
    @commands.has_permissions(manage_guild=True)
    async def announce_create(
        self,
        ctx: commands.Context,
        channel: disnake.TextChannel,
        interval_minutes: int,
        *,
        content: str,
    ) -> None:
        cog = self._require_cog("AnnouncementCog")
        await cog.create(self._interaction(ctx), channel, interval_minutes, content)

    @announce_group.command(name="toggle")
    @commands.has_permissions(manage_guild=True)
    async def announce_toggle(
        self,
        ctx: commands.Context,
        announcement_id: int,
        enabled: bool,
    ) -> None:
        cog = self._require_cog("AnnouncementCog")
        await cog.toggle(self._interaction(ctx), announcement_id, enabled)

    @announce_group.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def announce_list(self, ctx: commands.Context) -> None:
        cog = self._require_cog("AnnouncementCog")
        await cog.list_announcements(self._interaction(ctx))

    @announce_group.command(name="runnow")
    @commands.has_permissions(manage_guild=True)
    async def announce_runnow(self, ctx: commands.Context, announcement_id: int) -> None:
        cog = self._require_cog("AnnouncementCog")
        await cog.run_now(self._interaction(ctx), announcement_id)

    @commands.group(name="analytics", invoke_without_command=True)
    async def analytics_group(self, ctx: commands.Context) -> None:
        await ctx.send(embed=build_standard_embed("Use `analytics <subcommand>`."))

    @analytics_group.command(name="topcommands")
    @commands.has_permissions(manage_guild=True)
    async def analytics_topcommands(self, ctx: commands.Context, limit: int = 10) -> None:
        cog = self._require_cog("AnalyticsCog")
        await cog.top_commands(self._interaction(ctx), limit)

    @analytics_group.command(name="topusers")
    @commands.has_permissions(manage_guild=True)
    async def analytics_topusers(self, ctx: commands.Context, limit: int = 10) -> None:
        cog = self._require_cog("AnalyticsCog")
        await cog.top_users(self._interaction(ctx), limit)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(PrefixBridgeCog(bot=bot))
