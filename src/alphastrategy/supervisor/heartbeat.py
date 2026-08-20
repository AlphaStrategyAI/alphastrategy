from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

INTERVAL_SEC = 20
LIVE_MAX_SEC = 45
STALE_MAX_SEC = 90


def _parse_iso(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def pulse_from_age(age_seconds: float | None) -> str:
    if age_seconds is None:
        return "missing"
    if age_seconds <= LIVE_MAX_SEC:
        return "live"
    if age_seconds <= STALE_MAX_SEC:
        return "stale"
    return "dead"


def describe(at: str | None, *, now: datetime | None = None) -> dict[str, Any]:
    if not at:
        return {
            "at": None,
            "age_seconds": None,
            "pulse": "missing",
            "interval_seconds": INTERVAL_SEC,
        }
    then = _parse_iso(at)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)
    age = max(0.0, (current - then).total_seconds())
    return {
        "at": at,
        "age_seconds": int(age),
        "pulse": pulse_from_age(age),
        "interval_seconds": INTERVAL_SEC,
    }
