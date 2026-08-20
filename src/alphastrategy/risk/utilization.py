from __future__ import annotations

from typing import Any

from alphastrategy.errors import FlattenRequested
from alphastrategy.risk.check import check_book
from alphastrategy.risk.policy import AccountPolicy
from alphastrategy.supervisor.orders import plan_orders

_EPS = 1e-12


def _nonzero_weight_count(weights: dict[str, float] | None) -> int:
    if not weights:
        return 0
    return sum(1 for value in weights.values() if abs(float(value)) > _EPS)


def _next_send_limit(
    *,
    policy: AccountPolicy,
    combined: dict[str, float] | None,
    prices: dict[str, float] | None,
    positions: list[dict[str, Any]] | None,
    equity: float | None,
    orders_today: int,
) -> dict[str, str] | None:
    if equity is None or equity <= 0:
        return None
    if not combined or not prices:
        return None
    qty: dict[str, float] = {}
    for pos in positions or []:
        symbol = str(pos.get("symbol") or "")
        if not symbol:
            continue
        qty[symbol] = float(pos.get("qty") or 0)
    try:
        plan_orders(
            dict(combined),
            qty,
            dict(prices),
            float(equity),
            policy,
            orders_already_today=int(orders_today),
        )
    except FlattenRequested as exc:
        return {"reason": str(exc.reason or "limit")}
    except Exception:
        return None
    return None


def summarize(
    *,
    policy: AccountPolicy,
    orders_today: int,
    equity: float | None = None,
    cash: float | None = None,
    positions: list[dict[str, Any]] | None = None,
    last_combined: dict[str, float] | None = None,
    last_got: dict[str, float] | None = None,
) -> dict[str, Any]:
    if positions:
        names = sum(1 for pos in positions if abs(float(pos.get("qty") or 0)) > _EPS)
    elif last_got:
        names = _nonzero_weight_count(last_got)
    else:
        names = _nonzero_weight_count(last_combined)

    cash_weight: float | None
    invested_weight: float | None
    if equity is None or cash is None:
        cash_weight = None
        invested_weight = None
    elif equity > 0:
        cash_weight = float(cash) / float(equity)
        invested_weight = 1.0 - cash_weight
    else:
        cash_weight = 0.0
        invested_weight = 0.0

    target_cash_weight: float | None = None
    if last_combined:
        target_cash_weight = max(0.0, 1.0 - sum(float(v) for v in last_combined.values()))

    live_limit = None
    if last_got:
        try:
            check_book(dict(last_got), 0.0, policy)
        except FlattenRequested as exc:
            live_limit = {"reason": str(exc.reason or "limit")}

    return {
        "names": int(names),
        "max_names": int(policy.max_names),
        "orders_today": int(orders_today),
        "max_orders_per_day": int(policy.max_orders_per_day),
        "cash_weight": cash_weight,
        "invested_weight": invested_weight,
        "target_cash_weight": target_cash_weight,
        "max_gross": float(policy.max_gross),
        "max_name_weight": float(policy.max_name_weight),
        "live_limit": live_limit,
    }


def from_supervisor(supervisor: Any, *, live: bool) -> dict[str, Any]:
    snapshot = supervisor.snapshot
    equity = None
    cash = None
    positions = None
    live_weights = None
    if live:
        try:
            account, positions = supervisor.live_book()
            equity = float(account.get("equity", 0))
            cash = float(account.get("cash", equity))
            live_weights = supervisor.live_cap_weights(equity, positions)
        except Exception:
            equity = None
            cash = None
            positions = None
            live_weights = None
    out = summarize(
        policy=supervisor.spoken_policy(),
        orders_today=snapshot.orders_today,
        equity=equity,
        cash=cash,
        positions=positions,
        last_combined=snapshot.last_combined,
        last_got=live_weights or snapshot.last_got,
    )
    if live and out.get("live_limit") is None:
        out["live_limit"] = _next_send_limit(
            policy=supervisor.spoken_policy(),
            combined=snapshot.last_combined,
            prices=getattr(snapshot, "last_prices", None),
            positions=positions,
            equity=equity,
            orders_today=snapshot.orders_today,
        )
    return out
