from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from dataclasses import replace

import pytest

from alphastrategy.home import AlphaStrategyHome
from alphastrategy.risk.policy import AccountPolicy
from alphastrategy.supervisor.loop import Supervisor
from alphastrategy.supervisor.state import SupervisorState


class SimulatedCrash(BaseException):
    """Host kill mid-tick: not `Exception`, so `tick` except-handlers do not convert it to halt."""


class FakeBroker:
    def __init__(
        self,
        *,
        equity: float = 10_000.0,
        is_open: bool = False,
        next_open: datetime | None = None,
        next_close: datetime | None = None,
        now: datetime | None = None,
    ) -> None:
        self.equity = equity
        self.positions: dict[str, float] = {}
        self.orders: list[tuple[str, float, str]] = []
        self.close_all_called = False
        self.close_all_count = 0
        self.cancel_open_orders_count = 0
        self.operations: list[str] = []
        self.fill_orders = True
        self.fill_fraction = 1.0
        self.raise_on_get_bars = False
        self.raise_on_get_clock = False
        self.fail_place_after = None
        self.crash_after_place = None
        self.crash_on_close_all = False
        self._next_open = next_open or datetime(2024, 1, 31, 14, 30)
        self._next_close = next_close or datetime(2024, 1, 31, 21, 0)
        self._now = now or self._next_open
        self._is_open = is_open
        self.bars: dict = {}

    def _iso(self, dt: datetime) -> str:
        return dt.isoformat()

    def set_session_open(
        self,
        *,
        open_time: datetime,
        session_close: datetime,
        now: datetime,
    ) -> None:
        self._next_open = open_time
        self._next_close = session_close
        self._now = now
        self._is_open = True

    def get_account(self) -> dict:
        return {"equity": str(self.equity), "cash": str(self.equity)}

    def list_positions(self) -> list[dict]:
        return [{"symbol": symbol, "qty": str(qty)} for symbol, qty in self.positions.items()]

    def place_order(self, symbol: str, qty: float, side: str) -> dict:
        if self.fail_place_after is not None and len(self.orders) >= self.fail_place_after:
            raise RuntimeError("broker place_order failed")
        if self.crash_after_place is not None and len(self.orders) >= self.crash_after_place:
            raise SimulatedCrash("host killed during place_order")
        self.orders.append((symbol, qty, side))
        if self.fill_orders:
            filled_qty = qty * self.fill_fraction
            delta = filled_qty if side == "buy" else -filled_qty
            self.positions[symbol] = self.positions.get(symbol, 0.0) + delta
        status = "filled" if self.fill_orders else "accepted"
        return {"id": f"order-{len(self.orders)}", "status": status}

    def cancel_order(self, order_id: str) -> None:
        return None

    def cancel_open_orders(self) -> None:
        self.cancel_open_orders_count += 1
        self.operations.append("cancel_open_orders")

    def close_all(self) -> None:
        if self.crash_on_close_all:
            raise SimulatedCrash("host killed during close_all")
        self.close_all_called = True
        self.close_all_count += 1
        self.operations.append("close_all")
        self.positions = {}

    def get_clock(self) -> dict:
        if self.raise_on_get_clock:
            raise RuntimeError("clock unavailable")
        return {
            "is_open": self._is_open,
            "next_open": self._iso(self._next_open),
            "next_close": self._iso(self._next_close),
            "timestamp": self._iso(self._now),
        }

    def advance_now(self, now: datetime) -> None:
        self._now = now

    def get_bars(self, symbols: list[str], start: str, end: str) -> dict:
        if self.raise_on_get_bars:
            raise RuntimeError("bars unavailable")
        out: dict = {}
        for symbol in symbols:
            if symbol in self.bars:
                out[symbol] = self.bars[symbol]
            else:
                out[symbol] = {"bars": [{"c": 100.0}]}
        return out


def _make_supervisor(
    tmp_path: Path,
    broker: FakeBroker,
    *,
    evaluators: dict[str, dict[str, float]] | None = None,
    policy: AccountPolicy | None = None,
) -> Supervisor:
    home = AlphaStrategyHome(root=tmp_path)
    for bundle_id in (evaluators or {"asb_test": {"AAPL": 1.0}}):
        home.bundle_dir(bundle_id).mkdir(parents=True, exist_ok=True)
    return Supervisor(
        home=home,
        broker=broker,
        policy=policy or AccountPolicy.defaults(),
        evaluators=evaluators or {"asb_test": {"AAPL": 1.0}},
    )


