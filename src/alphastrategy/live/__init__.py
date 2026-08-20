"""
alphastrategy.live - Broker connectivity for paper and live trading.

HARD WALL: live trading requires `paper=False` AND `confirm_live=True`.
"""
from .alpaca import DATA_BASE_URL, LIVE_BASE_URL, PAPER_BASE_URL, AlpacaAdapter
from .broker import (
    CONFIRM_LIVE_FLAG,
    Broker,
    BrokerConfig,
    LiveTradingRefused,
)

__all__ = [
    "Broker",
    "BrokerConfig",
    "LiveTradingRefused",
    "CONFIRM_LIVE_FLAG",
    "AlpacaAdapter",
    "PAPER_BASE_URL",
    "LIVE_BASE_URL",
    "DATA_BASE_URL",
]
