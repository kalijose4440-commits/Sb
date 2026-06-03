from __future__ import annotations

import pytest
from disnake.ext import commands

from bot.core.error_hints import classify_command_error
from bot.core.prefix_adapter import PrefixResponseAdapter


class _FakeContext:
    def __init__(self) -> None:
        self.sent_payload: dict | None = None

    async def send(self, **kwargs):
        self.sent_payload = kwargs
        return kwargs

    async def trigger_typing(self) -> None:
        return None


@pytest.mark.asyncio
async def test_prefix_adapter_strips_ephemeral_kwarg() -> None:
    ctx = _FakeContext()
    adapter = PrefixResponseAdapter(ctx)  # type: ignore[arg-type]

    await adapter.send_message("hello", ephemeral=True)

    assert ctx.sent_payload is not None
    assert "ephemeral" not in ctx.sent_payload
    assert "embed" in ctx.sent_payload


def test_error_hints_return_localized_fix() -> None:
    hint = classify_command_error(
        commands.BadArgument("bad arg"),
        prefix="!",
        command_name="ban",
        language="en",
    )
    assert hint.title == "Invalid Argument"
    assert "expected format" in hint.reason or "expected format" in hint.possible_fix
    assert "!help ban" in hint.possible_fix
