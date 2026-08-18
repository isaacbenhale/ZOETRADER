"""Volatility helpers."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum


class VolatilityState(StrEnum):
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


def classify_volatility(
    atr_values: Sequence[float | None],
    *,
    lookback: int = 20,
    high_ratio: float = 1.5,
    low_ratio: float = 0.7,
) -> VolatilityState:
    valid = [value for value in atr_values if value is not None]
    if not valid:
        return VolatilityState.NORMAL
    current = valid[-1]
    sample = valid[-lookback:]
    average = sum(sample) / len(sample)
    if average == 0:
        return VolatilityState.NORMAL
    ratio = current / average
    if ratio >= high_ratio:
        return VolatilityState.HIGH
    if ratio <= low_ratio:
        return VolatilityState.LOW
    return VolatilityState.NORMAL

