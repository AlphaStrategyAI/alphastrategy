from __future__ import annotations

import cgi
import json
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from alphastrategy.bundle.import_bundle import import_asb
from alphastrategy.bundle.schema import load_risk_envelope
from alphastrategy.errors import ImportRejected
from alphastrategy.home import AlphaStrategyHome
from alphastrategy.risk.policy import AccountPolicy, merge_limits
from alphastrategy.supervisor import audit
from alphastrategy.supervisor.loop import Supervisor
from alphastrategy.supervisor.state import SupervisorState


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(runtime, sort_keys=True), encoding="utf-8")


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


def _bundle_envelope(home: AlphaStrategyHome, bundle_id: str) -> dict[str, Any]:
    envelope_path = home.bundle_dir(bundle_id) / "risk-envelope.yaml"
    if not envelope_path.is_file():
        return {}
    return load_risk_envelope(envelope_path.read_bytes())


def _effective_sleeve_policy(
    home: AlphaStrategyHome,
    supervisor: Supervisor,
    bundle_id: str,
) -> AccountPolicy:
    runtime = _load_runtime(home)
    sleeve_overlays = runtime.get("sleeve_overlays", {})
    overlay = sleeve_overlays.get(bundle_id) if isinstance(sleeve_overlays, dict) else None
    envelope = _bundle_envelope(home, bundle_id)
    return merge_limits(envelope, supervisor.policy, overlay)


def _read_audit_events(home: AlphaStrategyHome, limit: int = 50) -> list[dict[str, Any]]:
    path = home.audit_path()
    if not path.is_file():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines[-limit:]]


def _extract_upload(handler: Any) -> tuple[str, bytes]:
    content_type = handler.headers.get("Content-Type", "")
    if "multipart/form-data" not in content_type:
        raise ValueError("expected multipart file upload")
    length = int(handler.headers.get("Content-Length", "0"))
    env = {
        "REQUEST_METHOD": "POST",
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(length),
    }
    form = cgi.FieldStorage(
        fp=handler.rfile,
        headers=handler.headers,
        environ=env,
        keep_blank_values=True,
    )
    if "file" in form:
        field = form["file"]
    else:
        keys = [key for key in form.keys() if key]
        if not keys:
            raise ValueError("missing upload field")
        field = form[keys[0]]
    if not getattr(field, "file", None):
        raise ValueError("missing upload file")
    filename = field.filename or "upload.asb"
    data = field.file.read()
    return filename, data


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
        },
    )


def handle_get_portfolio(handler: Any, home: AlphaStrategyHome, supervisor: Supervisor) -> None:
    account = supervisor.broker.get_account()
    equity = float(account.get("equity", 0))
    cash = float(account.get("cash", equity))
    positions = supervisor.broker.list_positions()
    snapshot = supervisor.snapshot
    payload: dict[str, Any] = {
        "equity": equity,
        "cash": cash,
        "pnl": float(account.get("pnl", account.get("day_pnl", 0)) or 0),
        "positions": positions,
        "sleeves": dict(snapshot.sleeves),
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
            "paper": paper,
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
        _error(handler, 400, str(exc))
    except Exception as exc:
        _error(handler, 400, str(exc))
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
        supervisor.start_sleeve(bundle_id, allocation)
        _json_response(handler, 200, {"ok": True})
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
            supervisor.kill_sleeve(str(bundle_id))
        else:
            supervisor.kill_account()
        _json_response(handler, 200, {"ok": True})
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
        bundle_id: _policy_to_dict(_effective_sleeve_policy(home, supervisor, bundle_id))
        for bundle_id in imported
    }
    _json_response(
        handler,
        200,
        {
            "account": _policy_to_dict(supervisor.policy),
            "sleeves": sleeves,
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

        _json_response(handler, 200, {"ok": True})
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
    routes = {
        ("GET", "/api/status"): handle_get_status,
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
