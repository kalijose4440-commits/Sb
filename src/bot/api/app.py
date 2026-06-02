from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.api.routes.settings import router as settings_router
from bot.bridge.state import BridgeState
from bot.core.config import Settings


def create_api(
    *,
    settings: Settings,
    bridge: BridgeState,
    session_factory: async_sessionmaker[AsyncSession],
) -> FastAPI:
    """Create and configure the FastAPI dashboard backend."""

    app = FastAPI(title="Discord Bot Dashboard API", version="0.1.0")
    app.state.settings = settings
    app.state.bridge = bridge
    app.state.session_factory = session_factory

    @app.get("/healthz", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(settings_router)
    return app
