from __future__ import annotations

import http.client
import json as json_module
import re
import threading
from dataclasses import asdict
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest

from alphastrategy.api.app import make_server
from alphastrategy.home import AlphaStrategyHome
from alphastrategy.risk.policy import AccountPolicy
from alphastrategy.supervisor.clock import ClockSnapshot, rebalance_countdown
from alphastrategy.supervisor.loop import Supervisor
from alphastrategy.supervisor.state import SupervisorState, save_state


class FakeBroker:
    def __init__(
        self,
        *,
        equity: float = 10_000.0,
        is_open: bool = False,
    ) -> None:
        self.equity = equity
        self.positions: dict[str, float] = {}
        self.close_all_count = 0
        self.orders: list[tuple[str, float, str]] = []
        self._is_open = is_open
        self._now = datetime(2024, 1, 31, 14, 30)
        self._next_open = datetime(2024, 1, 31, 14, 30)
        self._next_close = datetime(2024, 1, 31, 21, 0)
        self.account_reads = 0
        self.position_reads = 0

    def get_account(self) -> dict:
        self.account_reads += 1
        return {"equity": str(self.equity), "cash": str(self.equity)}

    def list_positions(self) -> list[dict]:
        self.position_reads += 1
        return [{"symbol": symbol, "qty": str(qty)} for symbol, qty in self.positions.items()]

    def place_order(self, symbol: str, qty: float, side: str) -> dict:
        self.orders.append((symbol, qty, side))
        delta = qty if side == "buy" else -qty
        self.positions[symbol] = self.positions.get(symbol, 0.0) + delta
        return {"id": "order-1", "status": "filled"}

    def cancel_order(self, order_id: str) -> None:
        return None

    def cancel_open_orders(self) -> None:
        return None

    def close_all(self) -> None:
        self.close_all_count += 1
        self.positions = {}

    def get_clock(self) -> dict:
        return {
            "is_open": self._is_open,
            "next_open": self._next_open.isoformat(),
            "next_close": self._next_close.isoformat(),
            "timestamp": self._now.isoformat(),
        }

    def get_bars(self, symbols: list[str], start: str, end: str) -> dict:
        return {symbol: {"bars": [{"c": 100.0}]} for symbol in symbols}


class ApiResponse:
    def __init__(self, response: http.client.HTTPResponse) -> None:
        self.status = response.status
        self.headers = response.headers
        raw = response.read()
        self.body = raw
        self._json: dict | list | None = None
        if raw:
            try:
                self._json = json_module.loads(raw.decode("utf-8"))
            except json_module.JSONDecodeError:
                self._json = None

    def json(self) -> dict | list:
        if self._json is None:
            raise ValueError("response is not JSON")
        return self._json


class ApiClient:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port

    def request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> ApiResponse:
        conn = http.client.HTTPConnection(self.host, self.port)
        conn.request(method, path, body=body, headers=headers or {})
        return ApiResponse(conn.getresponse())

    def get(self, path: str) -> ApiResponse:
        return self.request("GET", path)

    def post(self, path: str, json: dict | None = None) -> ApiResponse:
        payload = json_module.dumps(json).encode("utf-8")
        return self.request(
            "POST",
            path,
            body=payload,
            headers={"Content-Type": "application/json", "Content-Length": str(len(payload))},
        )

    def put(self, path: str, json: dict | None = None) -> ApiResponse:
        payload = json_module.dumps(json).encode("utf-8")
        return self.request(
            "PUT",
            path,
            body=payload,
            headers={"Content-Type": "application/json", "Content-Length": str(len(payload))},
        )

    def post_file(self, path: str, file_path: Path, field_name: str = "file") -> ApiResponse:
        data = file_path.read_bytes()
        boundary = "----alphastrategy-test"
        parts = [
            (
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"{field_name}\"; "
                f"filename=\"{file_path.name}\"\r\n"
                "Content-Type: application/octet-stream\r\n\r\n"
            ).encode("utf-8"),
            data,
            f"\r\n--{boundary}--\r\n".encode("utf-8"),
        ]
        body = b"".join(parts)
        return self.request(
            "POST",
            path,
            body=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            },
        )


@pytest.fixture
def api_stack(tmp_path: Path):
    broker = FakeBroker()
    home = AlphaStrategyHome(root=tmp_path)
    home.bundle_dir("asb_x").mkdir(parents=True)
    home.bundle_dir("asb_y").mkdir(parents=True)
    supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={
            "asb_x": {"AAPL": 1.0},
            "asb_y": {"MSFT": 1.0},
        },
    )
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = ApiClient("127.0.0.1", server.server_port)
    yield client, home, supervisor, broker
    server.shutdown()
    thread.join(timeout=2)


@pytest.fixture
def api_client(api_stack):
    return api_stack[0]


