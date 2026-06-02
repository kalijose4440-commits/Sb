from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from bot.api.app import create_api
from bot.bridge.state import BridgeState
from bot.core.config import Settings
from bot.db.session import create_engine_and_sessionmaker, init_db


@pytest.mark.asyncio
async def test_premium_api_routes_cover_core_workflows(tmp_path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'premium_api.db'}"
    engine, session_factory = create_engine_and_sessionmaker(database_url)
    await init_db(engine)

    settings = Settings(discord_token="test-token", database_url=database_url)
    bridge = BridgeState(session_factory=session_factory)
    app = create_api(settings=settings, bridge=bridge, session_factory=session_factory)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        add_keyword = await client.post(
            "/api/v1/premium/42/automod/keywords",
            json={"keyword": "leak", "action": "warn"},
        )
        assert add_keyword.status_code == 200
        assert add_keyword.json()["keyword"] == "leak"

        list_keywords = await client.get("/api/v1/premium/42/automod/keywords")
        assert list_keywords.status_code == 200
        assert len(list_keywords.json()) == 1

        add_announcement = await client.post(
            "/api/v1/premium/42/announcements",
            json={"channel_id": 9001, "content": "Status update", "interval_minutes": 15},
        )
        assert add_announcement.status_code == 200
        announcement_id = add_announcement.json()["id"]

        toggle = await client.patch(
            f"/api/v1/premium/42/announcements/{announcement_id}",
            json={"enabled": False},
        )
        assert toggle.status_code == 200
        assert toggle.json()["enabled"] is False

        upsert_reaction = await client.post(
            "/api/v1/premium/42/reaction-roles",
            json={"channel_id": 9, "message_id": 10, "emoji": "fire", "role_id": 11},
        )
        assert upsert_reaction.status_code == 200

        remove_reaction = await client.delete("/api/v1/premium/42/reaction-roles/10/fire")
        assert remove_reaction.status_code == 204

        get_welcome = await client.get("/api/v1/premium/42/welcome")
        assert get_welcome.status_code == 200
        assert get_welcome.json()["enabled"] is False

        patch_welcome = await client.patch(
            "/api/v1/premium/42/welcome",
            json={"channel_id": 1234, "enabled": True, "message_template": "Welcome {mention}"},
        )
        assert patch_welcome.status_code == 200
        assert patch_welcome.json()["enabled"] is True

        get_security = await client.get("/api/v1/premium/42/security")
        assert get_security.status_code == 200
        assert get_security.json()["join_threshold"] == 8

        patch_security = await client.patch(
            "/api/v1/premium/42/security",
            json={
                "enabled": True,
                "join_threshold": 6,
                "window_seconds": 25,
                "alert_channel_id": 1234,
            },
        )
        assert patch_security.status_code == 200
        assert patch_security.json()["enabled"] is True
        assert patch_security.json()["join_threshold"] == 6

    await engine.dispose()
