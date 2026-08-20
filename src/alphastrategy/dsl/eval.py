"""In-process DSL v0 evaluator."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from alphastrategy.dsl import factors
from alphastrategy.dsl.grammar import FACTOR_OPS, validate_step
from alphastrategy.errors import IllegalWeights

__all__ = ["evaluate_dsl", "IllegalWeights"]

_SUM_TOL = 1e-9


def evaluate_dsl(
    dsl: dict,
    bars: pd.DataFrame,
    effective_at,
    params: dict,
) -> dict[str, float]:
    universe = list(dsl["universe"])
    weights = {sym: 0.0 for sym in universe}

    for step in dsl.get("steps", []):
        op = validate_step(step)
        step_params = {**params, **step.get("params", {})}
        if op in FACTOR_OPS:
            weights = _apply_factor(op, step_params, weights, universe, bars, effective_at)
        elif op == "equal_weight":
            weights = _op_equal_weight(universe)
        elif op == "normalize":
            weights = _op_normalize(weights, universe)
        elif op == "clip":
            weights = _op_clip(weights, universe, step_params)
        elif op == "cash":
            weights = _op_cash(weights, universe, step_params)
        else:  # pragma: no cover
            raise ValueError(f"unknown op: {op}")

    _validate_weights(weights, universe)
    return weights


def _apply_factor(
    op: str,
    step_params: dict[str, Any],
    weights: dict[str, float],
    universe: list[str],
    bars: pd.DataFrame,
    effective_at,
) -> dict[str, float]:
    out = dict(weights)
    if op == "pairs_spread":
        leg_a = step_params.get("leg_a")
        leg_b = step_params.get("leg_b")
        if leg_a not in universe or leg_b not in universe:
            raise IllegalWeights("pairs_spread legs must be in universe")
        if leg_a not in bars.columns or leg_b not in bars.columns:
            raise IllegalWeights("pairs_spread legs missing from bars")
        series = factors.pairs_spread(
            bars[leg_a],
            bars[leg_b],
            window=int(step_params.get("window", 60)),
            num_std=float(step_params.get("num_std", 1.5)),
        )
        for sym in universe:
            out[sym] = 0.0
        out[leg_a] = _factor_weight_at(series, effective_at)
        return out

    fn = getattr(factors, op)
    for sym in universe:
        if sym not in bars.columns:
            continue
        close = bars[sym]
        if op in ("ohlr_4_pct", "atr_breakout"):
            ohlc = _close_to_ohlc(close)
            series = fn(ohlc, **_factor_kwargs(op, step_params))
        elif op == "obv_slope":
            volume = pd.Series(1.0, index=close.index, dtype=float)
            series = fn(close, volume, **_factor_kwargs(op, step_params))
        else:
            series = fn(close, **_factor_kwargs(op, step_params))
        out[sym] = _factor_weight_at(series, effective_at)
    return out


def _factor_kwargs(op: str, step_params: dict[str, Any]) -> dict[str, Any]:
    reserved = {"leg_a", "leg_b", "max", "min_cash"}
    return {k: v for k, v in step_params.items() if k not in reserved}


def _close_to_ohlc(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"high": close, "low": close, "close": close}, index=close.index)


def _factor_weight_at(series: pd.Series, effective_at) -> float:
    val = _value_at(series, effective_at)
    if not math.isfinite(val):
        return 0.0
    if val < 0.0:
        return 0.0
    return min(float(val), 1.0)


def _value_at(series: pd.Series, effective_at) -> float:
    ts = pd.Timestamp(effective_at)
    eligible = series.index[series.index <= ts]
    if len(eligible) == 0:
        return 0.0
    return float(series.loc[eligible[-1]])


def _op_equal_weight(universe: list[str]) -> dict[str, float]:
    n = len(universe)
    if n == 0:
        return {}
    w = 1.0 / n
    return {sym: w for sym in universe}


def _op_normalize(weights: dict[str, float], universe: list[str]) -> dict[str, float]:
    vals = []
    for sym in universe:
        v = weights.get(sym, 0.0)
        if math.isfinite(v) and v >= 0.0:
            vals.append(v)
        else:
            vals.append(0.0)
    total = sum(vals)
    if total == 0.0:
        return {sym: 0.0 for sym in universe}
    return {sym: max(0.0, weights.get(sym, 0.0)) / total for sym in universe}


def _op_clip(
    weights: dict[str, float],
    universe: list[str],
    step_params: dict[str, Any],
) -> dict[str, float]:
    max_w = float(step_params.get("max", 0.2))
    if max_w < 0.0:
        raise IllegalWeights("clip max must be non-negative")
    clipped = {sym: min(max(0.0, weights.get(sym, 0.0)), max_w) for sym in universe}
    total = sum(clipped.values())
    if total == 0.0:
        return clipped
    return {sym: v / total for sym, v in clipped.items()}


def _op_cash(
    weights: dict[str, float],
    universe: list[str],
    step_params: dict[str, Any],
) -> dict[str, float]:
    min_cash = float(step_params.get("min_cash", 0.0))
    max_invested = 1.0 - min_cash
    total = sum(weights.get(sym, 0.0) for sym in universe)
    if total <= max_invested or total == 0.0:
        return dict(weights)
    scale = max_invested / total
    return {sym: weights.get(sym, 0.0) * scale for sym in universe}


def _validate_weights(weights: dict[str, float], universe: list[str]) -> None:
    extra = set(weights) - set(universe)
    if extra:
        raise IllegalWeights(f"symbol not in universe: {sorted(extra)[0]}")
    total = 0.0
    for sym in universe:
        w = weights.get(sym, 0.0)
        if w < 0.0:
            raise IllegalWeights(f"negative weight for {sym}")
        if not math.isfinite(w):
            raise IllegalWeights(f"non-finite weight for {sym}")
        total += w
    if total > 1.0 + _SUM_TOL:
        raise IllegalWeights("weights sum exceeds 1")