def test_import_bad_zip_returns_400(api_client: ApiClient, tmp_path: Path):
    bad = tmp_path / "bad.asb"
    bad.write_bytes(b"not a zip file")
    response = api_client.post_file("/api/import", bad)
    assert response.status == 400
    body = response.json()
    assert "error" in body
    assert body["error"]
    assert body["kind"] == "archive"
    assert body["title"]
    assert body["next"]


def test_import_hash_mismatch_returns_kind(api_client: ApiClient, tmp_path: Path) -> None:
    from tests.alphastrategy.fixtures.make_asb import build_golden_asb, mutate_member

    dest = tmp_path / "tampered.asb"
    dest.write_bytes(mutate_member(build_golden_asb(), "strategy.dsl.yaml", b"steps: []\n"))
    response = api_client.post_file("/api/import", dest)
    assert response.status == 400
    body = response.json()
    assert body["kind"] == "hash"
    assert "hash" in body["error"].lower()
    assert body["title"]
    assert "Re-export" in body["next"]


def test_start_rejects_allocation_sum_over_one(api_client: ApiClient):
    r = api_client.post("/api/paper/start", json={"bundle_id": "asb_x", "allocation": 0.7})
    assert r.status == 200
    r2 = api_client.post("/api/paper/start", json={"bundle_id": "asb_y", "allocation": 0.4})
    assert r2.status == 409
    body = r2.json()
    assert "error" in body


def test_start_replaces_existing_sleeve_allocation(api_client: ApiClient):
    first = api_client.post("/api/paper/start", json={"bundle_id": "asb_x", "allocation": 0.7})
    assert first.status == 200
    second = api_client.post("/api/paper/start", json={"bundle_id": "asb_x", "allocation": 0.5})
    assert second.status == 200
    bundles = api_client.get("/api/bundles").json()
    assert bundles["paper"]["asb_x"] == 0.5


def test_start_while_halted_returns_held(api_stack):
    client, _home, supervisor, _broker = api_stack
    first = client.post("/api/paper/start", json={"bundle_id": "asb_x", "allocation": 0.15})
    assert first.status == 200
    assert first.json()["ok"] is True
    assert first.json()["held"] is False
    supervisor._halt("stale bars")
    second = client.post("/api/paper/start", json={"bundle_id": "asb_x", "allocation": 0.2})
    assert second.status == 200
    body = second.json()
    assert body["ok"] is True
    assert body["held"] is True
    assert body["flattened"] is False
    assert supervisor.state == SupervisorState.HALTED
    assert supervisor.snapshot.sleeves["asb_x"] == 0.2


def test_status_returns_state_clock_and_halt(api_client: ApiClient):
    response = api_client.get("/api/status")
    assert response.status == 200
    body = response.json()
    assert "state" in body
    assert "clock" in body
    assert isinstance(body["clock"], dict)
    assert "is_open" in body["clock"]
    assert "halted" in body
    assert body["flattened"] is False


def test_status_day_pnl_null_without_last_equity(api_stack):
    client, _home, supervisor, broker = api_stack
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["pnl"] is None
    assert body["pnl_source"] is None
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"


def test_status_day_pnl_from_last_equity(api_stack):
    client, _home, _supervisor, broker = api_stack
    orig = broker.get_account

    def with_last():
        account = orig()
        account["last_equity"] = "9900"
        return account

    broker.get_account = with_last  # type: ignore[method-assign]
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["pnl"] == 100.0
    assert body["pnl_source"] == "last_close"
    assert broker.close_all_count == close_all_before


def test_status_heartbeat_missing_before_tick(api_client: ApiClient) -> None:
    body = api_client.get("/api/status").json()
    assert body["heartbeat"]["pulse"] == "missing"
    assert body["heartbeat"]["interval_seconds"] == 20
    assert body["heartbeat"]["at"] is None


def test_status_heartbeat_live_after_tick(api_stack) -> None:
    client, _home, supervisor, _broker = api_stack
    supervisor.tick()
    body = client.get("/api/status").json()
    assert body["heartbeat"]["pulse"] == "live"
    assert body["heartbeat"]["at"]
    assert body["heartbeat"]["interval_seconds"] == 20


def test_status_flattened_true_after_account_kill(api_stack):
    client, _home, supervisor, _broker = api_stack
    supervisor.kill_account()
    body = client.get("/api/status").json()
    assert body["state"] == "stopped"
    assert body["flattened"] is True


def test_handlers_never_set_paper_false():
    api_dir = Path(__file__).resolve().parents[2] / "src" / "alphastrategy" / "api"
    patterns = [
        re.compile(r"paper\s*=\s*False"),
        re.compile(r"['\"]paper['\"]\s*:\s*False"),
        re.compile(r"paper\s*=\s*false"),
        re.compile(r"['\"]paper['\"]\s*:\s*false"),
    ]
    for path in api_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            assert not pattern.search(text), f"{path.name} may set paper=False: {pattern.pattern}"