def _read_state(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "supervisor-state.json").read_text(encoding="utf-8"))


def test_open_rebalance_places_orders_and_sets_last_event(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(is_open=False, next_open=open_time, next_close=session_close, now=open_time)
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()

    assert broker.orders
    assert len(broker.orders) >= 1
    state = _read_state(tmp_path)
    assert state["last_rebalance_event"] == "2024-01-31:open"
    assert state["last_rebalance_complete"] is True


def test_second_tick_same_session_places_no_orders(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(is_open=False, next_open=open_time, next_close=session_close, now=open_time)
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()
    first_batch = list(broker.orders)
    assert first_batch

    broker.advance_now(open_time + timedelta(minutes=10))
    supervisor.tick()

    assert broker.orders == first_batch


def test_get_bars_failure_halts_without_flatten(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(is_open=False, next_open=open_time, next_close=session_close, now=open_time)
    broker.raise_on_get_bars = True
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()

    assert supervisor.state == SupervisorState.HALTED
    assert broker.close_all_called is False
    assert broker.orders == []


def test_resume_after_failed_open_does_not_catch_up_same_session(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.raise_on_get_bars = True
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )

    supervisor.tick()
    assert supervisor.state == SupervisorState.HALTED
    assert broker.orders == []

    broker.raise_on_get_bars = False
    supervisor.resume()
    supervisor.tick()

    assert broker.orders == []
    assert supervisor.last_rebalance_event == "2024-01-31:open"


def test_kill_account_calls_close_all_and_stops(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    broker.positions["AAPL"] = 10.0
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    supervisor.kill_account()

    assert broker.close_all_called is True
    assert supervisor.state in (SupervisorState.STOPPED, SupervisorState.IDLE_IN_SESSION)


def test_flatten_cancels_open_orders_before_closing_positions(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    broker.positions["AAPL"] = 10.0
    supervisor = _make_supervisor(tmp_path, broker)

    supervisor.kill_account()

    assert broker.operations == ["cancel_open_orders", "close_all"]


def test_resume_after_halt_does_not_place_orders_until_next_event(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(is_open=False, next_open=open_time, next_close=session_close, now=open_time)
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()
    assert broker.orders

    broker.raise_on_get_bars = True
    broker.advance_now(open_time + timedelta(minutes=10))
    supervisor.tick()
    assert supervisor.state == SupervisorState.HALTED

    broker.raise_on_get_bars = False
    supervisor.resume()
    orders_after_open = list(broker.orders)

    broker.advance_now(open_time + timedelta(minutes=15))
    supervisor.tick()

    assert broker.orders == orders_after_open


def test_start_sleeve_rejects_allocation_over_one(tmp_path: Path):
    broker = FakeBroker()
    supervisor = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_a": {"AAPL": 1.0}, "asb_b": {"AAPL": 1.0}},
    )
    supervisor.start_sleeve("asb_a", 0.7)
    with pytest.raises(ValueError):
        supervisor.start_sleeve("asb_b", 0.4)


@pytest.mark.parametrize("allocation", [-0.1, 1.1, float("nan"), float("inf")])
def test_start_sleeve_rejects_invalid_allocation(tmp_path: Path, allocation: float):
    supervisor = _make_supervisor(tmp_path, FakeBroker())

    with pytest.raises(ValueError):
        supervisor.start_sleeve("asb_test", allocation)


def test_start_sleeve_requires_imported_bundle(tmp_path: Path):
    supervisor = _make_supervisor(tmp_path, FakeBroker())

    with pytest.raises(ValueError, match="not imported"):
        supervisor.start_sleeve("asb_missing", 0.1)


def _trigger_open_rebalance(
    tmp_path: Path,
    broker: FakeBroker,
    supervisor: Supervisor,
) -> None:
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()


def test_limit_breach_flattens_account(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(is_open=False, next_open=open_time, next_close=session_close, now=open_time)
    policy = replace(AccountPolicy.defaults(), max_gross=0.5)
    supervisor = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 1.0}},
        policy=policy,
    )
    supervisor.start_sleeve("asb_test", 1.0)

    _trigger_open_rebalance(tmp_path, broker, supervisor)

    assert broker.close_all_called is True
    assert broker.close_all_count == 1
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.orders == []
    assert supervisor.snapshot.last_kill is not None
    assert supervisor.snapshot.last_kill["reason"] == "max_gross"
    assert supervisor.snapshot.last_kill["flattened"] is True
    assert supervisor.snapshot.last_kill["scope"] == "account"
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    flattens = [ev for ev in events if ev.get("event") == "flatten"]
    assert flattens[-1]["reason"] == "max_gross"


def test_residual_cash_weights_do_not_halt(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(is_open=False, next_open=open_time, next_close=session_close, now=open_time)
    supervisor = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 0.4}},
    )
    supervisor.start_sleeve("asb_test", 0.15)

    _trigger_open_rebalance(tmp_path, broker, supervisor)

    assert supervisor.state == SupervisorState.IDLE_IN_SESSION
    assert broker.close_all_called is False
    assert broker.orders == [("AAPL", 6, "buy")]


def test_stopping_last_sleeve_sells_existing_positions_at_next_rebalance(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.positions["AAPL"] = 10.0
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    supervisor.stop_sleeve("asb_test")

    _trigger_open_rebalance(tmp_path, broker, supervisor)

    assert broker.orders == [("AAPL", 10, "sell")]
    assert broker.positions["AAPL"] == 0.0


def test_stale_bars_halt_without_flatten(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.bars["AAPL"] = {"bars": [{"c": 100.0, "t": "2024-01-20T21:00:00Z"}]}
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    _trigger_open_rebalance(tmp_path, broker, supervisor)

    assert supervisor.state == SupervisorState.HALTED
    assert "stale" in (supervisor.snapshot.halt_reason or "")
    assert broker.close_all_called is False
    assert broker.orders == []


def test_unexpected_open_session_halts_without_flatten(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 23, 0)
    broker = FakeBroker(
        is_open=True,
        next_open=open_time,
        next_close=session_close,
        now=datetime(2024, 1, 31, 22, 0),
    )
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    supervisor.tick()

    assert supervisor.state == SupervisorState.HALTED
    assert "unexpected open session" in (supervisor.snapshot.halt_reason or "")
    assert broker.close_all_called is False
    assert broker.orders == []


def test_rebalance_audits_execution_deviation_after_partial_immediate_fill(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.fill_fraction = 0.5
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    _trigger_open_rebalance(tmp_path, broker, supervisor)

    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    deviations = [event for event in events if event["event"] == "execution_deviation"]
    assert deviations == [
        {
            "event": "execution_deviation",
            "asset": "AAPL",
            "wanted": 0.15,
            "got": 0.075,
            "ts": deviations[0]["ts"],
        }
    ]


def test_rebalance_audits_execution_deviation_for_unfilled_order(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.fill_orders = False
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    _trigger_open_rebalance(tmp_path, broker, supervisor)

    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    deviations = [event for event in events if event["event"] == "execution_deviation"]
    assert deviations
    assert deviations[0]["asset"] == "AAPL"
    assert deviations[0]["wanted"] == 0.15
    assert deviations[0]["got"] == 0.0


def test_get_clock_failure_halts_without_flatten(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    broker.raise_on_get_clock = True
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    supervisor.tick()

    assert supervisor.state == SupervisorState.HALTED
    assert broker.close_all_called is False
    assert broker.orders == []


def test_resume_after_get_clock_halt_does_not_catch_up_open(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=True,
        next_open=open_time,
        next_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    broker.raise_on_get_clock = True
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    supervisor.tick()
    assert supervisor.state == SupervisorState.HALTED
    assert broker.orders == []

    broker.raise_on_get_clock = False
    supervisor.resume()
    supervisor.tick()

    assert supervisor.state == SupervisorState.IDLE_IN_SESSION
    assert broker.orders == []


def test_resume_suppression_survives_supervisor_restart(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=True,
        next_open=open_time,
        next_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    broker.raise_on_get_clock = True
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    supervisor.tick()
    assert supervisor.state == SupervisorState.HALTED

    broker.raise_on_get_clock = False
    supervisor.resume()
    assert _read_state(tmp_path)["prime_clock_after_resume"] is True

    restarted = _make_supervisor(tmp_path, broker)
    restarted.tick()

    assert restarted.state == SupervisorState.IDLE_IN_SESSION
    assert broker.orders == []
    assert _read_state(tmp_path)["prime_clock_after_resume"] is False


def test_kill_sleeve_calls_close_all_once(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    broker.positions["AAPL"] = 10.0
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    supervisor.kill_sleeve("asb_test")

    assert broker.close_all_count == 1
    assert supervisor.state == SupervisorState.STOPPED


def test_kill_sleeve_isolates_when_last_book_exists(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    evaluators = {"asb_a": {"AAPL": 1.0}, "asb_b": {"MSFT": 1.0}}
    supervisor = _make_supervisor(tmp_path, broker, evaluators=evaluators)
    supervisor.start_sleeve("asb_a", 0.15)
    supervisor.start_sleeve("asb_b", 0.15)
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()
    assert "AAPL" in broker.positions
    assert "MSFT" in broker.positions
    close_all_before = broker.close_all_count
    supervisor.kill_sleeve("asb_a")
    assert broker.close_all_count == close_all_before
    assert supervisor.state != SupervisorState.STOPPED
    assert supervisor.snapshot.sleeves["asb_a"] == 0.0
    assert supervisor.snapshot.sleeves["asb_b"] == 0.15
    assert broker.positions.get("AAPL", 0.0) == 0.0
    assert broker.positions.get("MSFT", 0.0) > 0
    assert "asb_a" in supervisor.snapshot.stopped


def test_restart_during_sleeve_isolate_flattens_account(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    evaluators = {
        "asb_a": {"AAPL": 0.5, "MSFT": 0.5},
        "asb_b": {"GOOG": 1.0},
    }
    supervisor = _make_supervisor(tmp_path, broker, evaluators=evaluators)
    supervisor.start_sleeve("asb_a", 0.15)
    supervisor.start_sleeve("asb_b", 0.15)
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()
    assert "GOOG" in broker.positions
    broker.crash_after_place = len(broker.orders) + 1
    with pytest.raises(SimulatedCrash):
        supervisor.kill_sleeve("asb_a")
    inflight = _read_state(tmp_path)
    assert inflight["isolate_in_flight"] == "asb_a"
    assert inflight["state"] != "stopped"
    assert broker.close_all_called is False
    broker.crash_after_place = None
    restarted = _make_supervisor(tmp_path, broker, evaluators=evaluators)
    assert restarted.state == SupervisorState.STOPPED
    assert broker.close_all_called is True
    assert broker.positions == {}
    assert restarted.snapshot.isolate_in_flight is None
    assert restarted.snapshot.last_kill["reason"] == "fallback_interrupted"
    assert restarted.snapshot.last_kill["flattened"] is True
    assert restarted.snapshot.sleeves.get("asb_b", 0) == 0.0
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    kills = [event for event in events if event["event"] == "kill"]
    assert kills
    assert kills[-1]["reason"] == "fallback_interrupted"


def test_sleeve_overlay_tightens_rebalance_policy(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    policy = replace(AccountPolicy.defaults(), max_name_weight=1.0)
    supervisor = _make_supervisor(tmp_path, broker, policy=policy)
    home = AlphaStrategyHome(root=tmp_path)
    bundle_dir = home.imported_dir() / "asb_test"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "risk-envelope.yaml").write_text("max_name_weight: 1.0\n", encoding="utf-8")
    home.runtime_path().write_text(
        yaml.safe_dump({"sleeve_overlays": {"asb_test": {"max_name_weight": 0.10}}}),
        encoding="utf-8",
    )

    supervisor.start_sleeve("asb_test", 1.0)
    _trigger_open_rebalance(tmp_path, broker, supervisor)

    assert broker.close_all_called is True
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.orders == []


def test_stop_sleeve_is_listed_as_stopped(tmp_path: Path):
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    supervisor.start_sleeve("asb_test", 0.4)
    supervisor.stop_sleeve("asb_test")
    assert "asb_test" in supervisor.snapshot.stopped
    assert supervisor.snapshot.sleeves["asb_test"] == 0.0


def test_start_sleeve_clears_stopped(tmp_path: Path):
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    supervisor.start_sleeve("asb_test", 0.4)
    supervisor.stop_sleeve("asb_test")
    supervisor.start_sleeve("asb_test", 0.2)
    assert "asb_test" not in supervisor.snapshot.stopped
    assert supervisor.snapshot.sleeves["asb_test"] == 0.2


def test_rebalance_persists_contribution_and_stop_does_not_zero_it(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.bars["AAPL"] = {"bars": [{"c": 100.0, "t": "2024-01-31"}]}
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()
    assert supervisor.snapshot.last_combined == {"AAPL": 0.15}
    assert supervisor.snapshot.last_sleeve_contribution["asb_test"]["AAPL"] == pytest.approx(0.15)
    assert supervisor.snapshot.last_prices["AAPL"] == pytest.approx(100.0)
    supervisor.stop_sleeve("asb_test")
    assert supervisor.snapshot.last_sleeve_contribution["asb_test"]["AAPL"] == pytest.approx(0.15)


def test_rebalance_counts_orders_today_and_audits_wanted_got(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    _trigger_open_rebalance(tmp_path, broker, supervisor)
    assert supervisor.snapshot.orders_today == len(broker.orders)
    assert supervisor.snapshot.orders_date == "2024-01-31"
    assert "AAPL" in supervisor.snapshot.last_got
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rebalances = [event for event in events if event["event"] == "rebalance"]
    assert rebalances
    assert "wanted" in rebalances[-1]
    assert "got" in rebalances[-1]


def test_rebalance_partial_place_order_failure_halts_without_flatten(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.fail_place_after = 1
    supervisor = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 0.5, "MSFT": 0.5}},
    )
    supervisor.start_sleeve("asb_test", 0.4)
    _trigger_open_rebalance(tmp_path, broker, supervisor)

    assert supervisor.state == SupervisorState.HALTED
    assert broker.close_all_called is False
    assert len(broker.orders) == 1
    assert supervisor.snapshot.orders_today == 1
    assert supervisor.snapshot.last_rebalance_event == "2024-01-31:open"
    assert supervisor.snapshot.last_got
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rebalances = [event for event in events if event["event"] == "rebalance"]
    assert rebalances
    assert rebalances[-1]["complete"] is False
    assert rebalances[-1]["orders"] == 1
    assert "wanted" in rebalances[-1]
    assert "got" in rebalances[-1]
    assert any(event["event"] == "execution_deviation" for event in events)
    first = list(broker.orders)
    broker.advance_now(open_time + timedelta(minutes=10))
    supervisor.tick()
    assert broker.orders == first
    assert supervisor.state == SupervisorState.HALTED


def test_rebalance_persists_inflight_before_first_place(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)

    class ProbeBroker(FakeBroker):
        def place_order(self, symbol: str, qty: float, side: str) -> dict:
            if not self.orders:
                self.before_first = _read_state(tmp_path)
            return super().place_order(symbol, qty, side)

    broker = ProbeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    supervisor = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 0.5, "MSFT": 0.5}},
    )
    supervisor.start_sleeve("asb_test", 0.4)
    _trigger_open_rebalance(tmp_path, broker, supervisor)

    assert broker.before_first["state"] == "rebalancing"
    assert broker.before_first["last_rebalance_event"] == "2024-01-31:open"
    assert broker.before_first["orders_today"] == 0
    assert broker.before_first.get("rebalance_placed", 0) == 0
    assert broker.before_first["last_rebalance_complete"] is False
    finished = _read_state(tmp_path)
    assert finished["state"] == "idle_in_session"
    assert finished["last_rebalance_event"] == "2024-01-31:open"
    assert finished["last_rebalance_complete"] is True
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rebalances = [event for event in events if event["event"] == "rebalance"]
    assert rebalances[-1]["complete"] is True


def test_restart_during_rebalancing_halts_without_duplicate_orders(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.crash_after_place = 1
    supervisor = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 0.5, "MSFT": 0.5}},
    )
    supervisor.start_sleeve("asb_test", 0.4)
    with pytest.raises(SimulatedCrash):
        _trigger_open_rebalance(tmp_path, broker, supervisor)

    inflight = _read_state(tmp_path)
    assert inflight["state"] == "rebalancing"
    assert inflight["last_rebalance_event"] == "2024-01-31:open"
    assert inflight["orders_today"] == 1
    assert len(broker.orders) == 1

    restarted = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 0.5, "MSFT": 0.5}},
    )
    assert restarted.state == SupervisorState.HALTED
    assert broker.close_all_called is False
    assert restarted.snapshot.orders_today == 1
    assert restarted.snapshot.last_rebalance_event == "2024-01-31:open"
    assert restarted.snapshot.last_got
    assert restarted.snapshot.last_rebalance_complete is False
    assert "interrupted rebalancing" in (restarted.snapshot.halt_reason or "").lower()
    assert "2024-01-31:open spent" in (restarted.snapshot.halt_reason or "").lower()
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rebalances = [event for event in events if event["event"] == "rebalance"]
    assert rebalances
    assert rebalances[-1]["complete"] is False
    assert rebalances[-1]["orders"] == 1
    assert "wanted" in rebalances[-1]
    assert "got" in rebalances[-1]
    first = list(broker.orders)
    broker.advance_now(open_time + timedelta(minutes=10))
    restarted.tick()
    assert broker.orders == first
    assert restarted.state == SupervisorState.HALTED
    assert broker.close_all_called is False


def test_restart_before_first_fill_spends_session_window(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    broker.crash_after_place = 0
    supervisor = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 0.5, "MSFT": 0.5}},
    )
    supervisor.start_sleeve("asb_test", 0.4)
    with pytest.raises(SimulatedCrash):
        _trigger_open_rebalance(tmp_path, broker, supervisor)

    inflight = _read_state(tmp_path)
    assert inflight["state"] == "rebalancing"
    assert inflight["last_rebalance_event"] == "2024-01-31:open"
    assert inflight["rebalance_placed"] == 0
    assert inflight["last_rebalance_complete"] is False
    assert inflight["orders_today"] == 0
    assert broker.orders == []

    restarted = _make_supervisor(
        tmp_path,
        broker,
        evaluators={"asb_test": {"AAPL": 0.5, "MSFT": 0.5}},
    )
    reason = (restarted.snapshot.halt_reason or "").lower()
    assert restarted.state == SupervisorState.HALTED
    assert broker.close_all_called is False
    assert restarted.snapshot.rebalance_placed == 0
    assert restarted.snapshot.last_rebalance_event == "2024-01-31:open"
    assert restarted.snapshot.last_rebalance_complete is False
    assert "interrupted rebalancing" in reason
    assert "2024-01-31:open spent" in reason
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    rebalances = [event for event in events if event["event"] == "rebalance"]
    assert rebalances[-1]["complete"] is False
    assert rebalances[-1]["orders"] == 0
    first = list(broker.orders)
    broker.advance_now(open_time + timedelta(minutes=10))
    restarted.tick()
    assert broker.orders == first
    restarted.resume()
    broker.advance_now(open_time + timedelta(minutes=11))
    restarted.tick()
    assert broker.orders == first
    assert restarted.snapshot.last_rebalance_event == "2024-01-31:open"
    assert restarted.snapshot.last_rebalance_complete is False


def test_daily_order_budget_flattens_without_overflow_batch(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    policy = replace(AccountPolicy.defaults(), max_orders_per_day=0)
    supervisor = _make_supervisor(tmp_path, broker, policy=policy)
    supervisor.start_sleeve("asb_test", 0.15)
    _trigger_open_rebalance(tmp_path, broker, supervisor)
    assert broker.close_all_called is True
    assert supervisor.state == SupervisorState.STOPPED
    assert broker.orders == []


def test_kill_sleeve_returns_isolated_outcome(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=False,
        next_open=open_time,
        next_close=session_close,
        now=open_time,
    )
    evaluators = {"asb_a": {"AAPL": 1.0}, "asb_b": {"MSFT": 1.0}}
    supervisor = _make_supervisor(tmp_path, broker, evaluators=evaluators)
    supervisor.start_sleeve("asb_a", 0.15)
    supervisor.start_sleeve("asb_b", 0.15)
    broker.set_session_open(
        open_time=open_time,
        session_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor.tick()
    outcome = supervisor.kill_sleeve("asb_a")
    assert outcome.isolated is True
    assert outcome.flattened is False
    assert outcome.scope == "sleeve"
    assert outcome.reason == "isolated"
    assert outcome.bundle_id == "asb_a"
    assert supervisor.snapshot.last_kill["isolated"] is True
    assert supervisor.snapshot.last_kill["reason"] == "isolated"


def test_kill_sleeve_returns_fallback_outcome_when_not_ready(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    broker.positions["AAPL"] = 10.0
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    outcome = supervisor.kill_sleeve("asb_test")
    assert outcome.isolated is False
    assert outcome.flattened is True
    assert outcome.scope == "account"
    assert outcome.reason == "fallback_not_ready"
    assert supervisor.snapshot.last_kill["flattened"] is True


def test_kill_sleeve_unknown_bundle_does_not_flatten(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    supervisor = _make_supervisor(tmp_path, broker)
    outcome = supervisor.kill_sleeve("missing")
    assert outcome.scope == "none"
    assert outcome.reason == "unknown_sleeve"
    assert outcome.flattened is False
    assert broker.close_all_count == 0
    assert supervisor.snapshot.last_kill["reason"] == "unknown_sleeve"


def test_kill_account_returns_account_outcome(tmp_path: Path):
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    outcome = supervisor.kill_account()
    assert outcome.isolated is False
    assert outcome.flattened is True
    assert outcome.scope == "account"
    assert outcome.reason == "account"
    assert outcome.bundle_id is None


def test_flatten_clears_last_book_and_zeros_sleeves(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    broker.positions["AAPL"] = 10.0
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    supervisor.snapshot.last_combined = {"AAPL": 0.15}
    supervisor.snapshot.last_got = {"AAPL": 0.10}
    supervisor.kill_account()
    snap = supervisor.snapshot
    assert snap.state == SupervisorState.STOPPED
    assert snap.last_combined == {}
    assert snap.last_got == {}
    assert snap.last_sleeve_weights == {}
    assert snap.last_sleeve_contribution == {}
    assert snap.last_prices == {}
    assert snap.sleeves.get("asb_test", 0) == 0.0
    assert "asb_test" in snap.stopped


def test_restart_during_flattening_finishes_flatten(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    broker.positions["AAPL"] = 10.0
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    supervisor.snapshot.last_combined = {"AAPL": 0.15}
    supervisor.snapshot.last_got = {"AAPL": 0.10}
    supervisor._snapshot.state = SupervisorState.FLATTENING
    supervisor._persist()

    restarted = _make_supervisor(tmp_path, broker)
    assert restarted.state == SupervisorState.STOPPED
    assert broker.close_all_called is True
    assert broker.positions == {}
    assert restarted.snapshot.last_combined == {}
    assert restarted.snapshot.last_got == {}
    assert restarted.snapshot.sleeves.get("asb_test", 0) == 0.0
    assert "asb_test" in restarted.snapshot.stopped
    events = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert any(event["event"] == "flatten" for event in events)
    assert restarted.snapshot.last_kill["reason"] == "flatten_interrupted"
    flattens = [event for event in events if event["event"] == "flatten"]
    assert flattens[-1]["reason"] == "flatten_interrupted"


def test_kill_account_host_crash_then_restart_finishes_flatten(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    broker.positions["AAPL"] = 10.0
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    broker.crash_on_close_all = True
    with pytest.raises(SimulatedCrash):
        supervisor.kill_account()
    inflight = _read_state(tmp_path)
    assert inflight["state"] == "flattening"
    assert broker.positions.get("AAPL", 0.0) == 10.0
    broker.crash_on_close_all = False
    restarted = _make_supervisor(tmp_path, broker)
    assert restarted.state == SupervisorState.STOPPED
    assert broker.close_all_called is True
    assert broker.positions == {}
    assert broker.close_all_count == 1


def test_start_sleeve_after_flatten_leaves_stopped_without_catchup(tmp_path: Path):
    open_time = datetime(2024, 1, 31, 14, 30)
    session_close = datetime(2024, 1, 31, 21, 0)
    broker = FakeBroker(
        is_open=True,
        next_open=open_time,
        next_close=session_close,
        now=open_time + timedelta(minutes=3),
    )
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)
    supervisor.kill_account()
    assert supervisor.state == SupervisorState.STOPPED
    orders_after_kill = list(broker.orders)
    supervisor.start_sleeve("asb_test", 0.15)
    assert supervisor.state == SupervisorState.IDLE_IN_SESSION
    supervisor.tick()
    assert broker.orders == orders_after_kill


def test_tick_stamps_heartbeat_when_halted(tmp_path: Path) -> None:
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    supervisor._snapshot.state = SupervisorState.HALTED
    supervisor._persist()
    supervisor.tick()
    assert supervisor.snapshot.last_heartbeat_at
    state = _read_state(tmp_path)
    assert state["last_heartbeat_at"] == supervisor.snapshot.last_heartbeat_at


def test_tick_stamps_heartbeat_when_stopped(tmp_path: Path) -> None:
    supervisor = _make_supervisor(tmp_path, FakeBroker())
    supervisor._snapshot.state = SupervisorState.STOPPED
    supervisor._persist()
    first = None
    supervisor.tick()
    first = supervisor.snapshot.last_heartbeat_at
    supervisor.tick()
    assert supervisor.snapshot.last_heartbeat_at
    assert supervisor.snapshot.last_heartbeat_at >= first
