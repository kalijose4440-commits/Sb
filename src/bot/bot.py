from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import disnake
import uvicorn
from disnake.ext import commands
from sqlalchemy.ext.asyncio import AsyncEngine

from bot.api.app import create_api
from bot.bridge.state import BridgeState
from bot.core.config import Settings
from bot.core.lifecycle import run_services
from bot.core.logging import setup_logging
from bot.core.response_style import install_interaction_response_style_patch
from bot.db.session import create_engine_and_sessionmaker, init_db


class DashboardBot(commands.Bot):
    """Typed bot that carries app-wide shared dependencies."""

    bridge: BridgeState
    settings: Settings
    logger: logging.Logger
    started_at: datetime


async def resolve_prefix(bot: DashboardBot, message: disnake.Message) -> str | list[str]:
    """Resolve per-guild command prefixes from runtime settings."""

    default_prefix = bot.settings.default_prefix
    if message.guild is None:
        return commands.when_mentioned_or(default_prefix)(bot, message)

    try:
        snapshot = await bot.bridge.get_or_load_settings(message.guild.id)
        configured_prefix = snapshot.prefix or default_prefix
    except Exception:
        bot.logger.exception(
            "prefix_resolution_failed",
            extra={"guild_id": message.guild.id, "fallback_prefix": default_prefix},
        )
        configured_prefix = default_prefix

    prefixes = [default_prefix]
    if configured_prefix not in prefixes:
        prefixes.append(configured_prefix)

    return commands.when_mentioned_or(*prefixes)(bot, message)


def create_bot(settings: Settings, bridge: BridgeState) -> DashboardBot:
    intents = disnake.Intents.default()
    intents.guilds = True
    intents.members = settings.enable_members_intent
    intents.moderation = True
    intents.messages = True
    intents.message_content = settings.enable_message_content_intent
    intents.reactions = True

    command_sync_flags = (
        commands.CommandSyncFlags.default()
        if settings.enable_slash_commands
        else commands.CommandSyncFlags.none()
    )
    bot = DashboardBot(
        command_prefix=resolve_prefix,
        intents=intents,
        help_command=None,
        command_sync_flags=command_sync_flags,
    )
    bot.bridge = bridge
    bot.settings = settings
    bot.logger = logging.getLogger("bot.discord")
    bot.started_at = datetime.now(UTC)

    @bot.event
    async def on_ready() -> None:
        if not bot.settings.enable_slash_commands:
            await _clear_remote_app_commands(bot)
        bot.logger.info(
            "discord_bot_ready",
            extra={"bot_user": str(bot.user), "guild_count": len(bot.guilds)},
        )

    @bot.event
    async def on_message(message: disnake.Message) -> None:
        if message.author.bot:
            return
        await bot.process_commands(message)

    @bot.event
    async def on_command(ctx: commands.Context) -> None:
        command_name = ctx.command.qualified_name if ctx.command is not None else "unknown"
        bot.logger.info(
            "prefix_command_received",
            extra={
                "command_name": command_name,
                "guild_id": ctx.guild.id if ctx.guild is not None else None,
                "channel_id": ctx.channel.id if ctx.channel is not None else None,
                "user_id": ctx.author.id if ctx.author is not None else None,
            },
        )

    @bot.event
    async def on_command_completion(ctx: commands.Context) -> None:
        command_name = ctx.command.qualified_name if ctx.command is not None else "unknown"
        bot.logger.info(
            "prefix_command_completed",
            extra={
                "command_name": command_name,
                "guild_id": ctx.guild.id if ctx.guild is not None else None,
                "channel_id": ctx.channel.id if ctx.channel is not None else None,
                "user_id": ctx.author.id if ctx.author is not None else None,
            },
        )

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
        command_name = ctx.command.qualified_name if ctx.command is not None else "unknown"
        bot.logger.exception(
            "prefix_command_error",
            extra={
                "command_name": command_name,
                "guild_id": ctx.guild.id if ctx.guild is not None else None,
                "channel_id": ctx.channel.id if ctx.channel is not None else None,
                "user_id": ctx.author.id if ctx.author is not None else None,
                "error_type": type(error).__name__,
            },
            exc_info=error,
        )

    return bot


async def _clear_remote_app_commands(bot: DashboardBot) -> None:
    """Clear slash/user/message commands when running in prefix-only mode."""

    for slash_cmd in list(bot.slash_commands):
        bot.remove_slash_command(slash_cmd.name)
    for user_cmd in list(bot.user_commands):
        bot.remove_user_command(user_cmd.name)
    for message_cmd in list(bot.message_commands):
        bot.remove_message_command(message_cmd.name)

    try:
        await bot.bulk_overwrite_global_commands([])
    except disnake.HTTPException:
        bot.logger.warning("failed_to_clear_global_app_commands")

    for guild in bot.guilds:
        try:
            await bot.bulk_overwrite_guild_commands(guild.id, [])
        except disnake.HTTPException:
            bot.logger.warning(
                "failed_to_clear_guild_app_commands",
                extra={"guild_id": guild.id},
            )


async def _load_extensions(bot: DashboardBot) -> None:
    for extension in bot.settings.cog_extensions:
        bot.load_extension(extension)
        bot.logger.info("loaded_extension", extra={"extension": extension})


async def _shutdown(bot: DashboardBot, engine: AsyncEngine) -> None:
    if not bot.is_closed():
        await bot.close()
    await engine.dispose()


async def main() -> None:
    settings = Settings()
    setup_logging(settings.log_level)
    install_interaction_response_style_patch()
    logger = logging.getLogger("bot")

    engine, session_factory = create_engine_and_sessionmaker(settings.database_url)
    await init_db(engine)

    bridge = BridgeState(
        session_factory=session_factory,
        default_prefix=settings.default_prefix,
        default_status=settings.default_status,
        default_language=settings.default_language,
    )
    bot = create_bot(settings=settings, bridge=bridge)
    await _load_extensions(bot)

    api = create_api(settings=settings, bridge=bridge, session_factory=session_factory)
    server = uvicorn.Server(
        uvicorn.Config(
            app=api,
            host=settings.api_host,
            port=settings.api_port,
            loop="asyncio",
            log_level=settings.log_level.lower(),
        )
    )

    logger.info("starting_services", extra={"api_port": settings.api_port})
    try:
        await run_services(server.serve(), bot.start(settings.discord_token))
    finally:
        logger.info("shutting_down_services")
        await _shutdown(bot, engine)


def run() -> None:
    """Console script entrypoint for local and cloud runners."""

    asyncio.run(main())


if __name__ == "__main__":
    run()
