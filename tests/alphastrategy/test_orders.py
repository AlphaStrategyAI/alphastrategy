from __future__ import annotations

from dataclasses import replace

import pytest

from alphastrategy.errors import FlattenRequested
from alphastrategy.risk.policy import AccountPolicy
from alphastrategy.supervisor.orders import OrderPlan, deviations_after, plan_orders


class FakeBroker:
    def __init__(self) -> None:
        self.orders: list[tuple[str, float, str]] = []

    def place_order(self, symbol: str, qty: float, side: str) -> dict:
        self.orders.append((symbol, qty, side))
        return {"id": f"order-{len(self.orders)}", "status": "filled"}


def test_plan_orders_buy_to_target():
    combined = {"AAPL": 0.15}
    positions = {}
    prices = {"AAPL": 100.0}
    equity = 10_000.0
    policy = AccountPolicy.defaults()

    plans = plan_orders(combined, positions, prices, equity, policy)

    assert plans == [OrderPlan(symbol="AAPL", qty=15, side="buy")]


def test_plan_orders_sell_to_target():
    combined = {"AAPL": 0.10}
    positions = {"AAPL": 20}
    prices = {"AAPL": 100.0}
    equity = 10_000.0
    policy = AccountPolicy.defaults()

    plans = plan_orders(combined, positions, prices, equity, policy)

    assert plans == [OrderPlan(symbol="AAPL", qty=10, side="sell")]


def test_plan_orders_skips_below_min_delta():
    combined = {"AAPL": 0.10001}
    positions = {"AAPL": 10}
    prices = {"AAPL": 100.0}
    equity = 10_000.0
    policy = AccountPolicy.defaults()

    plans = plan_orders(combined, positions, prices, equity, policy)

    assert plans == []


def test_plan_orders_floors_to_whole_shares():
    combined = {"AAPL": 0.15}
    positions = {}
    prices = {"AAPL": 150.0}
    equity = 10_000.0
    policy = AccountPolicy.defaults()

    plans = plan_orders(combined, positions, prices, equity, policy)

    assert plans == [OrderPlan(symbol="AAPL", qty=10, side="buy")]


def test_plan_orders_missing_position_is_zero():
    combined = {"AAPL": 0.15}
    positions = {}
    prices = {"AAPL": 100.0}
    equity = 10_000.0
    policy = AccountPolicy.defaults()

    plans = plan_orders(combined, positions, prices, equity, policy)

    assert plans == [OrderPlan(symbol="AAPL", qty=15, side="buy")]


def test_plan_orders_skips_assets_with_missing_prices():
    combined = {"AAPL": 0.10, "MSFT": 0.10}
    positions = {}
    prices = {"AAPL": 100.0}
    equity = 10_000.0
    policy = AccountPolicy.defaults()

    plans = plan_orders(combined, positions, prices, equity, policy)

    assert plans == [OrderPlan(symbol="AAPL", qty=10, side="buy")]


def test_plan_orders_residual_cash_is_not_an_order():
    combined = {"AAPL": 0.10}
    positions = {}
    prices = {"AAPL": 100.0}
    equity = 10_000.0
    policy = AccountPolicy.defaults()

    plans = plan_orders(combined, positions, prices, equity, policy)

    assert plans == [OrderPlan(symbol="AAPL", qty=10, side="buy")]


def test_plan_orders_sells_position_not_in_combined():
    combined = {}
    positions = {"AAPL": 10}
    prices = {"AAPL": 100.0}
    equity = 10_000.0
    policy = AccountPolicy.defaults()

    plans = plan_orders(combined, positions, prices, equity, policy)

    assert plans == [OrderPlan(symbol="AAPL", qty=10, side="sell")]


def test_plan_orders_raises_flatten_on_order_notional_breach():
    combined = {"AAPL": 0.15}
    positions = {}
    prices = {"AAPL": 100.0}
    equity = 10_000.0
    policy = replace(AccountPolicy.defaults(), max_order_notional_frac=0.10)

    with pytest.raises(FlattenRequested) as exc:
        plan_orders(combined, positions, prices, equity, policy)
    assert exc.value.scope == "account"


def test_plan_orders_raises_flatten_on_order_count_breach():
    combined = {f"S{i}": 0.01 for i in range(5)}
    positions = {}
    prices = {f"S{i}": 10.0 for i in range(5)}
    equity = 10_000.0
    policy = replace(AccountPolicy.defaults(), max_orders_per_rebalance=3)

    with pytest.raises(FlattenRequested) as exc:
        plan_orders(combined, positions, prices, equity, policy)
    assert exc.value.scope == "account"


def test_fake_broker_captures_place_order_calls():
    combined = {"AAPL": 0.10, "MSFT": 0.10}
    positions = {"MSFT": 5}
    prices = {"AAPL": 100.0, "MSFT": 50.0}
    equity = 10_000.0
    policy = AccountPolicy.defaults()
    broker = FakeBroker()

    plans = plan_orders(combined, positions, prices, equity, policy)
    for plan in plans:
        broker.place_order(plan.symbol, plan.qty, plan.side)

    assert broker.orders == [
        ("AAPL", 10, "buy"),
        ("MSFT", 15, "buy"),
    ]


def test_deviations_after_empty_when_within_min_delta():
    wanted = {"AAPL": 0.10}
    got = {"AAPL": 0.0999}
    equity = 10_000.0
    prices = {"AAPL": 100.0}

    assert deviations_after(wanted, got, equity, prices) == []


def test_deviations_after_reports_weight_gap():
    wanted = {"AAPL": 0.15}
    got = {"AAPL": 0.10}
    equity = 10_000.0
    prices = {"AAPL": 100.0}

    deviations = deviations_after(wanted, got, equity, prices)

    assert deviations == [{"asset": "AAPL", "wanted": 0.15, "got": 0.10}]


def test_deviations_after_skips_assets_with_missing_prices():
    wanted = {"AAPL": 0.15, "MSFT": 0.15}
    got = {"AAPL": 0.10, "MSFT": 0.05}
    equity = 10_000.0
    prices = {"AAPL": 100.0}

    deviations = deviations_after(wanted, got, equity, prices)

    assert deviations == [{"asset": "AAPL", "wanted": 0.15, "got": 0.10}]
