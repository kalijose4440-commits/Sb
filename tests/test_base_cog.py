from __future__ import annotations

from types import SimpleNamespace

import pytest

from bot.bridge.state import BridgeState
from bot.cogs.base_cog import BaseCog
from bot.db.session import create_engine_and_sessionmaker, init_db


@pytest.mark.asyncio
async def test_base_cog_persists_and_publishes_prefix(tmp_path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'base_cog.db'}"
    engine, session_factory = create_engine_and_sessionmaker(database_url)
    await init_db(engine)

    bridge = BridgeState(session_factory=session_factory)
    fake_bot = SimpleNamespace(bridge=bridge)

    cog = BaseCog(bot=fake_bot, session_factory=session_factory)

    queue = await bridge.register_listener()
    await cog.update_prefix(guild_id=1001, prefix="#")
    event = await queue.get()

    assert event.guild_id == 1001
    assert event.field == "prefix"
    assert event.value == "#"

    read_model = await cog.get_guild_settings(guild_id=1001)
    assert read_model.prefix == "#"

    await bridge.unregister_listener(queue)
    await engine.dispose()