def test_make_server_rejects_non_loopback_bind(api_stack):
    _, home, supervisor, _ = api_stack
    with pytest.raises(ValueError, match="loopback"):
        make_server(home, supervisor, bind="0.0.0.0", port=0)


def test_get_bundles_lists_imported_and_paper(api_stack):
    client, home, supervisor, _ = api_stack
    bundle_dir = home.imported_dir() / "asb_test"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "bundle.yaml").write_text("bundle_id: asb_test\n", encoding="utf-8")
    supervisor.start_sleeve("asb_test", 0.25)

    response = client.get("/api/bundles")
    assert response.status == 200
    body = response.json()
    assert "asb_test" in body["imported"]
    assert body["paper"]["asb_test"] == 0.25
    assert "imported_at" in body


def test_get_portfolio_returns_account_fields(api_client: ApiClient):
    response = api_client.get("/api/portfolio")
    assert response.status == 200
    body = response.json()
    assert body["equity"] == 10_000.0
    assert body["cash"] == 10_000.0
    assert body["pnl"] is None
    assert body["pnl_source"] is None
    assert "positions" in body
    assert "sleeves" in body


def test_get_portfolio_pnl_from_last_equity(api_stack):
    client, _home, _supervisor, broker = api_stack
    orig = broker.get_account

    def with_last():
        account = orig()
        account["last_equity"] = "9900"
        return account

    broker.get_account = with_last  # type: ignore[method-assign]
    close_all_before = broker.close_all_count
    body = client.get("/api/portfolio").json()
    assert body["pnl"] == 100.0
    assert body["pnl_source"] == "last_close"
    assert broker.close_all_count == close_all_before


def test_get_portfolio_pnl_prefers_account_field(api_stack):
    client, _home, _supervisor, broker = api_stack
    orig = broker.get_account

    def with_both():
        account = orig()
        account["pnl"] = "42.5"
        account["last_equity"] = "9900"
        return account

    broker.get_account = with_both  # type: ignore[method-assign]
    body = client.get("/api/portfolio").json()
    assert body["pnl"] == 42.5
    assert body["pnl_source"] == "account"


def test_get_portfolio_explicit_zero_pnl_is_not_null(api_stack):
    client, _home, _supervisor, broker = api_stack
    orig = broker.get_account

    def with_zero():
        account = orig()
        account["pnl"] = "0"
        return account

    broker.get_account = with_zero  # type: ignore[method-assign]
    body = client.get("/api/portfolio").json()
    assert body["pnl"] == 0.0
    assert body["pnl_source"] == "account"


def _positions_by_symbol(positions: list[dict]) -> dict[str, dict]:
    return {str(row["symbol"]): row for row in positions}


def test_get_portfolio_position_day_pnl_null_without_last_close(api_stack):
    client, home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 15.0}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    close_all_before = broker.close_all_count
    body = client.get("/api/portfolio").json()
    row = _positions_by_symbol(body["positions"])["AAPL"]
    assert row["day_pnl"] is None
    assert broker.close_all_count == close_all_before


def test_get_portfolio_position_day_pnl_from_intraday(api_stack):
    client, _home, _supervisor, broker = api_stack
    orig = broker.list_positions

    def with_intraday():
        rows = orig()
        for row in rows:
            row["unrealized_intraday_pl"] = "12.5"
            row["unrealized_pl"] = "999"
        return rows

    broker.list_positions = with_intraday  # type: ignore[method-assign]
    broker.positions = {"AAPL": 15.0}
    body = client.get("/api/portfolio").json()
    assert _positions_by_symbol(body["positions"])["AAPL"]["day_pnl"] == 12.5


def test_get_portfolio_position_day_pnl_ignores_unrealized_pl(api_stack):
    client, _home, _supervisor, broker = api_stack
    orig = broker.list_positions

    def with_lifetime():
        rows = orig()
        for row in rows:
            row["unrealized_pl"] = "999"
        return rows

    broker.list_positions = with_lifetime  # type: ignore[method-assign]
    broker.positions = {"AAPL": 15.0}
    body = client.get("/api/portfolio").json()
    assert _positions_by_symbol(body["positions"])["AAPL"]["day_pnl"] is None


def test_get_portfolio_position_day_pnl_from_lastday_price(api_stack):
    client, home, supervisor, broker = api_stack
    orig = broker.list_positions

    def with_last_close():
        rows = orig()
        for row in rows:
            row["lastday_price"] = "100"
        return rows

    broker.list_positions = with_last_close  # type: ignore[method-assign]
    broker.positions = {"AAPL": 15.0}
    supervisor.snapshot.last_prices = {"AAPL": 110.0}
    save_state(home.state_path(), supervisor.snapshot)
    body = client.get("/api/portfolio").json()
    assert _positions_by_symbol(body["positions"])["AAPL"]["day_pnl"] == 150.0


