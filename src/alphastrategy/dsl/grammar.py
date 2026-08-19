"""Closed-operator grammar for alphaloop.dsl/v0."""

from __future__ import annotations

from alphastrategy.errors import IllegalWeights

FACTOR_OPS = frozenset(
    {
        "rsi",
        "macd",
        "roc",
        "momentum_12_1",
        "bollinger_zscore",
        "ohlr_4_pct",
        "pairs_spread",
        "atr_breakout",
        "parkinson_hist_vol",
        "obv_slope",
    }
)

PORTFOLIO_OPS = frozenset({"normalize", "clip", "equal_weight", "cash"})

KNOWN_OPS = FACTOR_OPS | PORTFOLIO_OPS


def validate_step(step: dict) -> str:
    """Return the op name or raise if the step is invalid."""
    if not isinstance(step, dict):
        raise IllegalWeights("step must be a mapping")
    op = step.get("op")
    if not isinstance(op, str) or not op:
        raise IllegalWeights("step missing op")
    if op not in KNOWN_OPS:
        raise ValueError(f"unknown op: {op}")
    return op
