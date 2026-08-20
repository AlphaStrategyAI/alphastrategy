from __future__ import annotations

import http.client
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path

from alphastrategy.api.app import make_server
from alphastrategy.bundle.import_bundle import import_asb
from alphastrategy.cli.main import _make_weight_fn
from alphastrategy.home import AlphaStrategyHome
from alphastrategy.risk.policy import AccountPolicy
from alphastrategy.supervisor import audit
from alphastrategy.supervisor.loop import Supervisor
from alphastrategy.supervisor.state import SupervisorSnapshot, SupervisorState, save_state

from tests.alphastrategy.test_halt_flatten import FakeBroker

GOLDEN_ASB = Path(__file__).parent / "fixtures" / "golden.asb"


def _audit_event_types(home: AlphaStrategyHome) -> list[str]:
    path = home.audit_path()
    if not path.is_file():
        return []
    return [
        json.loads(line)["event"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _make_supervisor(home: AlphaStrategyHome, broker: FakeBroker) -> Supervisor:
    return Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        weight_fn=_make_weight_fn(home, broker),
    )


def _setup_broker_bars(broker: FakeBroker) -> None:
    bar = {"c": 100.0, "t": "2024-01-31"}
    for symbol in ("AAPL", "MSFT"):
        broker.bars[symbol] = {"bars": [bar]}


def test_v1_done_path(tmp_path: Path) -> None:
    home = AlphaStrategyHome(root=tmp_path)
    home.root.mkdir(parents=True, exist_ok=True)

    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    _setup_broker_bars(broker)

    bundle_id = import_asb(GOLDEN_ASB, home)
    audit.append(home.audit_path(), {"event": "import", "bundle_id": bundle_id})

    supervisor = _make_supervisor(home, broker)
    supervisor.start_sleeve(bundle_id, 0.4)

    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()

    assert broker.orders
    assert supervisor.last_rebalance_event == "2024-01-31:open"

    supervisor.set_policy({"max_gross": 0.1})
    broker.advance_now(session_close - timedelta(minutes=10))
    supervisor.tick()

    assert broker.close_all_count == 1
    assert supervisor.state == SupervisorState.STOPPED

    stopped_supervisor = _make_supervisor(home, broker)
    assert stopped_supervisor.state == SupervisorState.STOPPED
    flatten_close_all_count = broker.close_all_count
    stopped_supervisor.tick()
    assert broker.close_all_count == flatten_close_all_count

    snapshot = stopped_supervisor.snapshot
    save_state(
        home.state_path(),
        SupervisorSnapshot(
            state=SupervisorState.IDLE_IN_SESSION,
            last_rebalance_event=snapshot.last_rebalance_event,
            sleeves=dict(snapshot.sleeves),
            halt_reason=None,
        ),
    )

    halted_supervisor = _make_supervisor(home, broker)
    broker.raise_on_get_bars = True
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=5),
    )
    close_all_before_halt = broker.close_all_count
    halted_supervisor.tick()

    assert halted_supervisor.state == SupervisorState.HALTED
    assert broker.close_all_count == close_all_before_halt

    server = make_server(home, halted_supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/api/portfolio")
        response = conn.getresponse()
        portfolio = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        halt_signal = portfolio.get("halt_reason") or portfolio.get("deviation")
        assert halt_signal
    finally:
        server.shutdown()
        thread.join(timeout=2)

    kill_close_all_before = broker.close_all_count
    halted_supervisor.kill_account()
    assert broker.close_all_count == kill_close_all_before + 1

    events = _audit_event_types(home)
    for required in ("import", "rebalance", "halt", "flatten"):
        assert required in events

    audit_text = home.audit_path().read_text(encoding="utf-8")
    assert "PK_" not in audit_text
    assert "SK_" not in audit_text
    assert '"secret"' not in audit_text.lower()


def test_operator_desk_portfolio_after_rebalance(tmp_path: Path) -> None:
    home = AlphaStrategyHome(root=tmp_path)
    home.root.mkdir(parents=True, exist_ok=True)

    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    _setup_broker_bars(broker)

    bundle_id = import_asb(GOLDEN_ASB, home)
    supervisor = _make_supervisor(home, broker)
    supervisor.start_sleeve(bundle_id, 0.4)

    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()

    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/api/portfolio")
        response = conn.getresponse()
        portfolio = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert portfolio["sleeve_contribution"][bundle_id]["AAPL"] == 0.2
        assert portfolio["sleeve_contribution"][bundle_id]["MSFT"] == 0.2
        assert portfolio["last_combined"]["AAPL"] == 0.2
        assert portfolio["last_combined"]["MSFT"] == 0.2

        conn.request("GET", "/api/status")
        response = conn.getresponse()
        status = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert status["countdown"]["next_rebalance"] in ("open", "close")
        assert "seconds" in status["countdown"]
        assert status["last_rebalance_event"] == "2024-01-31:open"
        assert "utilization" in status
        assert "names" in status["utilization"]
        assert "orders_today" in status["utilization"]

        supervisor.stop_sleeve(bundle_id)

        conn.request("GET", "/api/bundles")
        response = conn.getresponse()
        bundles = json.loads(response.read().decode("utf-8"))
        assert bundle_id in bundles["stopped"]
        assert bundle_id not in bundles["paper"]

        conn.request("GET", "/api/portfolio")
        response = conn.getresponse()
        after_stop = json.loads(response.read().decode("utf-8"))
        assert after_stop["sleeve_contribution"] == portfolio["sleeve_contribution"]
        aapl = next(item for item in portfolio["positions"] if item["symbol"] == "AAPL")
        assert "wanted" in aapl
        assert "weight" in aapl
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_e2e_isolated_sleeve_kill(tmp_path: Path) -> None:
    home = AlphaStrategyHome(root=tmp_path)
    home.root.mkdir(parents=True, exist_ok=True)
    for bundle_id in ("asb_a", "asb_b"):
        home.bundle_dir(bundle_id).mkdir(parents=True)

    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.bars["AAPL"] = {"bars": [{"c": 100.0, "t": "2024-01-31"}]}
    broker.bars["MSFT"] = {"bars": [{"c": 100.0, "t": "2024-01-31"}]}

    supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={"asb_a": {"AAPL": 1.0}, "asb_b": {"MSFT": 1.0}},
    )
    supervisor.start_sleeve("asb_a", 0.15)
    supervisor.start_sleeve("asb_b", 0.15)
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()

    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
        payload = json.dumps({"bundle_id": "asb_a"}).encode("utf-8")
        conn.request(
            "POST",
            "/api/paper/kill",
            body=payload,
            headers={"Content-Type": "application/json", "Content-Length": str(len(payload))},
        )
        response = conn.getresponse()
        assert response.status == 200
        kill_body = json.loads(response.read().decode("utf-8"))
        assert kill_body["isolated"] is True
        assert kill_body["flattened"] is False
        assert kill_body["reason"] == "isolated"
        assert broker.close_all_count == 0
        assert supervisor.state != SupervisorState.STOPPED
        conn.request("GET", "/api/status")
        status = json.loads(conn.getresponse().read().decode("utf-8"))
        assert status["last_kill"]["reason"] == "isolated"
        conn.request("GET", "/")
        html = conn.getresponse().read().decode("utf-8")
        assert 'id="desk-banners"' in html
        assert 'id="kill-outcome-banner"' in html
        assert 'id="first-run"' in html
        assert 'id="metric-countdown"' in html
        assert 'id="metric-names"' in html
        assert 'id="metric-orders"' in html
        assert 'id="metric-cash-bar"' in html
        conn.request("GET", "/api/bundles")
        bundles = json.loads(conn.getresponse().read().decode("utf-8"))
        assert "asb_a" in bundles["stopped"]
        assert bundles["paper"]["asb_b"] == 0.15
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_e2e_account_flatten_sets_status_flattened(tmp_path: Path) -> None:
    home = AlphaStrategyHome(root=tmp_path)
    home.root.mkdir(parents=True, exist_ok=True)
    broker = FakeBroker()
    supervisor = Supervisor(
        home=home,
        broker=broker,
        policy=AccountPolicy.defaults(),
        evaluators={"asb_a": {"AAPL": 1.0}},
    )
    home.bundle_dir("asb_a").mkdir(parents=True)
    supervisor.kill_account()
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/api/status")
        status = json.loads(conn.getresponse().read().decode("utf-8"))
        assert status["flattened"] is True
        assert status["state"] == "stopped"
        conn.request("GET", "/")
        html = conn.getresponse().read().decode("utf-8")
        assert 'id="flatten-banner"' in html
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_control_plane_serves_help(tmp_path: Path) -> None:
    home = AlphaStrategyHome(root=tmp_path)
    home.root.mkdir(parents=True, exist_ok=True)
    broker = FakeBroker()
    supervisor = _make_supervisor(home, broker)
    server = make_server(home, supervisor, bind="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/api/help")
        help_resp = conn.getresponse()
        help_body = json.loads(help_resp.read().decode("utf-8"))
        assert help_resp.status == 200
        assert help_body["sections"][2]["id"] == "halt_flatten"
        assert help_body["howtos"][0]["id"] == "how_portfolio"
        conn.request("GET", "/")
        html_resp = conn.getresponse()
        html = html_resp.read().decode("utf-8")
        assert html_resp.status == 200
        assert 'id="help-toggle"' in html
        assert 'id="import-error-kind"' in html
        assert 'id="desk-pulse"' in html
        assert 'id="glance-book"' in html
        assert 'id="run-flatten"' in html
        assert 'id="strat-inventory"' in html
        assert 'id="risk-tighten"' in html
        assert 'id="act-tape"' in html
        conn.request("GET", "/app.js")
        js_resp = conn.getresponse()
        js_body = js_resp.read().decode("utf-8")
        assert js_resp.status == 200
        assert "function bookTable" in js_body
        assert "JSON.stringify(payload" not in js_body
        conn.request("GET", "/api/risk")
        risk_resp = conn.getresponse()
        risk_body = json.loads(risk_resp.read().decode("utf-8"))
        assert risk_resp.status == 200
        assert risk_body["labels"]["max_gross"] == "Gross cap"
    finally:
        server.shutdown()
        thread.join(timeout=2)
