"""Subprocess DSL worker: JSON stdin → JSON stdout."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from alphastrategy.dsl.eval import evaluate_dsl


def _set_memory_cap() -> None:
    try:
        import resource

        cap = 512 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    except (ImportError, OSError, ValueError):
        pass


def _bars_from_payload(bars_dict: dict) -> pd.DataFrame:
    dates = bars_dict["date"]
    cols = {k: v for k, v in bars_dict.items() if k != "date"}
    return pd.DataFrame(cols, index=pd.to_datetime(dates))


def main() -> None:
    _set_memory_cap()
    try:
        payload = json.load(sys.stdin)
        bundle_dir = Path(payload["bundle_dir"])
        effective_at = payload["effective_at"]
        bars = _bars_from_payload(payload["bars"])

        dsl = yaml.safe_load((bundle_dir / "strategy.dsl.yaml").read_bytes())
        params_raw = yaml.safe_load((bundle_dir / "parameters.yaml").read_bytes())
        params = params_raw if isinstance(params_raw, dict) else {}

        weights = evaluate_dsl(dsl, bars, effective_at, params)
        sys.stdout.write(json.dumps({"ok": True, "weights": weights}))
        sys.stdout.write("\n")
    except Exception as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": str(exc)}))
        sys.stdout.write("\n")
        sys.exit(2)


if __name__ == "__main__":
    main()
