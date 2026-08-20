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
    finally:
        server.shutdown()
        thread.join(timeout=2)
