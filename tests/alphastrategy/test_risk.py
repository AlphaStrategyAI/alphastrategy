from __future__ import annotations

from dataclasses import fields, replace

import pytest

from alphastrategy.errors import FlattenRequested, ImportRejected
from alphastrategy.risk.check import check_book
from alphastrategy.risk.policy import AccountPolicy, merge_limits
from alphastrategy.risk.utilization import summarize


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
    assert exc.value.reason == "max_gross"


def test_check_book_long_only_breach_flattens():
    policy = AccountPolicy.defaults()
    with pytest.raises(FlattenRequested) as exc:
        check_book({"A": -0.1, "B": 1.1}, 100_000.0, policy)
    assert exc.value.scope == "account"
    assert exc.value.reason == "long_only"


def test_check_book_name_weight_breach_flattens():
    policy = AccountPolicy.defaults()
    with pytest.raises(FlattenRequested) as exc:
        check_book({"A": 0.25}, 100_000.0, policy)
    assert exc.value.scope == "account"
    assert exc.value.reason == "max_name_weight"


def test_check_book_name_count_breach_flattens():
    policy = replace(AccountPolicy.defaults(), max_names=2)
    combined = {"A": 0.1, "B": 0.1, "C": 0.1}
    with pytest.raises(FlattenRequested) as exc:
        check_book(combined, 100_000.0, policy)
    assert exc.value.scope == "account"
    assert exc.value.reason == "max_names"


def test_check_book_ok_passes():
    policy = AccountPolicy.defaults()
    check_book({"A": 0.1, "B": 0.1, "C": 0.1}, 100_000.0, policy)


def test_summarize_counts_live_nonzero_positions() -> None:
    policy = AccountPolicy.defaults()
    out = summarize(
        policy=policy,
        orders_today=3,
        equity=10_000.0,
        cash=4_000.0,
        positions=[{"symbol": "AAPL", "qty": "10"}, {"symbol": "MSFT", "qty": "0"}],
        last_combined={"AAPL": 0.6},
        last_got={"AAPL": 0.55, "MSFT": 0.1},
    )
    assert out["names"] == 1
    assert out["max_names"] == 50
    assert out["orders_today"] == 3
    assert out["max_orders_per_day"] == 200
    assert out["cash_weight"] == pytest.approx(0.4)
    assert out["invested_weight"] == pytest.approx(0.6)
    assert out["target_cash_weight"] == pytest.approx(0.4)
    assert out["max_gross"] == 1.0
    assert out["max_name_weight"] == 0.20


def test_from_supervisor_uses_spoken_policy() -> None:
    from alphastrategy.risk.utilization import from_supervisor

    class Snap:
        orders_today = 0
        last_combined = {}
        last_got = {}

    class Fake:
        policy = AccountPolicy.defaults()
        snapshot = Snap()

        def spoken_policy(self):
            return replace(AccountPolicy.defaults(), max_name_weight=0.05, max_names=10)

    out = from_supervisor(Fake(), live=False)
    assert out["max_name_weight"] == 0.05
    assert out["max_names"] == 10
    assert out["max_gross"] == 1.0


def test_from_supervisor_live_limit_ignores_last_combined() -> None:
    from alphastrategy.risk.utilization import from_supervisor

    class Snap:
        orders_today = 0
        last_combined = {"AAPL": 0.40}
        last_got = {}
        last_prices = {}

    class Fake:
        snapshot = Snap()

        def spoken_policy(self):
            return AccountPolicy.defaults()

        def live_book(self):
            return {"equity": 10_000.0, "cash": 10_000.0}, []

        def live_cap_weights(self, equity, positions):
            del equity, positions
            return {}

    out = from_supervisor(Fake(), live=True)
    assert out["live_limit"] is None


def test_from_supervisor_live_limit_next_send_order_size() -> None:
    from alphastrategy.risk.utilization import from_supervisor

    class Snap:
        orders_today = 0
        last_combined = {"AAPL": 0.18}
        last_got = {}
        last_prices = {"AAPL": 100.0}

    class Fake:
        snapshot = Snap()

        def spoken_policy(self):
            return replace(AccountPolicy.defaults(), max_order_notional_frac=0.10)

        def live_book(self):
            return {"equity": 10_000.0, "cash": 10_000.0}, []

        def live_cap_weights(self, equity, positions):
            del equity, positions
            return {}

    out = from_supervisor(Fake(), live=True)
    assert out["live_limit"]["reason"] == "max_order_notional_frac"
    assert out["live_limit"]["kind"] == "send"