def test_get_activity_returns_audit_events(api_stack):
    client, home, _, _ = api_stack
    from alphastrategy.supervisor import audit

    audit.append(home.audit_path(), {"event": "paper_start", "bundle_id": "asb_x"})
    response = client.get("/api/activity")
    assert response.status == 200
    events = response.json()
    assert isinstance(events, list)
    assert events[-1]["event"] == "paper_start"


def test_put_risk_tightens_account_policy(api_stack):
    client, home, supervisor, _ = api_stack
    response = client.put("/api/risk", json={"account": {"max_name_weight": 0.15}})
    assert response.status == 200
    assert response.json()["ok"] is True
    assert response.json()["flattened"] is False
    assert supervisor.policy.max_name_weight == 0.15

    risk = client.get("/api/risk").json()
    assert risk["account"]["max_name_weight"] == 0.15


def test_put_risk_source_uses_supervisor_apply_risk() -> None:
    from alphastrategy.api import handlers as handlers_mod

    src = Path(handlers_mod.__file__).read_text(encoding="utf-8")
    body = src.split("def handle_put_risk", 1)[1].split("def dispatch", 1)[0]
    assert "apply_risk" in body
    assert "_load_runtime" not in body
    assert "_bundle_envelope" not in body


def test_put_risk_overlay_does_not_reload_envelope_in_handlers(
    api_stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alphastrategy.api import handlers as handlers_mod
    from alphastrategy.bundle.schema import load_risk_envelope
    from alphastrategy.supervisor import loop as loop_mod

    assert not hasattr(handlers_mod, "load_risk_envelope")
    client, home, supervisor, _broker = api_stack
    bundle_dir = home.imported_dir() / "asb_x"
    (bundle_dir / "risk-envelope.yaml").write_text(
        "max_name_weight: 0.20\n", encoding="utf-8"
    )
    loads = {"n": 0}
    orig = load_risk_envelope

    def counted(raw: bytes):
        loads["n"] += 1
        return orig(raw)

    monkeypatch.setattr(loop_mod, "load_risk_envelope", counted)
    supervisor.sleeve_policies(["asb_x"])
    after = loads["n"]
    assert after >= 1
    response = client.put(
        "/api/risk",
        json={"sleeves": {"asb_x": {"max_name_weight": 0.15}}},
    )
    assert response.status == 200
    assert response.json()["ok"] is True
    assert loads["n"] == after


def test_put_risk_flattens_when_live_book_breaches(api_stack):
    client, _home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 15.0}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor._persist()
    response = client.put("/api/risk", json={"account": {"max_gross": 0.1}})
    assert response.status == 200
    body = response.json()
    assert body["ok"] is True
    assert body["flattened"] is True
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.close_all_count == 1


def test_put_risk_overlay_while_idle_does_not_flatten_live_book(api_stack):
    client, home, supervisor, broker = api_stack
    bundle_dir = home.imported_dir() / "asb_x"
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 0.20\n", encoding="utf-8")
    broker.positions = {"AAPL": 15.0}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor._persist()
    response = client.put(
        "/api/risk",
        json={"sleeves": {"asb_x": {"max_name_weight": 0.05}}},
    )
    assert response.status == 200
    body = response.json()
    assert body["ok"] is True
    assert body["flattened"] is False
    assert supervisor.state != SupervisorState.STOPPED
    assert broker.close_all_count == 0


def test_put_risk_overlay_while_allocated_flattens_live_book(api_stack):
    client, home, supervisor, broker = api_stack
    bundle_dir = home.imported_dir() / "asb_x"
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 0.20\n", encoding="utf-8")
    broker.positions = {"AAPL": 15.0}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor._persist()
    start = client.post("/api/paper/start", json={"bundle_id": "asb_x", "allocation": 0.25})
    assert start.status == 200
    assert start.json()["flattened"] is False
    response = client.put(
        "/api/risk",
        json={"sleeves": {"asb_x": {"max_name_weight": 0.05}}},
    )
    assert response.status == 200
    body = response.json()
    assert body["ok"] is True
    assert body["flattened"] is True
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.close_all_count == 1


def test_start_flattens_when_idle_overlay_breaches_live_book(api_stack):
    client, home, supervisor, broker = api_stack
    bundle_dir = home.imported_dir() / "asb_x"
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 0.20\n", encoding="utf-8")
    broker.positions = {"AAPL": 15.0}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor._persist()
    overlay = client.put(
        "/api/risk",
        json={"sleeves": {"asb_x": {"max_name_weight": 0.05}}},
    )
    assert overlay.status == 200
    assert overlay.json()["flattened"] is False
    response = client.post(
        "/api/paper/start",
        json={"bundle_id": "asb_x", "allocation": 0.25},
    )
    assert response.status == 200
    body = response.json()
    assert body["ok"] is True
    assert body["held"] is False
    assert body["flattened"] is True
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.close_all_count == 1


