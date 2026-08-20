from __future__ import annotations

from typing import Any

from alphastrategy.risk.policy import AccountPolicy

_EPS = 1e-12


def _nonzero_weight_count(weights: dict[str, float] | None) -> int:
    if not weights:
        return 0
    return sum(1 for value in weights.values() if abs(float(value)) > _EPS)


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

    return {
        "names": int(names),
        "max_names": int(policy.max_names),
        "orders_today": int(orders_today),
        "max_orders_per_day": int(policy.max_orders_per_day),
        "cash_weight": cash_weight,
        "invested_weight": invested_weight,
        "target_cash_weight": target_cash_weight,
        "max_gross": float(policy.max_gross),
    }


def from_supervisor(supervisor: Any, *, live: bool) -> dict[str, Any]:
    snapshot = supervisor.snapshot
    equity = None
    cash = None
    positions = None
    if live:
        try:
            account = supervisor.broker.get_account()
            equity = float(account.get("equity", 0))
            cash = float(account.get("cash", equity))
            positions = supervisor.broker.list_positions()
        except Exception:
            equity = None
            cash = None
            positions = None
    return summarize(
        policy=supervisor.policy,
        orders_today=snapshot.orders_today,
        equity=equity,
        cash=cash,
        positions=positions,
        last_combined=snapshot.last_combined,
        last_got=snapshot.last_got,
    )
