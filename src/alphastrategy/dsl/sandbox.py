"""Subprocess sandbox around the DSL worker."""
from __future__ import annotations

import json
import os
import site
import subprocess
import sys
import tempfile
from pathlib import Path

from alphastrategy.errors import HaltRequested

_SRC_ROOT = Path(__file__).resolve().parents[2]


def _pythonpath() -> str:
    parts = [str(_SRC_ROOT)]
    for entry in site.getsitepackages():
        parts.append(entry)
    user_site = site.getusersitepackages()
    if user_site:
        parts.append(user_site)
    return os.pathsep.join(dict.fromkeys(parts))


def weights_match(got: dict[str, float], expected: dict[str, float]) -> bool:
    if set(got) != set(expected):
        return False
    for k, exp in expected.items():
        tol = max(1e-9, abs(exp) * 1e-6)
        if abs(got[k] - exp) > tol:
            return False
    return True


def run_sandbox(
    bundle_dir: Path,
    bars: dict,
    effective_at: str,
    timeout_s: float = 5.0,
) -> dict[str, float]:
    payload = json.dumps(
        {
            "bundle_dir": str(bundle_dir.resolve()),
            "effective_at": effective_at,
            "bars": bars,
        }
    )
    with tempfile.TemporaryDirectory() as tmp_home:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": _pythonpath(),
            "HOME": tmp_home,
            "LANG": "C",
        }
        try:
            result = subprocess.run(
                [sys.executable, "-m", "alphastrategy.dsl.worker"],
                cwd=str(bundle_dir),
                env=env,
                input=payload,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise HaltRequested(f"sandbox timeout after {timeout_s}s") from exc

    if result.returncode != 0:
        detail = _worker_error(result.stdout) or result.stderr.strip() or "non-zero exit"
        raise HaltRequested(f"sandbox worker failed: {detail}")

    try:
        out = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HaltRequested("sandbox worker returned invalid JSON") from exc

    if not out.get("ok"):
        raise HaltRequested(out.get("error", "sandbox worker reported failure"))

    weights = out.get("weights")
    if not isinstance(weights, dict):
        raise HaltRequested("sandbox worker missing weights")

    return {str(k): float(v) for k, v in weights.items()}


def _worker_error(stdout: str) -> str | None:
    try:
        out = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if isinstance(out, dict) and not out.get("ok"):
        return str(out.get("error", ""))
    return None
