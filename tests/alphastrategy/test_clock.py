from __future__ import annotations

from datetime import datetime, timedelta

from alphastrategy.supervisor.clock import ClockSnapshot, next_rebalance_event


def _snap(
    is_open: bool,
    next_open: datetime,
    next_close: datetime,
    now: datetime,
) -> ClockSnapshot:
    return ClockSnapshot(
        is_open=is_open,
        next_open=next_open,
        next_close=next_close,
        now=now,
    )


def test_open_event_after_three_minutes():
    session_close = datetime(2024, 1, 31, 21, 0)
    open_time = datetime(2024, 1, 31, 14, 30)
    prev = _snap(False, open_time, session_close, open_time - timedelta(minutes=1))
    now = open_time + timedelta(minutes=3)
    cur = _snap(True, open_time, session_close, now)
    assert next_rebalance_event(prev, cur, None) == "open"


def test_open_event_uses_cur_next_open_when_prev_none():
    session_close = datetime(2024, 1, 31, 21, 0)
    open_time = datetime(2024, 1, 31, 14, 30)
    now = open_time + timedelta(minutes=3)
    cur = _snap(True, open_time, session_close, now)
    assert next_rebalance_event(None, cur, None) == "open"


def test_open_delayed_before_three_minutes_returns_none():
    session_close = datetime(2024, 1, 31, 21, 0)
    open_time = datetime(2024, 1, 31, 14, 30)
    prev = _snap(False, open_time, session_close, open_time - timedelta(minutes=1))
    now = open_time + timedelta(minutes=2)
    cur = _snap(True, open_time, session_close, now)
    assert next_rebalance_event(prev, cur, None) is None


def test_no_double_open_on_heartbeat():
    session_close = datetime(2024, 1, 31, 21, 0)
    open_time = datetime(2024, 1, 31, 14, 30)
    now = open_time + timedelta(minutes=10)
    prev = _snap(True, open_time, session_close, now - timedelta(minutes=1))
    cur = _snap(True, open_time, session_close, now)
    last_event = "2024-01-31:open"
    assert next_rebalance_event(prev, cur, last_event) is None


def test_close_event_inside_twelve_minutes():
    session_close = datetime(2024, 1, 31, 21, 0)
    open_time = datetime(2024, 1, 31, 14, 30)
    now = session_close - timedelta(minutes=12)
    prev = _snap(True, open_time, session_close, now - timedelta(minutes=1))
    cur = _snap(True, open_time, session_close, now)
    assert next_rebalance_event(prev, cur, None) == "close"


def test_close_not_fired_twice():
    session_close = datetime(2024, 1, 31, 21, 0)
    open_time = datetime(2024, 1, 31, 14, 30)
    now = session_close - timedelta(minutes=5)
    prev = _snap(True, open_time, session_close, now - timedelta(minutes=1))
    cur = _snap(True, open_time, session_close, now)
    last_event = "2024-01-31:close"
    assert next_rebalance_event(prev, cur, last_event) is None


def test_close_can_fire_after_open_same_session():
    session_close = datetime(2024, 1, 31, 21, 0)
    open_time = datetime(2024, 1, 31, 14, 30)
    now = session_close - timedelta(minutes=5)
    prev = _snap(True, open_time, session_close, now - timedelta(minutes=1))
    cur = _snap(True, open_time, session_close, now)
    last_event = "2024-01-31:open"
    assert next_rebalance_event(prev, cur, last_event) == "close"


def test_heartbeat_unchanged_is_open_outside_close_window_returns_none():
    session_close = datetime(2024, 1, 31, 21, 0)
    open_time = datetime(2024, 1, 31, 14, 30)
    now = session_close - timedelta(minutes=30)
    prev = _snap(True, open_time, session_close, now - timedelta(minutes=1))
    cur = _snap(True, open_time, session_close, now)
    assert next_rebalance_event(prev, cur, None) is None


def test_close_outside_twelve_minute_window_returns_none():
    session_close = datetime(2024, 1, 31, 21, 0)
    open_time = datetime(2024, 1, 31, 14, 30)
    now = session_close - timedelta(minutes=13)
    prev = _snap(True, open_time, session_close, now - timedelta(minutes=1))
    cur = _snap(True, open_time, session_close, now)
    assert next_rebalance_event(prev, cur, None) is None


def test_open_uses_prev_next_open_for_delay():
    session_close = datetime(2024, 1, 31, 21, 0)
    prev_open = datetime(2024, 1, 31, 14, 30)
    cur_open = datetime(2024, 2, 1, 14, 30)
    prev = _snap(False, prev_open, session_close, prev_open - timedelta(minutes=1))
    now = prev_open + timedelta(minutes=3)
    cur = _snap(True, cur_open, session_close, now)
    assert next_rebalance_event(prev, cur, None) == "open"