def test_get_risk_spoken_follows_allocated_overlay(api_stack):
    client, home, supervisor, _broker = api_stack
    bundle_dir = home.imported_dir() / "asb_x"
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 0.20\n", encoding="utf-8")
    overlay = client.put(
        "/api/risk",
        json={"sleeves": {"asb_x": {"max_name_weight": 0.05, "max_names": 10}}},
    )
    assert overlay.status == 200
    idle = client.get("/api/risk").json()
    assert idle["account"]["max_name_weight"] == 0.20
    assert idle["spoken"]["max_name_weight"] == 0.20
    assert idle["utilization"]["max_name_weight"] == 0.20
    assert idle["spoken"]["max_names"] == 50
    start = client.post("/api/paper/start", json={"bundle_id": "asb_x", "allocation": 0.25})
    assert start.status == 200
    spoken = client.get("/api/risk").json()
    assert spoken["account"]["max_name_weight"] == 0.20
    assert spoken["account"]["max_names"] == 50
    assert spoken["spoken"]["max_name_weight"] == 0.05
    assert spoken["spoken"]["max_names"] == 10
    assert spoken["utilization"]["max_name_weight"] == 0.05
    assert spoken["utilization"]["max_names"] == 10
    status = client.get("/api/status").json()
    assert status["utilization"]["max_name_weight"] == 0.05
    assert status["utilization"]["max_names"] == 10


