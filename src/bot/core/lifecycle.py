from __future__ import annotations

import asyncio
from collections.abc import Awaitable


async def run_services(*services: Awaitable[None]) -> None:
    """Run all long-lived services together under structured concurrency."""

    async with asyncio.TaskGroup() as task_group:
        for service in services:
            task_group.create_task(service)
