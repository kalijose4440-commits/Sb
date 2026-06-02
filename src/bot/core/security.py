from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta


def update_join_window(
    join_times: deque[datetime],
    now: datetime,
    *,
    window_seconds: int,
) -> int:
    """Record a join event and prune stale timestamps from the tracking window."""

    join_times.append(now)
    cutoff = now - timedelta(seconds=window_seconds)
    while join_times and join_times[0] < cutoff:
        join_times.popleft()
    return len(join_times)


def should_emit_alert(
    *,
    join_count: int,
    threshold: int,
    last_alert_at: datetime | None,
    now: datetime,
    cooldown_seconds: int,
) -> bool:
    """Return true when a raid alert should be emitted."""

    if join_count < threshold:
        return False

    if last_alert_at is None:
        return True

    return (now - last_alert_at) >= timedelta(seconds=cooldown_seconds)


def utc_now() -> datetime:
    """Small helper for test-friendly UTC timestamps."""

    return datetime.now(UTC)
