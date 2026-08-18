"""Helpers for extracting price series from candles."""

from __future__ import annotations

from collections.abc import Sequence

from zoetrading.domain import Candle


def closes(candles: Sequence[Candle]) -> list[float]:
    return [candle.close for candle in candles]


def highs(candles: Sequence[Candle]) -> list[float]:
    return [candle.high for candle in candles]


def lows(candles: Sequence[Candle]) -> list[float]:
    return [candle.low for candle in candles]


def require_min_length(values: Sequence[object], minimum: int, name: str) -> None:
    if len(values) < minimum:
        raise ValueError(f"{name} requires at least {minimum} values")

