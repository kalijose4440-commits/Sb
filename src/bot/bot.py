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

    snapshot = await bot.bridge.get_or_load_settings(message.guild.id)
    prefix = snapshot.prefix or default_prefix
    return commands.when_mentioned_or(prefix)(bot, message)


def create_bot(settings: Settings, bridge: BridgeState) -> DashboardBot:
    intents = disnake.Intents.default()
    intents.guilds = True
    intents.members = settings.enable_members_intent
    intents.moderation = True
    intents.messages = True
    intents.message_content = settings.enable_message_content_intent
    intents.reactions = True

    bot = DashboardBot(
        command_prefix=resolve_prefix,
        intents=intents,
        help_command=None,
    )
    bot.bridge = bridge
    bot.settings = settings
    bot.logger = logging.getLogger("bot.discord")
    bot.started_at = datetime.now(UTC)

    @bot.event
    async def on_ready() -> None:
        bot.logger.info(
            "discord_bot_ready",
            extra={"bot_user": str(bot.user), "guild_count": len(bot.guilds)},
        )

    @bot.event
    async def on_message(message: disnake.Message) -> None:
        if message.author.bot:
            return
        await bot.process_commands(message)

    return bot


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
