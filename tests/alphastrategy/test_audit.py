from __future__ import annotations

import json
from pathlib import Path

import pytest

from alphastrategy.supervisor import audit


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_append_source_uses_append_text() -> None:
    from alphastrategy.supervisor import audit as audit_mod

    src = Path(audit_mod.__file__).read_text(encoding="utf-8")
    body = src.split("def append", 1)[1]
    assert "append_text" in body
    assert 'open("a"' not in body


def test_append_redacts_api_key(tmp_path: Path):
    path = tmp_path / "audit.jsonl"
    audit.append(path, {"event": "order", "api_key": "PK_SECRET", "symbol": "AAPL"})
    text = path.read_text(encoding="utf-8")
    assert "PK_SECRET" not in text
    record = _read_lines(path)[0]
    assert record["event"] == "order"
    assert record["symbol"] == "AAPL"
    assert record["api_key"] == "***"


def test_append_adds_ts_when_missing(tmp_path: Path):
    path = tmp_path / "audit.jsonl"
    audit.append(path, {"event": "import"})
    record = _read_lines(path)[0]
    assert "ts" in record
    assert record["ts"].endswith("Z") or "+00:00" in record["ts"]


def test_append_preserves_caller_ts(tmp_path: Path):
    path = tmp_path / "audit.jsonl"
    audit.append(path, {"event": "halt", "ts": "2024-01-31T14:30:00Z"})
    record = _read_lines(path)[0]
    assert record["ts"] == "2024-01-31T14:30:00Z"


def test_append_is_append_only(tmp_path: Path):
    path = tmp_path / "audit.jsonl"
    audit.append(path, {"event": "paper_start"})
    audit.append(path, {"event": "paper_stop"})
    lines = _read_lines(path)
    assert len(lines) == 2
    assert lines[0]["event"] == "paper_start"
    assert lines[1]["event"] == "paper_stop"


@pytest.mark.parametrize(
    "key",
    ["secret", "client_secret", "access_token", "password", "API_KEY"],
)
def test_append_redacts_sensitive_key_names(tmp_path: Path, key: str):
    path = tmp_path / "audit.jsonl"
    audit.append(path, {"event": "order", key: "SENSITIVE_VALUE"})
    text = path.read_text(encoding="utf-8")
    assert "SENSITIVE_VALUE" not in text
    record = _read_lines(path)[0]
    assert record[key] == "***"


def test_append_redacts_nested_dicts(tmp_path: Path):
    path = tmp_path / "audit.jsonl"
    audit.append(
        path,
        {
            "event": "order",
            "broker": {"api_key": "PK_SECRET", "account": "paper"},
        },
    )
    text = path.read_text(encoding="utf-8")
    assert "PK_SECRET" not in text
    record = _read_lines(path)[0]
    assert record["broker"]["api_key"] == "***"
    assert record["broker"]["account"] == "paper"
