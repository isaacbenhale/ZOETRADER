"""Market structure, swings, breakouts and retests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from zoetrading.domain import Candle


class StructureTrend(StrEnum):
    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    RANGE = "RANGE"
    UNDEFINED = "UNDEFINED"


@dataclass(frozen=True)
class SwingPoint:
    index: int
    kind: str
    price: float

    def __post_init__(self) -> None:
        if self.kind not in {"HIGH", "LOW"}:
            raise ValueError("swing kind must be HIGH or LOW")


@dataclass(frozen=True)
class MarketStructure:
    trend: StructureTrend
    last_high: SwingPoint | None
    previous_high: SwingPoint | None
    last_low: SwingPoint | None
    previous_low: SwingPoint | None
    broke_structure: bool
    description: str


@dataclass(frozen=True)
class Breakout:
    direction: str
    level: float
    candle_index: int
    close: float

    def __post_init__(self) -> None:
        if self.direction not in {"UP", "DOWN"}:
            raise ValueError("breakout direction must be UP or DOWN")


def detect_swings(candles: Sequence[Candle], *, left: int = 2, right: int = 2) -> tuple[SwingPoint, ...]:
    if left <= 0 or right <= 0:
        raise ValueError("left and right must be positive")
    if len(candles) < left + right + 1:
        return ()

    swings: list[SwingPoint] = []
    for index in range(left, len(candles) - right):
        candle = candles[index]
        left_window = candles[index - left : index]
        right_window = candles[index + 1 : index + right + 1]
        if all(candle.high > item.high for item in left_window + right_window):
            swings.append(SwingPoint(index=index, kind="HIGH", price=candle.high))
        if all(candle.low < item.low for item in left_window + right_window):
            swings.append(SwingPoint(index=index, kind="LOW", price=candle.low))
    return tuple(swings)


def infer_market_structure(swings: Sequence[SwingPoint]) -> MarketStructure:
    highs = [swing for swing in swings if swing.kind == "HIGH"]
    lows = [swing for swing in swings if swing.kind == "LOW"]
    previous_high = highs[-2] if len(highs) >= 2 else None
    last_high = highs[-1] if highs else None
    previous_low = lows[-2] if len(lows) >= 2 else None
    last_low = lows[-1] if lows else None

    trend = StructureTrend.UNDEFINED
    description = "insufficient structure"
    if previous_high and last_high and previous_low and last_low:
        higher_high = last_high.price > previous_high.price
        higher_low = last_low.price > previous_low.price
        lower_high = last_high.price < previous_high.price
        lower_low = last_low.price < previous_low.price
        if higher_high and higher_low:
            trend = StructureTrend.UPTREND
            description = "HH/HL"
        elif lower_high and lower_low:
            trend = StructureTrend.DOWNTREND
            description = "LH/LL"
        else:
            trend = StructureTrend.RANGE
            description = "mixed highs/lows"

    broke_structure = _has_recent_bos(swings)
    return MarketStructure(
        trend=trend,
        last_high=last_high,
        previous_high=previous_high,
        last_low=last_low,
        previous_low=previous_low,
        broke_structure=broke_structure,
        description=description,
    )


def detect_breakout(
    candles: Sequence[Candle],
    *,
    resistance: float,
    support: float,
    lookback: int = 3,
) -> Breakout | None:
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    if not candles:
        return None
    start = max(0, len(candles) - lookback)
    for index in range(start, len(candles)):
        close = candles[index].close
        if close > resistance:
            return Breakout(direction="UP", level=resistance, candle_index=index, close=close)
        if close < support:
            return Breakout(direction="DOWN", level=support, candle_index=index, close=close)
    return None


def detect_retest(
    candles: Sequence[Candle],
    breakout: Breakout,
    *,
    tolerance: float,
    max_bars_after_breakout: int = 5,
) -> bool:
    if tolerance < 0:
        raise ValueError("tolerance must be zero or positive")
    end = min(len(candles), breakout.candle_index + max_bars_after_breakout + 1)
    for candle in candles[breakout.candle_index + 1 : end]:
        touched_level = candle.low <= breakout.level + tolerance and candle.high >= breakout.level - tolerance
        if not touched_level:
            continue
        if breakout.direction == "UP" and candle.close >= breakout.level:
            return True
        if breakout.direction == "DOWN" and candle.close <= breakout.level:
            return True
    return False


def _has_recent_bos(swings: Sequence[SwingPoint]) -> bool:
    if len(swings) < 3:
        return False
    recent = swings[-3:]
    highs = [swing for swing in recent if swing.kind == "HIGH"]
    lows = [swing for swing in recent if swing.kind == "LOW"]
    return len(highs) >= 2 and highs[-1].price > highs[-2].price or (
        len(lows) >= 2 and lows[-1].price < lows[-2].price
    )

