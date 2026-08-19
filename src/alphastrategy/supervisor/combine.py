from __future__ import annotations


def combine(sleeves: list[tuple[float, dict[str, float]]]) -> dict[str, float]:
    total_alloc = 0.0
    for alloc, _weights in sleeves:
        if alloc < 0:
            raise ValueError("allocation must be >= 0")
        total_alloc += alloc
    if total_alloc > 1.0:
        raise ValueError("allocation sum must be <= 1.0")

    out: dict[str, float] = {}
    for alloc, weights in sleeves:
        for asset, w in weights.items():
            out[asset] = out.get(asset, 0.0) + alloc * w
    return out
