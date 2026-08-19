"""
Tests for AlpacaAdapter (alphastrategy.live, paper mode).

All network calls are MOCKED via monkeypatch on urllib.request.urlopen.
"""
from __future__ import annotations

import json
from unittest import mock

import pytest

from alphastrategy.live import (
    AlpacaAdapter,
    DATA_BASE_URL,
    PAPER_BASE_URL,
)

@pytest.fixture(autouse=True)
def _block_real_urlopen(monkeypatch):
    """Fail fast if a test forgets to mock urllib.request.urlopen."""

    def _real_network_blocked(*args, **kwargs):
        raise RuntimeError(
            "Real urllib.request.urlopen called — tests must monkeypatch urlopen"
        )

    monkeypatch.setattr("urllib.request.urlopen", _real_network_blocked)


def _mock_urlopen_response(payload: dict | list) -> mock.MagicMock:
    response = mock.MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def test_construct_with_credentials():
    b = AlpacaAdapter(api_key="PK_TEST", secret="SECRET_TEST")
    assert b.is_paper is True
    assert b.name == "alpaca"
    assert b.base_url == PAPER_BASE_URL


def test_construct_live_requires_confirm():
    with pytest.raises(Exception):
        AlpacaAdapter(api_key="AK_TEST", secret="SECRET", paper=False)


def test_custom_base_url_overrides_default():
    custom = "https://my-proxy.example.com"
    b = AlpacaAdapter(paper=True, base_url=custom)
    assert b.base_url == custom


def test_get_account_without_credentials_raises():
    b = AlpacaAdapter()
    with pytest.raises(RuntimeError, match="api_key and secret"):
        b.get_account()


def test_is_market_open_without_credentials_raises():
    b = AlpacaAdapter()
    with pytest.raises(RuntimeError, match="api_key and secret"):
        b.is_market_open()


def test_get_account_uses_paper_url(monkeypatch):
    b = AlpacaAdapter(api_key="PK", secret="SEC")
    mock_resp = _mock_urlopen_response(
        {"equity": "100000", "cash": "100000", "status": "ACTIVE"}
    )
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["method"] = req.get_method()
        captured["timeout"] = timeout
        return mock_resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = b.get_account()
    assert captured["url"] == PAPER_BASE_URL + "/v2/account"
    headers_lc = {k.lower(): v for k, v in captured["headers"].items()}
    assert headers_lc.get("apca-api-key-id") == "PK"
    assert headers_lc.get("apca-api-secret-key") == "SEC"
    assert captured["method"] == "GET"
    assert result == {"equity": "100000", "cash": "100000", "status": "ACTIVE"}


def test_is_market_open_uses_clock_endpoint(monkeypatch):
    b = AlpacaAdapter(api_key="PK", secret="SEC")
    mock_resp = _mock_urlopen_response({"is_open": True, "next_open": "2026-01-02"})
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        return mock_resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert b.is_market_open() is True
    assert captured["url"] == PAPER_BASE_URL + "/v2/clock"


def test_place_order_posts_market_day(monkeypatch):
    b = AlpacaAdapter(api_key="PK", secret="SEC")
    mock_resp = _mock_urlopen_response({"id": "order-1", "status": "accepted"})
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = req.data.decode("utf-8") if req.data else None
        return mock_resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = b.place_order("AAPL", 10, "buy")
    assert captured["url"] == PAPER_BASE_URL + "/v2/orders"
    assert captured["method"] == "POST"
    assert json.loads(captured["body"]) == {
        "symbol": "AAPL",
        "qty": 10,
        "side": "buy",
        "type": "market",
        "time_in_force": "day",
    }
    assert result == {"id": "order-1", "status": "accepted"}


def test_get_bars_uses_data_host(monkeypatch):
    b = AlpacaAdapter(api_key="PK", secret="SEC")
    mock_resp = _mock_urlopen_response({"bars": []})
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        return mock_resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    b.get_bars(["AAPL"], "2026-01-01", "2026-01-02")
    assert captured["url"].startswith(DATA_BASE_URL + "/v2/stocks/AAPL/bars")
    assert "paper-api.alpaca.markets" not in captured["url"]
    headers_lc = {k.lower(): v for k, v in captured["headers"].items()}
    assert headers_lc.get("apca-api-key-id") == "PK"
    assert headers_lc.get("apca-api-secret-key") == "SEC"


def test_place_order_not_called_in_this_test_file_against_real_network(monkeypatch):
    """place_order must use monkeypatched urlopen, never real network."""
    b = AlpacaAdapter(api_key="PK", secret="SEC")
    mock_called = False
    mock_resp = _mock_urlopen_response({"id": "order-2"})

    def fake_urlopen(req, timeout):
        nonlocal mock_called
        mock_called = True
        return mock_resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    b.place_order("MSFT", 1, "sell")
    assert mock_called
