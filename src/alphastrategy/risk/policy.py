from __future__ import annotations

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


def _apply_envelope(account: AccountPolicy, envelope: dict) -> AccountPolicy:
    updates: dict = {}
    for key, value in envelope.items():
        if key == "long_only":
            if value is not True:
                updates["long_only"] = True
            continue
        if key not in _NUMERIC_CAPS:
            continue
        current = getattr(account, key)
        if key in ("max_names", "max_orders_per_rebalance", "max_orders_per_day"):
            updates[key] = _tighten_int(current, int(value))
        elif key in ("min_delta_dollar",):
            updates[key] = _tighten_min_delta_dollar(current, float(value))
        elif key in ("min_delta_frac",):
            updates[key] = _tighten_min_delta_frac(current, float(value))
        else:
            updates[key] = _tighten_numeric(current, float(value))
    return replace(account, **updates) if updates else account


def _apply_overlay(base: AccountPolicy, overlay: dict) -> AccountPolicy:
    updates: dict = {}
    for key, value in overlay.items():
        if key == "long_only":
            if value is not True and base.long_only:
                raise ImportRejected("overlay cannot loosen long_only")
            if value is True and not base.long_only:
                updates["long_only"] = True
            continue
        if key not in _NUMERIC_CAPS:
            continue
        current = getattr(base, key)
        if key in ("max_names", "max_orders_per_rebalance", "max_orders_per_day"):
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
