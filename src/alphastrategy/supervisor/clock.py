from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class ClockSnapshot:
    is_open: bool
    next_open: datetime
    next_close: datetime
    now: datetime


def next_rebalance_event(
    prev: ClockSnapshot | None,
    cur: ClockSnapshot,
    last_event: str | None,
) -> str | None:
    session_date = cur.next_close.date().isoformat()
    close_key = f"{session_date}:close"
    open_key = f"{session_date}:open"
    now = cur.now

    in_close_window = cur.is_open and (cur.next_close - now) <= timedelta(minutes=12)

    if prev is not None and prev.is_open == cur.is_open:
        if not in_close_window or last_event == close_key:
            return None
        return "close"

    if cur.is_open and (prev is None or not prev.is_open):
        open_time = prev.next_open if prev is not None else cur.next_open
        if now >= open_time + timedelta(minutes=3) and last_event != open_key:
            return "open"
        return None

    if in_close_window and last_event != close_key:
        return "close"

    return None
