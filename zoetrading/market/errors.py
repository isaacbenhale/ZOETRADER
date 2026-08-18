"""Market data specific exceptions."""


class MarketDataError(RuntimeError):
    """Base class for market data failures."""


class MT5ConnectionError(MarketDataError):
    """Raised when MetaTrader 5 is unavailable or disconnected."""


class SymbolUnavailableError(MarketDataError):
    """Raised when a requested symbol is not available in MT5."""


class StaleMarketDataError(MarketDataError):
    """Raised when market data is too old to support a decision."""

