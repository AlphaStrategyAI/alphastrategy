from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from alphastrategy.persist import append_text

_SENSITIVE_SUBSTRINGS = ("key", "secret", "token", "password")


def _is_sensitive_key(key: str) -> bool:
    lower = key.lower()
    return any(substr in lower for substr in _SENSITIVE_SUBSTRINGS)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if _is_sensitive_key(key) else _redact(nested)
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def append(path: Path | str, payload: dict) -> None:
    record = dict(payload)
    if "ts" not in record:
        record["ts"] = _utc_ts()
    record = _redact(record)
    line = json.dumps(record, separators=(",", ":")) + "\n"
    append_text(path, line)
