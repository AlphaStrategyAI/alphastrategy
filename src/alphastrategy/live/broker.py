"""
Broker interface and safety guards.

This module defines:

  - `Broker` — a vendor-agnostic protocol every broker adapter must
    implement. Defining it here (rather than in each adapter) lets
    downstream code swap Alpaca for Interactive Brokers, Futu, etc.
    without changing the calling site.

  - `LiveTradingRefused` — the single exception raised whenever
    live-trading is requested without the explicit
    `--confirm-yes-i-know-what-im-doing` flag.

**Safety model (HARD WALL)**

The v1.0 design is intentionally conservative:

  1. **Default is paper**. A caller that constructs an adapter without
     setting `paper=False` cannot accidentally connect to a live
     account.

  2. **Double opt-in for live**. Even if `paper=False` is set, the
     adapter still refuses to construct unless
     `confirm_live=True` is also set. Two flags, both required.

  3. **No silent fall-through**. If the constructor is called with
     `paper=False, confirm_live=False`, it raises immediately.
     There is no "warning then proceed" mode.

  4. **The flag is verbose on purpose**. The string
     `confirm_yes_i_know_what_im_doing` is hard to type by accident,
     making the safety barrier proportional to its risk.

This module contains ZERO network code. The actual HTTP calls live
in the adapter (see `alpaca.py`). Tests for this module are pure
Python (no mocking required).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable
from urllib.parse import unquote, urlsplit


class LiveTradingRefused(Exception):
    """Raised when live trading is requested without explicit confirmation.

    This is the project's hard wall against accidentally connecting
    to a real brokerage account. The message is intentionally loud
    and includes the exact flag the caller must set.
    """


# The exact name of the "I really mean it" flag. Must match the
# CLI argument name in `cli/commands.py`.
CONFIRM_LIVE_FLAG = "confirm_yes_i_know_what_im_doing"


def _normalized_hostname(url: str) -> str | None:
    hostname = urlsplit(url).hostname
    if hostname is None:
        return None
    while True:
        decoded = unquote(hostname)
        if decoded == hostname:
            break
        hostname = decoded
    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError:
        pass
    return hostname.rstrip(".").casefold()


@dataclass
class BrokerConfig:
    """Configuration shared by every Broker adapter.

    Attributes:
        paper: True for paper trading (sandbox), False for live.
        confirm_live: Required to be True when paper=False. Has no
            effect when paper=True.
        api_key: API key. None means "not configured" — adapters
            may refuse to construct without a key.
        secret: API secret. Same rules as `api_key`.
        base_url: Override for the broker's HTTP endpoint. Optional;
            adapters compute their own default from `paper`.
        timeout_seconds: HTTP timeout for broker requests.
    """

    paper: bool = True
    confirm_live: bool = False
    api_key: Optional[str] = None
    secret: Optional[str] = None
    base_url: Optional[str] = None
    timeout_seconds: float = 30.0


def _enforce_safety(config: BrokerConfig) -> None:
    """Raise LiveTradingRefused if a live-mode configuration is unsafe.

    Called from every Broker adapter's constructor.

    Rules:
      1. `paper=False` requires `confirm_live=True`.
      2. `paper=True` accepts any `confirm_live` value.
    """
    if config.paper and config.base_url:
        hostname = _normalized_hostname(config.base_url)
        if hostname == "api.alpaca.markets":
            raise LiveTradingRefused(
                "Paper trading refused: live trading base URL "
                "https://api.alpaca.markets is not allowed when paper=True."
            )
    if not config.paper and not config.confirm_live:
        raise LiveTradingRefused(
            "Live trading refused: paper=False requires "
            f"{CONFIRM_LIVE_FLAG}=True. "
            "Default is paper trading (sandbox). "
            "If you really intend to connect to a real-money account, "
            f"pass `confirm_live=True` to the constructor (or the "
            f"`--{CONFIRM_LIVE_FLAG}` CLI flag)."
        )


@runtime_checkable
class Broker(Protocol):
    """Vendor-agnostic broker interface.

    Adapters (Alpaca, IB, Futu, ...) implement this. Downstream
    code depends on the protocol, not the implementation.
    """

    @property
    def is_paper(self) -> bool:
        """True if connected to paper / sandbox."""
        ...

    @property
    def name(self) -> str:
        """Adapter name, e.g. 'alpaca'."""
        ...

    def get_account(self) -> dict:
        """Return the account summary as a dict.

        Must NOT mutate state. Must NOT place orders. Safe to call
        any number of times.

        Returns:
            dict with at minimum the keys: equity, cash, status.
        """
        ...

    def is_market_open(self) -> bool:
        """Return True if the broker reports the market is currently open."""
        ...

    def list_positions(self) -> list[dict]:
        """Return open positions as a list of dicts."""
        ...

    def place_order(self, symbol: str, qty: float, side: str) -> dict:
        """Place a market day order and return the broker order dict."""
        ...

    def cancel_order(self, order_id: str) -> None:
        """Cancel an open order by id."""
        ...

    def cancel_open_orders(self) -> None:
        """Cancel every currently open order."""
        ...

    def close_all(self) -> None:
        """Close all open positions at market."""
        ...

    def get_clock(self) -> dict:
        """Return the broker clock snapshot as a dict."""
        ...

    def get_bars(self, symbols: list[str], start: str, end: str) -> dict:
        """Return daily bars keyed by symbol."""
        ...
