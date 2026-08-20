from __future__ import annotations

import json
import re
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from alphastrategy.bundle.import_bundle import import_asb
from alphastrategy.bundle.reject import payload
from alphastrategy.bundle.schema import load_risk_envelope
from alphastrategy.errors import ImportRejected
from alphastrategy.helptext import help_payload
from alphastrategy.home import AlphaStrategyHome
from alphastrategy.persist import replace_text
from alphastrategy.risk.labels import POLICY_LABELS
from alphastrategy.risk.policy import AccountPolicy, merge_limits
from alphastrategy.risk.utilization import from_supervisor
from alphastrategy.supervisor.heartbeat import describe
from alphastrategy.supervisor import audit
from alphastrategy.supervisor.clock import ClockSnapshot, rebalance_countdown
from alphastrategy.supervisor.loop import Supervisor
from alphastrategy.supervisor.state import SupervisorState


def _parse_iso(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def _countdown_payload(clock: dict[str, Any], last_event: str | None) -> dict[str, Any] | None:
    if not isinstance(clock, dict) or clock.get("error") is not None:
        return None
    try:
        now_raw = clock.get("timestamp") or clock.get("now")
        cur = ClockSnapshot(
            is_open=bool(clock.get("is_open", False)),
            next_open=_parse_iso(clock["next_open"]),
            next_close=_parse_iso(clock["next_close"]),
            now=_parse_iso(now_raw),
        )
    except (KeyError, TypeError, ValueError):
        return None
    hint = rebalance_countdown(cur, last_event)
    return {
        "next_rebalance": hint.next_rebalance,
        "at": hint.at.isoformat(),
        "seconds": hint.seconds,
    }


def _enrich_positions(
    positions: list[dict[str, Any]],
    equity: float,
    prices: dict[str, float],
    last_combined: dict[str, float] | None = None,
    last_fill_got: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    combined = last_combined or {}
    filled = last_fill_got or {}
    out: list[dict[str, Any]] = []
    for pos in positions:
        item = dict(pos)
        symbol = str(item.get("symbol", ""))
        qty = float(item.get("qty", 0) or 0)
        price = prices.get(symbol)
        if price is not None:
            notional = qty * price
            item["notional"] = notional
            item["weight"] = (notional / equity) if equity else 0.0
        if symbol in combined:
            item["wanted"] = combined[symbol]
        if symbol in filled:
            item["fill"] = float(filled[symbol])
        out.append(item)
    seen = {str(item.get("symbol", "")) for item in out}
    for symbol, weight in sorted(combined.items()):
        if symbol in seen:
            continue
        wanted = float(weight)
        if abs(wanted) <= 0:
            continue
        row: dict[str, Any] = {
            "symbol": symbol,
            "qty": 0.0,
            "notional": 0.0,
            "weight": 0.0,
            "wanted": wanted,
        }
        if symbol in filled:
            row["fill"] = float(filled[symbol])
        out.append(row)
    return out


def _json_response(handler: Any, status: int, payload: Any) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _error(handler: Any, status: int, message: str) -> None:
    _json_response(handler, status, {"error": message})


def _read_json_body(handler: Any) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b""
    if not raw:
        return {}
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expected JSON object")
    return payload


def _load_runtime(home: AlphaStrategyHome) -> dict[str, Any]:
    path = home.runtime_path()
    if not path.exists():
        return {}
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {}


def _save_runtime(home: AlphaStrategyHome, runtime: dict[str, Any]) -> None:
    path = home.runtime_path()
    replace_text(path, yaml.safe_dump(runtime, sort_keys=True), prefix=".runtime.")


def _apply_startup_runtime(home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    runtime = _load_runtime(home)
    overlay = runtime.get("account_overlay")
    if isinstance(overlay, dict) and overlay:
        supervisor.set_policy(overlay)


def _policy_to_dict(policy: AccountPolicy) -> dict[str, Any]:
    return asdict(policy)


def _list_imported_bundles(home: AlphaStrategyHome) -> list[str]:
    imported_dir = home.imported_dir()
    if not imported_dir.is_dir():
        return []
    return sorted(
        entry.name
        for entry in imported_dir.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    )


def _imported_at_map(home: AlphaStrategyHome) -> dict[str, str]:
    out: dict[str, str] = {}
    for bundle_id in _list_imported_bundles(home):
        meta_path = home.bundle_dir(bundle_id) / "import-meta.json"
        if not meta_path.is_file():
            continue
        try:
            doc = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(doc, dict) and doc.get("imported_at"):
            out[bundle_id] = str(doc["imported_at"])
    return out


def _bundle_envelope(home: AlphaStrategyHome, bundle_id: str) -> dict[str, Any]:
    envelope_path = home.bundle_dir(bundle_id) / "risk-envelope.yaml"
    if not envelope_path.is_file():
        return {}
    return load_risk_envelope(envelope_path.read_bytes())


def _read_audit_events(home: AlphaStrategyHome, limit: int = 50) -> list[dict[str, Any]]:
    path = home.audit_path()
    if not path.is_file():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines[-limit:]]


def parse_multipart_file(content_type: str, body: bytes) -> tuple[str, bytes]:
    if "multipart/form-data" not in content_type:
        raise ValueError("expected multipart file upload")
    match = re.search(r"boundary=([^;]+)", content_type, flags=re.IGNORECASE)
    if not match:
        raise ValueError("missing multipart boundary")
    boundary = match.group(1).strip().strip('"')
    delim = b"--" + boundary.encode("ascii", errors="replace")
    preferred: tuple[str, bytes] | None = None
    fallback: tuple[str, bytes] | None = None
    for raw in body.split(delim):
        if not raw or raw in (b"--", b"--\r\n", b"--\n"):
            continue
        if raw.startswith(b"--"):
            continue
        if raw.startswith(b"\r\n"):
            raw = raw[2:]
        elif raw.startswith(b"\n"):
            raw = raw[1:]
        header_end = raw.find(b"\r\n\r\n")
        sep_len = 4
        if header_end < 0:
            header_end = raw.find(b"\n\n")
            sep_len = 2
        if header_end < 0:
            continue
        header_text = raw[:header_end].decode("utf-8", errors="replace")
        data = raw[header_end + sep_len :]
        if data.endswith(b"\r\n"):
            data = data[:-2]
        elif data.endswith(b"\n"):
            data = data[:-1]
        disposition = ""
        for line in header_text.splitlines():
            if line.lower().startswith("content-disposition:"):
                disposition = line
                break
        name_match = re.search(r'name="([^"]*)"', disposition)
        file_match = re.search(r'filename="([^"]*)"', disposition)
        if file_match is None:
            continue
        filename = file_match.group(1) or "upload.asb"
        candidate = (filename, data)
        if name_match and name_match.group(1) == "file":
            preferred = candidate
        elif fallback is None:
            fallback = candidate
    chosen = preferred or fallback
    if chosen is None:
        raise ValueError("missing upload file")
    return chosen


def _extract_upload(handler: Any) -> tuple[str, bytes]:
    content_type = handler.headers.get("Content-Type", "")
    length = int(handler.headers.get("Content-Length", "0"))
    body = handler.rfile.read(length) if length else b""
    return parse_multipart_file(content_type, body)


def handle_get_help(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    del home, supervisor
    _json_response(handler, 200, help_payload())


def handle_get_status(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    snapshot = supervisor.snapshot
    try:
        clock = supervisor.broker.get_clock()
    except Exception as exc:
        clock = {"error": str(exc)}
    halted = snapshot.state == SupervisorState.HALTED
    _json_response(
        handler,
        200,
        {
            "state": snapshot.state.value,
            "clock": clock,
            "halted": halted,
            "halt_reason": snapshot.halt_reason,
            "last_rebalance_event": snapshot.last_rebalance_event,
            "last_rebalance_complete": bool(snapshot.last_rebalance_complete),
            "countdown": _countdown_payload(clock, snapshot.last_rebalance_event),
            "flattened": snapshot.state
            in (SupervisorState.FLATTENING, SupervisorState.STOPPED),
            "last_kill": snapshot.last_kill,
            "utilization": from_supervisor(supervisor, live=True),
            "heartbeat": describe(snapshot.last_heartbeat_at),
        },
    )


def handle_get_portfolio(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    account, raw_positions = supervisor.live_book()
    equity = float(account.get("equity", 0))
    cash = float(account.get("cash", equity))
    snapshot = supervisor.snapshot
    positions = _enrich_positions(
        raw_positions,
        equity,
        snapshot.last_prices,
        snapshot.last_combined,
        snapshot.last_fill_got,
    )
    payload: dict[str, Any] = {
        "equity": equity,
        "cash": cash,
        "pnl": float(account.get("pnl", account.get("day_pnl", 0)) or 0),
        "positions": positions,
        "sleeves": dict(snapshot.sleeves),
        "last_combined": dict(snapshot.last_combined),
        "sleeve_contribution": {
            bundle_id: dict(weights)
            for bundle_id, weights in snapshot.last_sleeve_contribution.items()
        },
        "last_rebalance_event": snapshot.last_rebalance_event,
    }
    if snapshot.halt_reason:
        payload["halt_reason"] = snapshot.halt_reason
    _json_response(handler, 200, payload)


def handle_get_bundles(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    snapshot = supervisor.snapshot
    paper = {
        bundle_id: allocation
        for bundle_id, allocation in snapshot.sleeves.items()
        if allocation > 0
    }
    _json_response(
        handler,
        200,
        {
            "imported": _list_imported_bundles(home),
            "imported_at": _imported_at_map(home),
            "paper": paper,
            "stopped": list(snapshot.stopped),
        },
    )


def handle_post_import(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    del supervisor
    try:
        filename, data = _extract_upload(handler)
    except (ValueError, json.JSONDecodeError) as exc:
        _error(handler, 400, str(exc))
        return
    suffix = Path(filename).suffix or ".asb"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        bundle_id = import_asb(tmp_path, home)
        audit.append(home.audit_path(), {"event": "import", "bundle_id": bundle_id})
        _json_response(handler, 200, {"bundle_id": bundle_id})
    except ImportRejected as exc:
        _json_response(handler, 400, payload(exc))
    except Exception as exc:
        _json_response(handler, 400, payload(exc))
    finally:
        tmp_path.unlink(missing_ok=True)


def handle_post_paper_start(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    del home
    try:
        body = _read_json_body(handler)
        bundle_id = str(body.get("bundle_id", ""))
        allocation = float(body.get("allocation", 0))
        if not bundle_id:
            _error(handler, 400, "bundle_id required")
            return
        held = supervisor.start_sleeve(bundle_id, allocation)
        flattened = supervisor.state in (
            SupervisorState.FLATTENING,
            SupervisorState.STOPPED,
        )
        _json_response(
            handler, 200, {"ok": True, "held": held, "flattened": flattened}
        )
    except ValueError as exc:
        _error(handler, 409, str(exc))
    except (json.JSONDecodeError, TypeError) as exc:
        _error(handler, 400, str(exc))


def handle_post_paper_stop(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    del home
    try:
        body = _read_json_body(handler)
        bundle_id = str(body.get("bundle_id", ""))
        if not bundle_id:
            _error(handler, 400, "bundle_id required")
            return
        supervisor.stop_sleeve(bundle_id)
        _json_response(handler, 200, {"ok": True})
    except (json.JSONDecodeError, TypeError) as exc:
        _error(handler, 400, str(exc))


def handle_post_paper_kill(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    del home
    try:
        body = _read_json_body(handler)
        bundle_id = body.get("bundle_id")
        if bundle_id:
            outcome = supervisor.kill_sleeve(str(bundle_id))
        else:
            outcome = supervisor.kill_account()
        _json_response(handler, 200, {"ok": True, **outcome.to_dict()})
    except (json.JSONDecodeError, TypeError) as exc:
        _error(handler, 400, str(exc))


def handle_post_paper_resume(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    del home
    supervisor.resume()
    _json_response(handler, 200, {"ok": True})


def handle_get_activity(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    del supervisor
    _json_response(handler, 200, _read_audit_events(home))


def handle_get_risk(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    imported = _list_imported_bundles(home)
    sleeves = {
        bundle_id: _policy_to_dict(policy)
        for bundle_id, policy in supervisor.sleeve_policies(imported).items()
    }
    _json_response(
        handler,
        200,
        {
            "account": _policy_to_dict(supervisor.policy),
            "spoken": _policy_to_dict(supervisor.spoken_policy()),
            "defaults": _policy_to_dict(AccountPolicy.defaults()),
            "sleeves": sleeves,
            "utilization": from_supervisor(supervisor, live=True),
            "labels": dict(POLICY_LABELS),
        },
    )


def handle_put_risk(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    try:
        body = _read_json_body(handler)
        runtime = _load_runtime(home)
        account_overlay = runtime.get("account_overlay", {})
        if not isinstance(account_overlay, dict):
            account_overlay = {}
        sleeve_overlays = runtime.get("sleeve_overlays", {})
        if not isinstance(sleeve_overlays, dict):
            sleeve_overlays = {}

        account_patch = body.get("account")
        if account_patch is not None and not isinstance(account_patch, dict):
            raise ValueError("account must be an object")

        sleeves_patch = body.get("sleeves")
        if sleeves_patch is not None and not isinstance(sleeves_patch, dict):
            raise ValueError("sleeves must be an object")

        planned_account_overlay = dict(account_overlay)
        planned_sleeve_overlays = {
            bundle_id: dict(overlay)
            for bundle_id, overlay in sleeve_overlays.items()
            if isinstance(overlay, dict)
        }

        projected_policy = supervisor.policy
        if account_patch is not None:
            projected_policy = merge_limits({}, supervisor.policy, account_patch)
            planned_account_overlay.update(account_patch)

        if sleeves_patch is not None:
            for bundle_id, patch in sleeves_patch.items():
                if not isinstance(patch, dict):
                    raise ValueError(f"sleeve overlay for {bundle_id} must be an object")
                envelope = _bundle_envelope(home, bundle_id)
                stored = planned_sleeve_overlays.get(bundle_id, {})
                current_effective = merge_limits(envelope, projected_policy, stored)
                merge_limits({}, current_effective, patch)
                stored.update(patch)
                planned_sleeve_overlays[bundle_id] = stored

        if account_patch is not None:
            supervisor.set_policy(account_patch)
            runtime["account_overlay"] = planned_account_overlay

        if sleeves_patch is not None:
            runtime["sleeve_overlays"] = planned_sleeve_overlays

        if account_patch is not None or sleeves_patch is not None:
            _save_runtime(home, runtime)
            if sleeves_patch is not None:
                supervisor.enforce_live_book()

        flattened = supervisor.state in (
            SupervisorState.FLATTENING,
            SupervisorState.STOPPED,
        )
        _json_response(handler, 200, {"ok": True, "flattened": flattened})
    except ImportRejected as exc:
        _error(handler, 400, str(exc))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        _error(handler, 400, str(exc))


def dispatch(
    handler: Any,
    home: AlphaStrategyHome,
    supervisor: Supervisor,
    method: str,
    path: str,
) -> None:
    supervisor.reload_from_disk()
    routes = {
        ("GET", "/api/status"): handle_get_status,
        ("GET", "/api/help"): handle_get_help,
        ("GET", "/api/portfolio"): handle_get_portfolio,
        ("GET", "/api/bundles"): handle_get_bundles,
        ("POST", "/api/import"): handle_post_import,
        ("POST", "/api/paper/start"): handle_post_paper_start,
        ("POST", "/api/paper/stop"): handle_post_paper_stop,
        ("POST", "/api/paper/kill"): handle_post_paper_kill,
        ("POST", "/api/paper/resume"): handle_post_paper_resume,
        ("GET", "/api/activity"): handle_get_activity,
        ("GET", "/api/risk"): handle_get_risk,
        ("PUT", "/api/risk"): handle_put_risk,
    }
    route = routes.get((method, path))
    if route is None:
        _error(handler, 404, "not found")
        return
    route(handler, home, supervisor)
