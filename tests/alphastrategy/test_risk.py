from __future__ import annotations

from dataclasses import replace

import pytest

from alphastrategy.errors import FlattenRequested, ImportRejected
from alphastrategy.risk.check import check_book
from alphastrategy.risk.policy import AccountPolicy, merge_limits


def test_account_policy_defaults():
    policy = AccountPolicy.defaults()
    assert policy.long_only is True
    assert policy.max_gross == 1.0
    assert policy.max_name_weight == 0.20
    assert policy.max_names == 50
    assert policy.max_order_notional_frac == 0.20
    assert policy.max_orders_per_rebalance == 100
    assert policy.max_orders_per_day == 200
    assert policy.min_delta(100_000.0) == 100.0
    assert policy.min_delta(500.0) == 1.0


def test_merge_limits_uses_envelope_to_tighten():
    account = AccountPolicy.defaults()
    envelope = {"max_name_weight": 0.10, "max_gross": 0.8}
    merged = merge_limits(envelope, account, None)
    assert merged.max_name_weight == 0.10
    assert merged.max_gross == 0.8
    assert merged.long_only is True


def test_merge_limits_missing_envelope_fields_use_account_defaults():
    account = AccountPolicy.defaults()
    merged = merge_limits({}, account, None)
    assert merged == account


def test_merge_limits_overlay_tightens():
    account = AccountPolicy.defaults()
    merged = merge_limits({}, account, {"max_name_weight": 0.10})
    assert merged.max_name_weight == 0.10


def test_merge_limits_overlay_increasing_max_name_weight_raises():
    account = AccountPolicy.defaults()
    with pytest.raises((ImportRejected, ValueError)):
        merge_limits({}, account, {"max_name_weight": 0.25})


@pytest.mark.parametrize("limits", [{"mystery_cap": 1}, {"max_gross": -0.1}, {"max_names": -1}])
def test_merge_limits_rejects_unknown_or_negative_limits(limits):
    with pytest.raises((ImportRejected, ValueError)):
        merge_limits(limits, AccountPolicy.defaults(), None)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), "not-a-number"])
def test_merge_limits_rejects_invalid_numeric_caps(value):
    with pytest.raises((ImportRejected, ValueError)):
        merge_limits({"max_gross": value}, AccountPolicy.defaults(), None)


def test_check_book_gross_breach_flattens_account():
    policy = AccountPolicy.defaults()
    combined = {"A": 0.6, "B": 0.6}
    with pytest.raises(FlattenRequested) as exc:
        check_book(combined, 1.0, policy)
    assert exc.value.scope == "account"


def test_check_book_long_only_breach_flattens():
    policy = AccountPolicy.defaults()
    with pytest.raises(FlattenRequested) as exc:
        check_book({"A": -0.1, "B": 1.1}, 100_000.0, policy)
    assert exc.value.scope == "account"


def test_check_book_name_weight_breach_flattens():
    policy = AccountPolicy.defaults()
    with pytest.raises(FlattenRequested) as exc:
        check_book({"A": 0.25}, 100_000.0, policy)
    assert exc.value.scope == "account"


def test_check_book_name_count_breach_flattens():
    policy = replace(AccountPolicy.defaults(), max_names=2)
    combined = {"A": 0.1, "B": 0.1, "C": 0.1}
    with pytest.raises(FlattenRequested) as exc:
        check_book(combined, 100_000.0, policy)
    assert exc.value.scope == "account"


def test_check_book_ok_passes():
    policy = AccountPolicy.defaults()
    check_book({"A": 0.1, "B": 0.1, "C": 0.1}, 100_000.0, policy)
