"""
Tests for the broker safety guards (alphastrategy.live).

These tests verify that the hard-wall against accidentally
connecting to a live brokerage account cannot be bypassed.
"""
from __future__ import annotations

import pytest

from alphastrategy.live import (
    AlpacaAdapter,
    CONFIRM_LIVE_FLAG,
    LIVE_BASE_URL,
    LiveTradingRefused,
    PAPER_BASE_URL,
)


def test_default_is_paper():
    b = AlpacaAdapter()
    assert b.is_paper is True
    assert b.base_url == PAPER_BASE_URL


def test_explicit_paper_true_is_paper():
    b = AlpacaAdapter(paper=True)
    assert b.is_paper is True
    assert b.base_url == PAPER_BASE_URL


def test_paper_does_not_require_confirm():
    b = AlpacaAdapter(paper=True, confirm_live=False)
    assert b.is_paper is True


def test_paper_false_without_confirm_raises():
    with pytest.raises(LiveTradingRefused):
        AlpacaAdapter(paper=False)


def test_paper_false_with_confirm_false_raises():
    with pytest.raises(LiveTradingRefused):
        AlpacaAdapter(paper=False, confirm_live=False)


def test_paper_false_with_confirm_true_succeeds():
    b = AlpacaAdapter(paper=False, confirm_live=True)
    assert b.is_paper is False
    assert b.base_url == LIVE_BASE_URL


def test_error_message_mentions_confirm_flag():
    with pytest.raises(LiveTradingRefused) as exc:
        AlpacaAdapter(paper=False)
    msg = str(exc.value)
    assert CONFIRM_LIVE_FLAG in msg
    assert "paper=False" in msg or "live" in msg.lower()


def test_error_message_says_default_is_paper():
    with pytest.raises(LiveTradingRefused) as exc:
        AlpacaAdapter(paper=False)
    assert "paper" in str(exc.value).lower()


def test_no_way_to_construct_live_without_double_flag():
    with pytest.raises(LiveTradingRefused):
        AlpacaAdapter(paper=False)
    with pytest.raises(LiveTradingRefused):
        AlpacaAdapter(paper=False, confirm_live=False)
    with pytest.raises(LiveTradingRefused):
        AlpacaAdapter(paper=False, confirm_live=None)


def test_confirm_flag_is_string_not_truthy_zero():
    for falsy in [0, "", [], None]:
        with pytest.raises(LiveTradingRefused):
            AlpacaAdapter(paper=False, confirm_live=falsy)


def test_confirm_flag_constant_value():
    assert CONFIRM_LIVE_FLAG == "confirm_yes_i_know_what_im_doing"


def test_paper_and_live_urls_are_distinct():
    assert PAPER_BASE_URL != LIVE_BASE_URL
    assert "paper" in PAPER_BASE_URL
    assert "paper" not in LIVE_BASE_URL or "api" in LIVE_BASE_URL


def test_alpaca_adapter_name():
    b = AlpacaAdapter()
    assert b.name == "alpaca"


def test_alpaca_adapter_repr_includes_mode():
    b = AlpacaAdapter()
    r = repr(b)
    assert "paper" in r or "LIVE" in r or "live" in r.lower()
    assert PAPER_BASE_URL in r