def test_from_supervisor_live_limit_next_send_orders_per_rebalance() -> None:
    from alphastrategy.risk.utilization import from_supervisor

    class Snap:
        orders_today = 0
        last_combined = {"AAA": 0.01, "BBB": 0.01, "CCC": 0.01}
        last_got = {}
        last_prices = {"AAA": 100.0, "BBB": 100.0, "CCC": 100.0}

    class Fake:
        snapshot = Snap()

        def spoken_policy(self):
            return replace(AccountPolicy.defaults(), max_orders_per_rebalance=2)

        def live_book(self):
            return {"equity": 10_000.0, "cash": 10_000.0}, []

        def live_cap_weights(self, equity, positions):
            del equity, positions
            return {}

    out = from_supervisor(Fake(), live=True)
    assert out["live_limit"]["reason"] == "max_orders_per_rebalance"
    assert out["live_limit"]["kind"] == "send"


def test_summarize_live_limit_from_marked_name() -> None:
    out = summarize(
        policy=AccountPolicy.defaults(),
        orders_today=0,
        last_got={"AAPL": 0.225},
    )
    assert out["live_limit"]["reason"] == "max_name_weight"
    assert out["live_limit"]["kind"] == "book"


def test_summarize_live_limit_none_inside_cap() -> None:
    out = summarize(
        policy=AccountPolicy.defaults(),
        orders_today=0,
        last_got={"AAPL": 0.15},
    )
    assert out["live_limit"] is None


def test_summarize_live_limit_zero_name_cap() -> None:
    out = summarize(
        policy=replace(AccountPolicy.defaults(), max_name_weight=0.0),
        orders_today=0,
        last_got={"AAPL": 0.15},
    )
    assert out["live_limit"]["reason"] == "max_name_weight"


def test_merge_limits_overlay_zero_name_cap() -> None:
    merged = merge_limits({}, AccountPolicy.defaults(), {"max_name_weight": 0})
    assert merged.max_name_weight == 0.0


def test_summarize_falls_back_to_last_got_when_no_positions() -> None:
    out = summarize(
        policy=AccountPolicy.defaults(),
        orders_today=0,
        last_got={"AAPL": 0.2, "MSFT": 0.0, "GOOG": 0.1},
    )
    assert out["names"] == 2
    assert out["cash_weight"] is None
    assert out["invested_weight"] is None
    assert out["target_cash_weight"] is None


def test_summarize_falls_back_to_last_combined_when_got_empty() -> None:
    out = summarize(
        policy=AccountPolicy.defaults(),
        orders_today=0,
        last_combined={"AAPL": 0.25, "MSFT": 0.25},
    )
    assert out["names"] == 2
    assert out["target_cash_weight"] == pytest.approx(0.5)


def test_summarize_empty_book_is_zeros() -> None:
    out = summarize(policy=AccountPolicy.defaults(), orders_today=0)
    assert out["names"] == 0
    assert out["orders_today"] == 0
    assert out["cash_weight"] is None
    assert out["target_cash_weight"] is None


def test_summarize_zero_equity_cash_weight_is_zero() -> None:
    out = summarize(
        policy=AccountPolicy.defaults(),
        orders_today=0,
        equity=0.0,
        cash=0.0,
        positions=[],
    )
    assert out["cash_weight"] == 0.0
    assert out["invested_weight"] == 0.0


def test_policy_labels_cover_account_policy_fields() -> None:
    from alphastrategy.risk.labels import POLICY_LABELS, label_for

    keys = {item.name for item in fields(AccountPolicy)}
    assert set(POLICY_LABELS) == keys
    assert label_for("max_gross") == "Gross cap"
    assert label_for("max_name_weight") == "Name cap"
    assert label_for("max_names") == "Names"
    assert label_for("max_order_notional_frac") == "Order size"
    assert label_for("max_orders_per_rebalance") == "Orders / rebalance"
    assert label_for("max_orders_per_day") == "Orders today"
    assert label_for("min_delta_dollar") == "Min delta $"
    assert label_for("min_delta_frac") == "Min delta % of equity"
    assert label_for("long_only") == "Long only"
    assert label_for("not_a_cap") == "not_a_cap"
