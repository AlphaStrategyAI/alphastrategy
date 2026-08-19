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


def test_rebalance_skips_execution_deviation_for_unfilled_order(tmp_path: Path):
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
    assert not any(event["event"] == "execution_deviation" for event in events)


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


def test_kill_sleeve_calls_close_all_once(tmp_path: Path):
    broker = FakeBroker(is_open=True)
    broker.positions["AAPL"] = 10.0
    supervisor = _make_supervisor(tmp_path, broker)
    supervisor.start_sleeve("asb_test", 0.15)

    supervisor.kill_sleeve("asb_test")

    assert broker.close_all_count == 1
    assert supervisor.state == SupervisorState.STOPPED


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
