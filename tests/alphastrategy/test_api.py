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
from alphastrategy.supervisor.loop import Supervisor


class FakeBroker:
    def __init__(
        self,
        *,
        equity: float = 10_000.0,
        is_open: bool = False,
    ) -> None:
        self.equity = equity
        self.positions: dict[str, float] = {}
        self._is_open = is_open
        self._now = datetime(2024, 1, 31, 14, 30)
        self._next_open = datetime(2024, 1, 31, 14, 30)
        self._next_close = datetime(2024, 1, 31, 21, 0)

    def get_account(self) -> dict:
        return {"equity": str(self.equity), "cash": str(self.equity)}

    def list_positions(self) -> list[dict]:
        return [{"symbol": symbol, "qty": str(qty)} for symbol, qty in self.positions.items()]

    def place_order(self, symbol: str, qty: float, side: str) -> dict:
        return {"id": "order-1", "status": "filled"}

    def cancel_order(self, order_id: str) -> None:
        return None

    def close_all(self) -> None:
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
            except json.JSONDecodeError:
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


def test_status_returns_state_clock_and_halt(api_client: ApiClient):
    response = api_client.get("/api/status")
    assert response.status == 200
    body = response.json()
    assert "state" in body
    assert "clock" in body
    assert isinstance(body["clock"], dict)
    assert "is_open" in body["clock"]
    assert "halted" in body


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


def test_get_bundles_lists_imported_and_paper(api_stack):
    client, home, supervisor, _ = api_stack
    bundle_dir = home.imported_dir() / "asb_test"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "bundle.yaml").write_text("bundle_id: asb_test\n", encoding="utf-8")
    supervisor.start_sleeve("asb_test", 0.25)

    response = client.get("/api/bundles")
    assert response.status == 200
    body = response.json()
    assert "asb_test" in body["imported"]
    assert body["paper"]["asb_test"] == 0.25


def test_get_portfolio_returns_account_fields(api_client: ApiClient):
    response = api_client.get("/api/portfolio")
    assert response.status == 200
    body = response.json()
    assert body["equity"] == 10_000.0
    assert body["cash"] == 10_000.0
    assert "pnl" in body
    assert "positions" in body
    assert "sleeves" in body


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
    assert supervisor.policy.max_name_weight == 0.15

    risk = client.get("/api/risk").json()
    assert risk["account"]["max_name_weight"] == 0.15


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
