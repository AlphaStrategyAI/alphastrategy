"""
Alpaca broker adapter.

Default: paper trading (sandbox at https://paper-api.alpaca.markets).
Live trading: requires both `paper=False` AND `confirm_live=True`.

This module does NOT initiate any HTTP connection at import time.
The actual REST calls live in private methods that are only invoked
when the user explicitly calls a request method.

References:
  - Alpaca paper trading base URL: https://paper-api.alpaca.markets
  - Alpaca live trading base URL:  https://api.alpaca.markets
  - Alpaca API docs:               https://alpaca.markets/docs/api-references/trading-api/
"""
from __future__ import annotations

import json
from typing import Any, Optional
from urllib.parse import urlencode

from .broker import BrokerConfig, _enforce_safety


PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"
DATA_BASE_URL = "https://data.alpaca.markets"


class AlpacaAdapter:
    """Alpaca Markets adapter (paper by default).

    Construction is safe: this class makes no HTTP calls until you
    invoke a request method. Even then, the request method uses
    urllib.request directly (no third-party SDK required) so the
    dependency surface stays minimal.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        paper: bool = True,
        confirm_live: "Optional[bool]" = False,
        base_url: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        if confirm_live is None:
            confirm_live = False
        config = BrokerConfig(
            paper=paper,
            confirm_live=confirm_live,
            api_key=api_key,
            secret=secret,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
        _enforce_safety(config)

        self._config = config
        self._base_url = base_url or (PAPER_BASE_URL if paper else LIVE_BASE_URL)

    @property
    def is_paper(self) -> bool:
        return self._config.paper

    @property
    def name(self) -> str:
        return "alpaca"

    @property
    def base_url(self) -> str:
        return self._base_url

    def get_account(self) -> dict:
        return self._request("GET", "/v2/account")

    def is_market_open(self) -> bool:
        data = self.get_clock()
        return bool(data.get("is_open", False))

    def list_positions(self) -> list[dict]:
        result = self._request("GET", "/v2/positions")
        if isinstance(result, list):
            return result
        return []

    def place_order(self, symbol: str, qty: float, side: str) -> dict:
        body = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": "market",
            "time_in_force": "day",
        }
        result = self._request("POST", "/v2/orders", body=body)
        return result if isinstance(result, dict) else {}

    def cancel_order(self, order_id: str) -> None:
        self._request("DELETE", f"/v2/orders/{order_id}")

    def cancel_open_orders(self) -> None:
        self._request("DELETE", "/v2/orders")

    def close_all(self) -> None:
        self._request("DELETE", "/v2/positions")

    def get_clock(self) -> dict:
        result = self._request("GET", "/v2/clock")
        return result if isinstance(result, dict) else {}

    def get_bars(self, symbols: list[str], start: str, end: str) -> dict:
        bars: dict[str, Any] = {}
        params = urlencode(
            {"start": start, "end": end, "timeframe": "1Day"}
        )
        for symbol in symbols:
            path = f"/v2/stocks/{symbol}/bars?{params}"
            bars[symbol] = self._request("GET", path, base_url=DATA_BASE_URL)
        return bars

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
        base_url: Optional[str] = None,
    ) -> Any:
        if not self._config.api_key or not self._config.secret:
            raise RuntimeError(
                "AlpacaAdapter requires api_key and secret to be set. "
                "Construct with AlpacaAdapter(api_key=..., secret=...)."
            )

        import urllib.request

        url = (base_url or self._base_url).rstrip("/") + path
        data: Optional[bytes] = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("APCA-API-KEY-ID", self._config.api_key)
        req.add_header("APCA-API-SECRET-KEY", self._config.secret)
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
            payload = resp.read().decode("utf-8")
        if not payload:
            return {}
        return json.loads(payload)

    def __repr__(self) -> str:
        mode = "paper" if self.is_paper else "LIVE"
        return f"<AlpacaAdapter mode={mode} base_url={self._base_url!r}>"