def test_status_live_limit_does_not_flatten(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_got = {"AAPL": 0.225}
    supervisor.snapshot.last_prices = {"AAPL": 150.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {"AAPL": 15.0}
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["reason"] == "max_name_weight"
    assert body["utilization"]["live_limit"]["kind"] == "book"
    risk = client.get("/api/risk").json()
    assert risk["utilization"]["live_limit"]["reason"] == "max_name_weight"
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"


def test_status_live_limit_without_last_got_uses_priced_book(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_prices = {"AAPL": 150.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {"AAPL": 15.0}
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["reason"] == "max_name_weight"
    risk = client.get("/api/risk").json()
    assert risk["utilization"]["live_limit"]["reason"] == "max_name_weight"
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"


def test_status_live_limit_priced_book_wins_over_stale_last_got(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_got = {"AAPL": 0.15}
    supervisor.snapshot.last_prices = {"AAPL": 150.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {"AAPL": 15.0}
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["reason"] == "max_name_weight"


def test_status_live_limit_next_send_order_size(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.set_policy({"max_order_notional_frac": 0.10})
    supervisor.snapshot.last_got = {}
    supervisor.snapshot.last_combined = {"AAPL": 0.18}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {}
    close_all_before = broker.close_all_count
    body = client.get("/api/status").json()
    assert body["utilization"]["live_limit"]["reason"] == "max_order_notional_frac"
    assert body["utilization"]["live_limit"]["kind"] == "send"
    risk = client.get("/api/risk").json()
    assert risk["utilization"]["live_limit"]["reason"] == "max_order_notional_frac"
    assert risk["utilization"]["live_limit"]["kind"] == "send"
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"


def test_put_risk_rejects_loosening(api_client: ApiClient):
    response = api_client.put("/api/risk", json={"account": {"max_name_weight": 0.25}})
    assert response.status == 400
    assert "error" in response.json()


def test_put_risk_atomic_invalid_sleeve_leaves_account_policy_unchanged(api_stack):
    client, home, supervisor, _ = api_stack
    bundle_dir = home.imported_dir() / "asb_test"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 0.20\n", encoding="utf-8")

    assert supervisor.policy.max_name_weight == 0.20

    response = client.put(
        "/api/risk",
        json={
            "account": {"max_name_weight": 0.15},
            "sleeves": {"asb_test": {"max_name_weight": 0.25}},
        },
    )
    assert response.status == 400
    assert supervisor.policy.max_name_weight == 0.20
    assert not home.runtime_path().exists()


def test_put_risk_sleeve_overlay_rejects_second_loosening(api_stack):
    client, home, _, _ = api_stack
    bundle_dir = home.imported_dir() / "asb_test"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 0.20\n", encoding="utf-8")

    tighten = client.put(
        "/api/risk",
        json={"sleeves": {"asb_test": {"max_name_weight": 0.15}}},
    )
    assert tighten.status == 200
    risk = client.get("/api/risk").json()
    assert risk["sleeves"]["asb_test"]["max_name_weight"] == 0.15

    loosen = client.put(
        "/api/risk",
        json={"sleeves": {"asb_test": {"max_name_weight": 0.18}}},
    )
    assert loosen.status == 400
    assert "error" in loosen.json()


def test_import_golden_asb_via_api(api_stack, tmp_path: Path):
    client, home, _, _ = api_stack
    golden = Path(__file__).parent / "fixtures" / "golden.asb"
    response = client.post_file("/api/import", golden)
    assert response.status == 200
    body = response.json()
    bundle_id = body["bundle_id"]
    assert bundle_id.startswith("asb_")
    assert home.bundle_dir(bundle_id).is_dir()
    bundles = client.get("/api/bundles").json()
    assert bundle_id in bundles["imported"]
    assert bundle_id in bundles["imported_at"]
    assert "T" in bundles["imported_at"][bundle_id]


def test_get_root_returns_html(api_client: ApiClient):
    response = api_client.get("/")
    assert response.status == 200
    assert b"text/html" in response.headers.get("Content-Type", "").encode()
    body = response.body.decode("utf-8")
    assert "<title>alphastrategy</title>" in body
    assert "Portfolio" in body


def test_get_static_assets(api_client: ApiClient):
    css = api_client.get("/styles.css")
    assert css.status == 200
    assert b"text/css" in css.headers.get("Content-Type", "").encode()
    assert b"#0b0e14" in css.body

    js = api_client.get("/app.js")
    assert js.status == 200
    assert b"javascript" in js.headers.get("Content-Type", "").encode()
    assert b"/api/status" in js.body
    from alphastrategy.web.cockpit import cockpit_js

    assert js.body == cockpit_js().encode("utf-8")

    static_css = api_client.get("/static/styles.css")
    assert static_css.status == 200
    assert b"text/css" in static_css.headers.get("Content-Type", "").encode()
    assert static_css.body == css.body

    static_js = api_client.get("/static/app.js")
    assert static_js.status == 200
    assert b"javascript" in static_js.headers.get("Content-Type", "").encode()
    assert static_js.body == js.body


def test_dispatch_reloads_cli_persisted_sleeve(api_stack):
    client, home, supervisor, broker = api_stack
    assert supervisor.snapshot.sleeves == {}

    cli_supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={"asb_x": {"AAPL": 1.0}},
    )
    cli_supervisor.start_sleeve("asb_x", 0.3)

    assert supervisor.snapshot.sleeves == {}

    response = client.get("/api/bundles")
    assert response.status == 200
    body = response.json()
    assert body["paper"]["asb_x"] == 0.3
    assert supervisor.snapshot.sleeves["asb_x"] == 0.3


def test_status_includes_last_rebalance_and_countdown(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_rebalance_event = "2024-01-31:open"
    save_state(home.state_path(), supervisor.snapshot)
    broker._is_open = True
    response = client.get("/api/status")
    assert response.status == 200
    body = response.json()
    assert body["last_rebalance_event"] == "2024-01-31:open"
    assert body["last_rebalance_complete"] is True
    clock = body["clock"]
    cur = ClockSnapshot(
        is_open=bool(clock["is_open"]),
        next_open=datetime.fromisoformat(clock["next_open"]),
        next_close=datetime.fromisoformat(clock["next_close"]),
        now=datetime.fromisoformat(clock["timestamp"]),
    )
    expected = rebalance_countdown(cur, "2024-01-31:open")
    assert body["countdown"]["next_rebalance"] == expected.next_rebalance
    assert body["countdown"]["seconds"] == expected.seconds
    assert "at" in body["countdown"]


def test_status_countdown_null_when_clock_fails(api_stack):
    client, _home, _supervisor, broker = api_stack

    def boom() -> dict:
        raise RuntimeError("clock down")

    broker.get_clock = boom  # type: ignore[method-assign]
    body = client.get("/api/status").json()
    assert "error" in body["clock"]
    assert body["countdown"] is None


def test_portfolio_includes_contribution_and_position_weight(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_combined = {"AAPL": 0.4}
    supervisor.snapshot.last_sleeve_contribution = {"asb_x": {"AAPL": 0.4}}
    supervisor.snapshot.last_prices = {"AAPL": 100.0}
    supervisor.snapshot.last_rebalance_event = "2024-01-31:open"
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {"AAPL": 10.0}
    broker.equity = 10_000.0
    body = client.get("/api/portfolio").json()
    assert body["last_combined"] == {"AAPL": 0.4}
    assert body["sleeve_contribution"]["asb_x"]["AAPL"] == 0.4
    assert body["last_rebalance_event"] == "2024-01-31:open"
    pos = next(item for item in body["positions"] if item["symbol"] == "AAPL")
    assert float(pos["qty"]) == 10.0
    assert pos["notional"] == pytest.approx(1000.0)
    assert pos["weight"] == pytest.approx(0.1)
    assert pos["wanted"] == pytest.approx(0.4)


def test_portfolio_includes_wanted_name_with_no_fill(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_combined = {"AAPL": 0.4, "MSFT": 0.2}
    supervisor.snapshot.last_prices = {"AAPL": 100.0, "MSFT": 200.0}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {"AAPL": 10.0}
    broker.equity = 10_000.0
    body = client.get("/api/portfolio").json()
    msft = next(item for item in body["positions"] if item["symbol"] == "MSFT")
    assert float(msft["qty"]) == 0.0
    assert msft["wanted"] == pytest.approx(0.2)
    assert msft["weight"] == pytest.approx(0.0)


def test_portfolio_fill_stays_on_last_rebalance_after_mark(api_stack):
    client, home, supervisor, broker = api_stack
    supervisor.snapshot.last_combined = {"AAPL": 0.15}
    supervisor.snapshot.last_prices = {"AAPL": 150.0}
    supervisor.snapshot.last_got = {"AAPL": 0.225}
    supervisor.snapshot.last_fill_got = {"AAPL": 0.15}
    save_state(home.state_path(), supervisor.snapshot)
    broker.positions = {"AAPL": 15.0}
    broker.equity = 10_000.0
    body = client.get("/api/portfolio").json()
    pos = next(item for item in body["positions"] if item["symbol"] == "AAPL")
    assert pos["weight"] == pytest.approx(0.225)
    assert pos["fill"] == pytest.approx(0.15)
    assert pos["wanted"] == pytest.approx(0.15)


def test_bundles_lists_stopped(api_stack):
    client, _home, supervisor, _broker = api_stack
    supervisor.start_sleeve("asb_x", 0.25)
    supervisor.stop_sleeve("asb_x")
    body = client.get("/api/bundles").json()
    assert "asb_x" in body["stopped"]
    assert "asb_x" not in body["paper"]


def test_api_kill_sleeve_isolates(api_stack):
    client, _home, supervisor, broker = api_stack
    supervisor.start_sleeve("asb_x", 0.15)
    supervisor.start_sleeve("asb_y", 0.15)
    broker._is_open = True
    broker._now = datetime(2024, 1, 31, 14, 33)
    supervisor.tick()
    assert broker.positions.get("AAPL", 0) > 0
    assert broker.positions.get("MSFT", 0) > 0
    close_all_before = broker.close_all_count
    response = client.post("/api/paper/kill", json={"bundle_id": "asb_x"})
    assert response.status == 200
    assert broker.close_all_count == close_all_before
    assert supervisor.state.value != "stopped"
    bundles = client.get("/api/bundles").json()
    assert "asb_x" in bundles["stopped"]
    assert bundles["paper"]["asb_y"] == 0.15
    assert broker.positions.get("AAPL", 0.0) == 0.0
    assert broker.positions.get("MSFT", 0.0) > 0


def test_api_kill_sleeve_returns_isolated_payload(api_stack):
    client, _home, supervisor, broker = api_stack
    supervisor.start_sleeve("asb_x", 0.15)
    supervisor.start_sleeve("asb_y", 0.15)
    broker._is_open = True
    broker._now = datetime(2024, 1, 31, 14, 33)
    supervisor.tick()
    response = client.post("/api/paper/kill", json={"bundle_id": "asb_x"})
    assert response.status == 200
    body = response.json()
    assert body["ok"] is True
    assert body["isolated"] is True
    assert body["flattened"] is False
    assert body["reason"] == "isolated"
    status = client.get("/api/status").json()
    assert status["last_kill"]["reason"] == "isolated"
    assert status["last_kill"]["bundle_id"] == "asb_x"


def test_api_kill_account_returns_account_payload(api_stack):
    client, _home, supervisor, _broker = api_stack
    response = client.post("/api/paper/kill", json={})
    assert response.status == 200
    body = response.json()
    assert body["isolated"] is False
    assert body["flattened"] is True
    assert body["reason"] == "account"
    status = client.get("/api/status").json()
    assert status["last_kill"]["reason"] == "account"


def test_status_and_risk_include_utilization(api_stack) -> None:
    client, home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 4.0, "MSFT": 2.0}
    supervisor.snapshot.orders_today = 7
    save_state(home.state_path(), supervisor.snapshot)
    status = client.get("/api/status").json()
    util = status["utilization"]
    assert util["names"] == 2
    assert util["orders_today"] == 7
    assert util["max_names"] == supervisor.policy.max_names
    assert util["max_orders_per_day"] == supervisor.policy.max_orders_per_day
    assert util["cash_weight"] == pytest.approx(1.0)
    risk = client.get("/api/risk").json()
    assert risk["utilization"]["names"] == 2
    assert risk["utilization"]["orders_today"] == 7


def test_status_portfolio_risk_share_one_live_book(api_stack) -> None:
    client, _home, _supervisor, broker = api_stack
    broker.positions = {"AAPL": 4.0}
    client.get("/api/status")
    client.get("/api/portfolio")
    client.get("/api/risk")
    assert broker.account_reads == 1
    assert broker.position_reads == 1


def test_tick_seeds_live_book_for_status_and_portfolio(api_stack) -> None:
    client, _home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 4.0}
    supervisor.tick()
    accounts = broker.account_reads
    positions = broker.position_reads
    client.get("/api/status")
    client.get("/api/portfolio")
    assert broker.account_reads == accounts
    assert broker.position_reads == positions


def test_glance_live_book_expires_after_ttl(
    api_stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alphastrategy.supervisor import loop as loop_mod

    client, _home, _supervisor, broker = api_stack
    broker.positions = {"AAPL": 4.0}
    clock = {"t": 0.0}
    monkeypatch.setattr(loop_mod.time, "monotonic", lambda: clock["t"])
    client.get("/api/status")
    assert broker.account_reads == 1
    assert broker.position_reads == 1
    clock["t"] += Supervisor.LIVE_BOOK_TTL_SEC + 0.1
    client.get("/api/status")
    assert broker.account_reads == 2
    assert broker.position_reads == 2


def test_heartbeat_live_book_holds_past_ttl_for_status_and_portfolio(
    api_stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alphastrategy.supervisor import loop as loop_mod

    client, _home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 4.0}
    clock = {"t": 0.0}
    monkeypatch.setattr(loop_mod.time, "monotonic", lambda: clock["t"])
    supervisor.tick()
    accounts = broker.account_reads
    positions = broker.position_reads
    clock["t"] += Supervisor.LIVE_BOOK_TTL_SEC + 5.0
    client.get("/api/status")
    client.get("/api/portfolio")
    assert broker.account_reads == accounts
    assert broker.position_reads == positions


def test_status_book_source_glance_without_tick(api_stack) -> None:
    client, _home, _supervisor, _broker = api_stack
    body = client.get("/api/status").json()
    assert body["book"]["source"] == "glance"


def test_status_book_source_heartbeat_after_tick(api_stack) -> None:
    client, _home, supervisor, _broker = api_stack
    supervisor.tick()
    body = client.get("/api/status").json()
    assert body["book"]["source"] == "heartbeat"


def test_status_book_source_glance_after_kill(api_stack) -> None:
    client, _home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 15.0}
    supervisor.tick()
    killed = client.post("/api/paper/kill", json={})
    assert killed.status == 200
    body = client.get("/api/status").json()
    assert body["book"]["source"] == "glance"


def test_portfolio_after_account_kill_is_not_stale_live_book(api_stack) -> None:
    client, _home, supervisor, broker = api_stack
    broker.positions = {"AAPL": 15.0}
    before = client.get("/api/portfolio").json()
    assert any(pos.get("symbol") == "AAPL" for pos in before["positions"])
    killed = client.post("/api/paper/kill", json={})
    assert killed.status == 200
    after = client.get("/api/portfolio").json()
    assert after["positions"] == []
    assert broker.close_all_count >= 1


def test_get_risk_includes_spoken_labels(api_client: ApiClient) -> None:
    from alphastrategy.risk.labels import POLICY_LABELS

    risk = api_client.get("/api/risk").json()
    assert risk["labels"] == POLICY_LABELS
    assert "max_gross" in risk["account"]
    assert risk["labels"]["max_gross"] == "Gross cap"


def test_get_risk_includes_v1_defaults(api_client: ApiClient) -> None:
    from dataclasses import asdict

    from alphastrategy.risk.policy import AccountPolicy

    risk = api_client.get("/api/risk").json()
    assert risk["defaults"] == asdict(AccountPolicy.defaults())
    assert risk["account"]["max_gross"] == risk["defaults"]["max_gross"]


def test_put_risk_ignores_defaults_payload(api_client: ApiClient) -> None:
    before = api_client.get("/api/risk").json()
    response = api_client.put(
        "/api/risk",
        json={
            "defaults": {"max_gross": 0.01},
            "account": {"max_name_weight": 0.15},
        },
    )
    assert response.status == 200
    after = api_client.get("/api/risk").json()
    assert after["defaults"] == before["defaults"]
    assert after["account"]["max_name_weight"] == 0.15
    assert after["account"]["max_gross"] == before["account"]["max_gross"]


def test_get_help_returns_operator_sections(api_client: ApiClient) -> None:
    from alphastrategy.helptext import help_payload

    response = api_client.get("/api/help")
    assert response.status == 200
    payload = response.json()
    assert payload["title"] == help_payload()["title"]
    ids = [section["id"] for section in payload["sections"]]
    assert ids == [
        "identity",
        "execution",
        "halt_flatten",
        "cockpit",
        "cli",
        "walls",
    ]
    assert [item["id"] for item in payload["howtos"]] == [
        "how_portfolio",
        "how_strategies",
        "how_run",
        "how_activity",
        "how_risk",
    ]
    assert [item["id"] for item in payload["tasks"]] == [
        "task_import",
        "task_start",
        "task_flatten",
        "task_tighten",
        "task_wanted",
        "task_spent",
    ]
    assert [item["id"] for item in payload["tutorials"]] == ["tutorial_first_session"]
    blob = json_module.dumps(payload)
    assert "secret" not in blob.lower()
    assert "ALPACA" not in blob


def test_get_root_includes_help_control(api_client: ApiClient) -> None:
    response = api_client.get("/")
    assert response.status == 200
    html = response.body.decode("utf-8")
    assert 'id="help-toggle"' in html
    assert 'id="help-panel"' in html
    assert 'data-screen="help"' not in html
