from __future__ import annotations

from typing import Any

from alphastrategy.errors import FlattenRequested
from alphastrategy.risk.check import check_book
from alphastrategy.risk.policy import AccountPolicy
from alphastrategy.supervisor.combine import combine
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
        return {"reason": str(exc.reason or "limit"), "kind": "send"}
    except Exception:
        return None
    return None


def _next_send_combined(snapshot: Any) -> dict[str, float] | None:
    weights = getattr(snapshot, "last_sleeve_weights", None) or {}
    sleeves = getattr(snapshot, "sleeves", None) or {}
    pairs: list[tuple[float, dict[str, float]]] = []
    for bundle_id, sleeve_weights in weights.items():
        if not isinstance(sleeve_weights, dict) or not sleeve_weights:
            continue
        try:
            alloc = float(sleeves.get(bundle_id) or 0)
        except (TypeError, ValueError):
            continue
        if alloc <= 0:
            continue
        pairs.append((alloc, dict(sleeve_weights)))
    if pairs:
        try:
            return combine(pairs)
        except Exception:
            return None
    combined = getattr(snapshot, "last_combined", None)
    if not combined:
        return None
    return dict(combined)


def _next_send_ready(snapshot: Any) -> bool:
    weights = getattr(snapshot, "last_sleeve_weights", None) or {}
    sleeves = getattr(snapshot, "sleeves", None) or {}
    for bundle_id, raw_alloc in sleeves.items():
        try:
            alloc = float(raw_alloc or 0)
        except (TypeError, ValueError):
            continue
        if alloc <= 0:
            continue
        sleeve_weights = weights.get(bundle_id)
        if not isinstance(sleeve_weights, dict) or not sleeve_weights:
            return False
    return True


def last_sleeve_weight_ids(snapshot: Any) -> list[str]:
    weights = getattr(snapshot, "last_sleeve_weights", None) or {}
    ids: list[str] = []
    for bundle_id, sleeve_weights in weights.items():
        if isinstance(sleeve_weights, dict) and sleeve_weights:
            ids.append(str(bundle_id))
    return sorted(ids)


def _cash_residual(weights: dict[str, float] | None) -> float | None:
    if not weights:
        return None
    return max(0.0, 1.0 - sum(float(v) for v in weights.values()))


def last_sleeve_contribution_glance(snapshot: Any) -> dict[str, dict[str, float]]:
    last = getattr(snapshot, "last_sleeve_contribution", None) or {}
    return {
        str(bundle_id): {str(asset): float(weight) for asset, weight in weights.items()}
        for bundle_id, weights in last.items()
        if isinstance(weights, dict)
    }


def sleeve_contribution_glance(snapshot: Any) -> dict[str, dict[str, float]]:
    out = last_sleeve_contribution_glance(snapshot)
    if not _next_send_ready(snapshot):
        return out
    sleeve_weights = getattr(snapshot, "last_sleeve_weights", None) or {}
    sleeves = getattr(snapshot, "sleeves", None) or {}
    for bundle_id, raw_alloc in sleeves.items():
        try:
            alloc = float(raw_alloc or 0)
        except (TypeError, ValueError):
            continue
        if alloc <= 0:
            continue
        weights = sleeve_weights.get(bundle_id)
        if not isinstance(weights, dict) or not weights:
            continue
        out[str(bundle_id)] = {
            str(asset): alloc * float(weight) for asset, weight in weights.items()
        }
    return out


def next_send_combined_glance(snapshot: Any) -> dict[str, float] | None:
    if not _next_send_ready(snapshot):
        return None
    return _next_send_combined(snapshot)


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

    target_cash_weight: float | None = _cash_residual(last_combined)

    live_limit = None
    if last_got:
        try:
            check_book(dict(last_got), 0.0, policy)
        except FlattenRequested as exc:
            live_limit = {"reason": str(exc.reason or "limit"), "kind": "book"}

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
    out["last_target_cash_weight"] = out.get("target_cash_weight")
    if _next_send_ready(snapshot):
        residual = _cash_residual(_next_send_combined(snapshot))
        if residual is not None:
            out["target_cash_weight"] = residual
    if live and out.get("live_limit") is None:
        if not _next_send_ready(snapshot):
            out["live_limit"] = {"reason": "next_send_unknown", "kind": "unknown"}
        else:
            out["live_limit"] = _next_send_limit(
                policy=supervisor.spoken_policy(),
                combined=_next_send_combined(snapshot),
                prices=getattr(snapshot, "last_prices", None),
                positions=positions,
                equity=equity,
                orders_today=snapshot.orders_today,
            )
    return out
