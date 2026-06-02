from __future__ import annotations

import asyncio
import logging

import disnake
import uvicorn
from disnake.ext import commands
from sqlalchemy.ext.asyncio import AsyncEngine

from bot.api.app import create_api
from bot.bridge.state import BridgeState
from bot.core.config import Settings
from bot.core.lifecycle import run_services
from bot.core.logging import setup_logging
from bot.db.session import create_engine_and_sessionmaker, init_db


class DashboardBot(commands.InteractionBot):
    """Typed InteractionBot that carries app-wide shared dependencies."""

    bridge: BridgeState
    settings: Settings
    logger: logging.Logger


def create_bot(settings: Settings, bridge: BridgeState) -> DashboardBot:
    intents = disnake.Intents.default()
    intents.guilds = True
    intents.members = True

    bot = DashboardBot(intents=intents)
    bot.bridge = bridge
    bot.settings = settings
    bot.logger = logging.getLogger("bot.discord")

    @bot.event
    async def on_ready() -> None:
        bot.logger.info(
            "discord_bot_ready",
            extra={"bot_user": str(bot.user), "guild_count": len(bot.guilds)},
        )

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


if __name__ == "__main__":
    asyncio.run(main())
