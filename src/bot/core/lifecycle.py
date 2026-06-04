from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any


async def run_services(*services: Coroutine[Any, Any, None]) -> None:
    """Run all long-lived services together under structured concurrency."""

    async with asyncio.TaskGroup() as task_group:
        for service in services:
            task_group.create_task(service)
