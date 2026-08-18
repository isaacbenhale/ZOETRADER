"""MetaTrader timeframe helpers."""

from __future__ import annotations

TIMEFRAME_SECONDS: dict[str, int] = {
    "M1": 60,
    "M5": 5 * 60,
    "M15": 15 * 60,
    "M30": 30 * 60,
    "H1": 60 * 60,
    "H4": 4 * 60 * 60,
    "D1": 24 * 60 * 60,
}


def normalize_timeframe(timeframe: str) -> str:
    value = timeframe.strip().upper()
    if value not in TIMEFRAME_SECONDS:
        allowed = ", ".join(sorted(TIMEFRAME_SECONDS))
        raise ValueError(f"Unsupported timeframe '{timeframe}'. Allowed values: {allowed}")
    return value


def mt5_timeframe_constant(mt5_module: object, timeframe: str) -> int:
    normalized = normalize_timeframe(timeframe)
    attr_name = f"TIMEFRAME_{normalized}"
    try:
        return int(getattr(mt5_module, attr_name))
    except AttributeError as exc:
        raise ValueError(f"MT5 module does not expose {attr_name}") from exc

