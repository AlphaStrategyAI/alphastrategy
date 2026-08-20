from __future__ import annotations

EPS = 1e-12


def residual_book(
    combined: dict[str, float],
    contribution: dict[str, float],
) -> dict[str, float]:
    assets = set(combined) | set(contribution)
    out: dict[str, float] = {}
    for asset in assets:
        weight = combined.get(asset, 0.0) - contribution.get(asset, 0.0)
        if weight > EPS:
            out[asset] = weight
    return out
