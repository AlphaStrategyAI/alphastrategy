from __future__ import annotations

from datetime import datetime, timedelta, timezone

from alphastrategy.supervisor.heartbeat import INTERVAL_SEC, describe, pulse_from_age


def test_pulse_bands() -> None:
    assert pulse_from_age(None) == "missing"
    assert pulse_from_age(0) == "live"
    assert pulse_from_age(45) == "live"
    assert pulse_from_age(46) == "stale"
    assert pulse_from_age(90) == "stale"
    assert pulse_from_age(91) == "dead"


def test_describe_missing_and_live() -> None:
    missing = describe(None)
    assert missing["pulse"] == "missing"
    assert missing["at"] is None
    assert missing["age_seconds"] is None
    assert missing["interval_seconds"] == INTERVAL_SEC == 20
    now = datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc)
    at = (now - timedelta(seconds=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = describe(at, now=now)
    assert body["pulse"] == "live"
    assert body["age_seconds"] == 3
    assert body["at"] == at


def test_app_imports_interval_constant() -> None:
    from pathlib import Path

    text = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "alphastrategy"
        / "api"
        / "app.py"
    ).read_text(encoding="utf-8")
    assert "HEARTBEAT_INTERVAL_SEC = 20" not in text
    assert "INTERVAL_SEC as HEARTBEAT_INTERVAL_SEC" in text
