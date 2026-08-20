from __future__ import annotations

from datetime import datetime, timedelta

from alphastrategy.supervisor.clock import (
    ClockSnapshot,
    next_rebalance_event,
    rebalance_countdown,
)


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


def test_countdown_closed_market_is_open_plus_three_minutes():
    session_close = datetime(2024, 1, 31, 21, 0)
    open_time = datetime(2024, 1, 31, 14, 30)
    now = open_time - timedelta(minutes=30)
    cur = _snap(False, open_time, session_close, now)
    hint = rebalance_countdown(cur, None)
    assert hint.next_rebalance == "open"
    assert hint.at == open_time + timedelta(minutes=3)
    assert hint.seconds == int((hint.at - now).total_seconds())


def test_countdown_after_session_open_event_is_close_minus_twelve():
    session_close = datetime(2024, 1, 31, 21, 0)
    now = datetime(2024, 1, 31, 16, 0)
    cur = _snap(True, datetime(2024, 2, 1, 14, 30), session_close, now)
    hint = rebalance_countdown(cur, "2024-01-31:open")
    assert hint.next_rebalance == "close"
    assert hint.at == session_close - timedelta(minutes=12)
    assert hint.seconds == int((hint.at - now).total_seconds())


def test_countdown_inside_close_window_has_zero_seconds():
    session_close = datetime(2024, 1, 31, 21, 0)
    now = session_close - timedelta(minutes=5)
    cur = _snap(True, datetime(2024, 2, 1, 14, 30), session_close, now)
    hint = rebalance_countdown(cur, "2024-01-31:open")
    assert hint.next_rebalance == "close"
    assert hint.seconds == 0


def test_countdown_after_close_event_is_next_open_plus_three():
    session_close = datetime(2024, 1, 31, 21, 0)
    next_open = datetime(2024, 2, 1, 14, 30)
    now = datetime(2024, 1, 31, 20, 55)
    cur = _snap(True, next_open, session_close, now)
    hint = rebalance_countdown(cur, "2024-01-31:close")
    assert hint.next_rebalance == "open"
    assert hint.at == next_open + timedelta(minutes=3)


def test_countdown_open_pending_when_open_not_recorded_is_due_now():
    session_close = datetime(2024, 1, 31, 21, 0)
    now = datetime(2024, 1, 31, 16, 0)
    cur = _snap(True, datetime(2024, 2, 1, 14, 30), session_close, now)
    hint = rebalance_countdown(cur, None)
    assert hint.next_rebalance == "open"
    assert hint.at == now
    assert hint.seconds == 0
