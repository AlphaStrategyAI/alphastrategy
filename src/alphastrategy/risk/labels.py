"""Spoken names for AccountPolicy fields. Storage keys stay machine names."""

from __future__ import annotations

POLICY_LABELS: dict[str, str] = {
    "long_only": "Long only",
    "max_gross": "Gross cap",
    "max_name_weight": "Name cap",
    "max_names": "Names",
    "max_order_notional_frac": "Order size",
    "max_orders_per_rebalance": "Orders / rebalance",
    "max_orders_per_day": "Orders today",
    "min_delta_dollar": "Min delta $",
    "min_delta_frac": "Min delta % of equity",
}


def label_for(key: str) -> str:
    return POLICY_LABELS.get(key, key)
