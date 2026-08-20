from __future__ import annotations

import math
from dataclasses import dataclass, replace

from alphastrategy.errors import ImportRejected

_NUMERIC_CAPS = (
    "max_gross",
    "max_name_weight",
    "max_names",
    "max_order_notional_frac",
    "max_orders_per_rebalance",
    "max_orders_per_day",
    "min_delta_dollar",
    "min_delta_frac",
)
_INTEGER_CAPS = ("max_names", "max_orders_per_rebalance", "max_orders_per_day")
_LIMIT_KEYS = frozenset((*_NUMERIC_CAPS, "long_only"))


@dataclass(frozen=True)
class AccountPolicy:
    long_only: bool = True
    max_gross: float = 1.0
    max_name_weight: float = 0.20
    max_names: int = 50
    max_order_notional_frac: float = 0.20
    max_orders_per_rebalance: int = 100
    max_orders_per_day: int = 200
    min_delta_dollar: float = 1.0
    min_delta_frac: float = 0.001

    @classmethod
    def defaults(cls) -> AccountPolicy:
        return cls()

    def min_delta(self, equity: float) -> float:
        return max(self.min_delta_dollar, self.min_delta_frac * equity)


def _tighten_numeric(current: float, proposed: float) -> float:
    return min(current, proposed)


def _tighten_int(current: int, proposed: int) -> int:
    return min(current, proposed)


def _tighten_min_delta_dollar(current: float, proposed: float) -> float:
    return max(current, proposed)


def _tighten_min_delta_frac(current: float, proposed: float) -> float:
    return max(current, proposed)


def _validate_limits(limits: dict, label: str) -> None:
    unknown = set(limits) - _LIMIT_KEYS
    if unknown:
        raise ImportRejected(f"unknown {label} limit: {sorted(unknown)[0]}")
    if "long_only" in limits and not isinstance(limits["long_only"], bool):
        raise ImportRejected(f"{label} long_only must be boolean")
    for key in _NUMERIC_CAPS:
        if key not in limits:
            continue
        value = limits[key]
        if isinstance(value, bool):
            raise ImportRejected(f"{label} {key} must be numeric")
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ImportRejected(f"{label} {key} must be numeric") from exc
        if not math.isfinite(numeric) or numeric < 0:
            raise ImportRejected(f"{label} {key} must be finite and non-negative")
        if key in _INTEGER_CAPS and not numeric.is_integer():
            raise ImportRejected(f"{label} {key} must be an integer")


def _apply_envelope(account: AccountPolicy, envelope: dict) -> AccountPolicy:
    _validate_limits(envelope, "envelope")
    updates: dict = {}
    for key, value in envelope.items():
        if key == "long_only":
            if value is not True:
                updates["long_only"] = True
            continue
        current = getattr(account, key)
        if key in _INTEGER_CAPS:
            updates[key] = _tighten_int(current, int(value))
        elif key in ("min_delta_dollar",):
            updates[key] = _tighten_min_delta_dollar(current, float(value))
        elif key in ("min_delta_frac",):
            updates[key] = _tighten_min_delta_frac(current, float(value))
        else:
            updates[key] = _tighten_numeric(current, float(value))
    return replace(account, **updates) if updates else account


def _apply_overlay(base: AccountPolicy, overlay: dict) -> AccountPolicy:
    _validate_limits(overlay, "overlay")
    updates: dict = {}
    for key, value in overlay.items():
        if key == "long_only":
            if value is not True and base.long_only:
                raise ImportRejected("overlay cannot loosen long_only")
            if value is True and not base.long_only:
                updates["long_only"] = True
            continue
        current = getattr(base, key)
        if key in _INTEGER_CAPS:
            proposed = int(value)
            if proposed > current:
                raise ImportRejected(f"overlay cannot loosen {key}")
            if proposed < current:
                updates[key] = proposed
        elif key in ("min_delta_dollar", "min_delta_frac"):
            proposed = float(value)
            if proposed < current:
                raise ImportRejected(f"overlay cannot loosen {key}")
            if proposed > current:
                updates[key] = proposed
        else:
            proposed = float(value)
            if proposed > current:
                raise ImportRejected(f"overlay cannot loosen {key}")
            if proposed < current:
                updates[key] = proposed
    return replace(base, **updates) if updates else base


def merge_limits(
    envelope: dict,
    account: AccountPolicy,
    overlay: dict | None,
) -> AccountPolicy:
    merged = _apply_envelope(account, envelope)
    if overlay is None:
        return merged
    return _apply_overlay(merged, overlay)


def tighten_policy(base: AccountPolicy, tighter: AccountPolicy) -> AccountPolicy:
    """Return the stricter of two policies (min caps, max min-deltas)."""
    return AccountPolicy(
        long_only=base.long_only or tighter.long_only,
        max_gross=min(base.max_gross, tighter.max_gross),
        max_name_weight=min(base.max_name_weight, tighter.max_name_weight),
        max_names=min(base.max_names, tighter.max_names),
        max_order_notional_frac=min(
            base.max_order_notional_frac, tighter.max_order_notional_frac
        ),
        max_orders_per_rebalance=min(
            base.max_orders_per_rebalance, tighter.max_orders_per_rebalance
        ),
        max_orders_per_day=min(base.max_orders_per_day, tighter.max_orders_per_day),
        min_delta_dollar=max(base.min_delta_dollar, tighter.min_delta_dollar),
        min_delta_frac=max(base.min_delta_frac, tighter.min_delta_frac),
    )
