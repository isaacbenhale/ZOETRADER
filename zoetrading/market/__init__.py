"""Market data access layer."""

from zoetrading.market.errors import (
    MarketDataError,
    MT5ConnectionError,
    StaleMarketDataError,
    SymbolUnavailableError,
)
from zoetrading.market.market_data import CandleCache, InstrumentScanResult, MarketDataEngine
from zoetrading.market.mt5_client import MT5Client
from zoetrading.market.timeframes import TIMEFRAME_SECONDS, normalize_timeframe

__all__ = [
    "CandleCache",
    "InstrumentScanResult",
    "MT5Client",
    "MT5ConnectionError",
    "MarketDataEngine",
    "MarketDataError",
    "StaleMarketDataError",
    "SymbolUnavailableError",
    "TIMEFRAME_SECONDS",
    "normalize_timeframe",
]
