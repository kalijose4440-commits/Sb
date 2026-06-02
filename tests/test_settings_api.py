from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from bot.api.app import create_api
from bot.bridge.state import BridgeState
from bot.core.config import Settings
from bot.db.session import create_engine_and_sessionmaker, init_db


@pytest.mark.asyncio
async def test_patch_settings_updates_prefix_and_status(tmp_path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'settings.db'}"
    engine, session_factory = create_engine_and_sessionmaker(database_url)
    await init_db(engine)

    settings = Settings(discord_token="test-token", database_url=database_url)
    bridge = BridgeState(session_factory=session_factory)
    app = create_api(settings=settings, bridge=bridge, session_factory=session_factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        patch_response = await client.patch(
            "/api/v1/settings/42",
            json={"prefix": "?", "status": "busy"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["prefix"] == "?"
        assert patch_response.json()["status"] == "busy"

        get_response = await client.get("/api/v1/settings/42")
        assert get_response.status_code == 200
        assert get_response.json()["prefix"] == "?"
        assert get_response.json()["status"] == "busy"

    await engine.dispose()
