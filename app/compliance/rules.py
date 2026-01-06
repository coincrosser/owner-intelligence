from __future__ import annotations

from datetime import datetime, timedelta


def is_suppressed(suppression_map: dict[str, str], owner_id: str) -> bool:
    return owner_id in suppression_map


def should_allow_outreach(
    attempts: list[datetime],
    max_attempts: int,
    window_days: int,
) -> bool:
    window_start = datetime.utcnow() - timedelta(days=window_days)
    recent_attempts = [attempt for attempt in attempts if attempt >= window_start]
    return len(recent_attempts) < max_attempts
