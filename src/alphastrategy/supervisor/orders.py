from __future__ import annotations

import math
from dataclasses import dataclass

from alphastrategy.errors import FlattenRequested
from alphastrategy.risk.policy import AccountPolicy


@dataclass(frozen=True)
class OrderPlan:
    symbol: str
    qty: int
    side: str


def _position_qty(positions: dict[str, float], symbol: str) -> float:
    return positions.get(symbol, 0.0)


def _target_qty(weight: float, equity: float, price: float) -> int:
    return math.floor((weight * equity) / price)


def plan_orders(
    combined: dict[str, float],
    positions: dict[str, float],
    prices: dict[str, float],
    equity: float,
    policy: AccountPolicy,
) -> list[OrderPlan]:
    symbols = set(combined) | set(positions)
    min_delta = policy.min_delta(equity)
    max_order_notional = policy.max_order_notional_frac * equity
    plans: list[OrderPlan] = []

    for symbol in sorted(symbols):
        if symbol not in prices:
            continue
        price = prices[symbol]
        weight = combined.get(symbol, 0.0)
        target = _target_qty(weight, equity, price)
        current = _position_qty(positions, symbol)
        delta = target - current
        notional = abs(delta) * price
        if notional < min_delta:
            continue
        if notional > max_order_notional:
            raise FlattenRequested("account")
        side = "buy" if delta > 0 else "sell"
        plans.append(OrderPlan(symbol=symbol, qty=int(abs(delta)), side=side))

    if len(plans) > policy.max_orders_per_rebalance:
        raise FlattenRequested("account")

    return plans


def deviations_after(
    wanted: dict[str, float],
    got: dict[str, float],
    equity: float,
    prices: dict[str, float],
) -> list[dict]:
    min_delta = max(1.0, 0.001 * equity)
    symbols = set(wanted) | set(got)
    deviations: list[dict] = []

    for symbol in sorted(symbols):
        if symbol not in prices:
            continue
        wanted_weight = wanted.get(symbol, 0.0)
        got_weight = got.get(symbol, 0.0)
        gap_notional = abs(wanted_weight - got_weight) * equity
        if gap_notional >= min_delta:
            deviations.append(
                {"asset": symbol, "wanted": wanted_weight, "got": got_weight}
            )

    return deviations
