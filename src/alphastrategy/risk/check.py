from __future__ import annotations

from alphastrategy.errors import FlattenRequested
from alphastrategy.risk.policy import AccountPolicy


def check_book(
    combined: dict[str, float],
    equity: float,
    policy: AccountPolicy,
) -> None:
    del equity  # reserved for future notional checks; weights drive v1 book checks

    if policy.long_only and any(w < 0 for w in combined.values()):
        raise FlattenRequested("account")

    gross = sum(abs(w) for w in combined.values())
    if gross > policy.max_gross:
        raise FlattenRequested("account")

    if any(abs(w) > policy.max_name_weight for w in combined.values()):
        raise FlattenRequested("account")

    names = sum(1 for w in combined.values() if w != 0.0)
    if names > policy.max_names:
        raise FlattenRequested("account")
