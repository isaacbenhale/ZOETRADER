"""Deterministic technical indicators."""

from __future__ import annotations

from collections.abc import Sequence

from zoetrading.domain import Candle
from zoetrading.analysis.series import closes, require_min_length


def sma(values: Sequence[float], period: int) -> list[float | None]:
    _validate_period(period)
    output: list[float | None] = []
    running_sum = 0.0
    for index, value in enumerate(values):
        running_sum += float(value)
        if index >= period:
            running_sum -= float(values[index - period])
        if index + 1 < period:
            output.append(None)
        else:
            output.append(running_sum / period)
    return output


def ema(values: Sequence[float], period: int) -> list[float | None]:
    _validate_period(period)
    if not values:
        return []
    output: list[float | None] = []
    multiplier = 2 / (period + 1)
    ema_value: float | None = None
    seed_values: list[float] = []
    for value in values:
        numeric = float(value)
        if ema_value is None:
            seed_values.append(numeric)
            if len(seed_values) < period:
                output.append(None)
                continue
            ema_value = sum(seed_values) / period
            output.append(ema_value)
            continue
        ema_value = (numeric - ema_value) * multiplier + ema_value
        output.append(ema_value)
    return output


def rate_of_change(values: Sequence[float], period: int) -> list[float | None]:
    _validate_period(period)
    output: list[float | None] = []
    for index, value in enumerate(values):
        if index < period:
            output.append(None)
            continue
        previous = float(values[index - period])
        output.append(((float(value) - previous) / previous) * 100 if previous != 0 else None)
    return output


def rsi(values: Sequence[float], period: int = 14) -> list[float | None]:
    _validate_period(period)
    require_min_length(values, period + 1, "rsi")
    output: list[float | None] = [None] * len(values)
    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, period + 1):
        change = float(values[index]) - float(values[index - 1])
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    average_gain = sum(gains) / period
    average_loss = sum(losses) / period
    output[period] = _rsi_value(average_gain, average_loss)

    for index in range(period + 1, len(values)):
        change = float(values[index]) - float(values[index - 1])
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        average_gain = ((average_gain * (period - 1)) + gain) / period
        average_loss = ((average_loss * (period - 1)) + loss) / period
        output[index] = _rsi_value(average_gain, average_loss)
    return output


def macd(
    values: Sequence[float],
    *,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    if fast_period >= slow_period:
        raise ValueError("fast_period must be lower than slow_period")
    fast = ema(values, fast_period)
    slow = ema(values, slow_period)
    macd_line: list[float | None] = []
    for fast_value, slow_value in zip(fast, slow, strict=True):
        macd_line.append(None if fast_value is None or slow_value is None else fast_value - slow_value)

    signal_input = [value for value in macd_line if value is not None]
    compact_signal = ema(signal_input, signal_period)
    signal_line: list[float | None] = [None] * len(macd_line)
    start_index = next((index for index, value in enumerate(macd_line) if value is not None), len(macd_line))
    for offset, value in enumerate(compact_signal):
        signal_line[start_index + offset] = value

    histogram: list[float | None] = []
    for macd_value, signal_value in zip(macd_line, signal_line, strict=True):
        histogram.append(
            None if macd_value is None or signal_value is None else macd_value - signal_value
        )
    return macd_line, signal_line, histogram


def atr(candles: Sequence[Candle], period: int = 14) -> list[float | None]:
    _validate_period(period)
    require_min_length(candles, period + 1, "atr")
    true_ranges: list[float] = []
    for index, candle in enumerate(candles):
        if index == 0:
            true_ranges.append(candle.high - candle.low)
            continue
        previous_close = candles[index - 1].close
        true_ranges.append(
            max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        )

    output: list[float | None] = [None] * len(candles)
    average = sum(true_ranges[1 : period + 1]) / period
    output[period] = average
    for index in range(period + 1, len(candles)):
        average = ((average * (period - 1)) + true_ranges[index]) / period
        output[index] = average
    return output


def close_sma(candles: Sequence[Candle], period: int) -> list[float | None]:
    return sma(closes(candles), period)


def _validate_period(period: int) -> None:
    if period <= 0:
        raise ValueError("period must be positive")


def _rsi_value(average_gain: float, average_loss: float) -> float:
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))

