from __future__ import annotations

import pytest

from alphastrategy.supervisor.combine import combine


def test_combine_two_sleeves():
    sleeves = [(0.4, {"A": 1.0}), (0.6, {"B": 1.0})]
    assert combine(sleeves) == {"A": 0.4, "B": 0.6}


def test_combine_overlapping_assets():
    sleeves = [(0.5, {"A": 1.0}), (0.5, {"A": 0.5, "B": 0.5})]
    assert combine(sleeves) == {"A": 0.75, "B": 0.25}


def test_combine_allocation_sum_over_one_raises():
    with pytest.raises(ValueError):
        combine([(0.6, {"A": 1.0}), (0.5, {"B": 1.0})])


def test_combine_negative_allocation_raises():
    with pytest.raises(ValueError):
        combine([(-0.1, {"A": 1.0})])


def test_combine_allows_residual_cash():
    assert combine([(0.4, {"A": 1.0})]) == {"A": 0.4}
