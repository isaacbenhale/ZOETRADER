"""Market regime classification built on technical primitives."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from zoetrading.analysis.indicators import atr
from zoetrading.analysis.market_structure import (
    StructureTrend,
    detect_breakout,
    detect_swings,
    infer_market_structure,
)
from zoetrading.analysis.volatility import VolatilityState, classify_volatility
from zoetrading.domain import Candle, MarketRegime


@dataclass(frozen=True)
class RegimeAssessment:
    regime: MarketRegime
    structure_trend: StructureTrend
    volatility: VolatilityState
    reasons: tuple[str, ...]
    blockers: tuple[str, ...] = ()

    @property
    def tradable(self) -> bool:
        return self.regime is not MarketRegime.CHAOTIC and not self.blockers


def classify_market_regime(
    candles: Sequence[Candle],
    *,
    swing_left: int = 1,
    swing_right: int = 1,
    atr_period: int = 14,
    breakout_lookback: int = 3,
    min_candles: int = 20,
) -> RegimeAssessment:
    """Classify the current market context from candles.

    This is deliberately deterministic and conservative: weak or contradictory
    context becomes CHAOTIC, which later maps naturally to NO_TRADE.
    """

    if len(candles) < min_candles:
        return RegimeAssessment(
            regime=MarketRegime.CHAOTIC,
            structure_trend=StructureTrend.UNDEFINED,
            volatility=VolatilityState.NORMAL,
            reasons=("insufficient candles",),
            blockers=("INSUFFICIENT_DATA",),
        )

    swings = detect_swings(candles, left=swing_left, right=swing_right)
    structure = infer_market_structure(swings)
    atr_values = atr(candles, period=atr_period) if len(candles) >= atr_period + 1 else []
    volatility = classify_volatility(atr_values)
    reasons: list[str] = [structure.description, f"volatility={volatility.value}"]

    recent_high = max(candle.high for candle in candles[-min(10, len(candles)) : -1])
    recent_low = min(candle.low for candle in candles[-min(10, len(candles)) : -1])
    breakout = detect_breakout(
        candles,
        resistance=recent_high,
        support=recent_low,
        lookback=breakout_lookback,
    )

    if volatility is VolatilityState.HIGH:
        reasons.append("high volatility")
        return RegimeAssessment(
            regime=MarketRegime.HIGH_VOLATILITY,
            structure_trend=structure.trend,
            volatility=volatility,
            reasons=tuple(reasons),
        )

    if volatility is VolatilityState.LOW:
        reasons.append("low volatility")
        return RegimeAssessment(
            regime=MarketRegime.LOW_VOLATILITY,
            structure_trend=structure.trend,
            volatility=volatility,
            reasons=tuple(reasons),
        )

    if breakout is not None:
        reasons.append(f"breakout={breakout.direction}")
        return RegimeAssessment(
            regime=MarketRegime.BREAKOUT,
            structure_trend=structure.trend,
            volatility=volatility,
            reasons=tuple(reasons),
        )

    if structure.trend is StructureTrend.UPTREND:
        return RegimeAssessment(
            regime=MarketRegime.TRENDING_UP,
            structure_trend=structure.trend,
            volatility=volatility,
            reasons=tuple(reasons),
        )

    if structure.trend is StructureTrend.DOWNTREND:
        return RegimeAssessment(
            regime=MarketRegime.TRENDING_DOWN,
            structure_trend=structure.trend,
            volatility=volatility,
            reasons=tuple(reasons),
        )

    if structure.trend is StructureTrend.RANGE:
        return RegimeAssessment(
            regime=MarketRegime.RANGING,
            structure_trend=structure.trend,
            volatility=volatility,
            reasons=tuple(reasons),
        )

    return RegimeAssessment(
        regime=MarketRegime.CHAOTIC,
        structure_trend=structure.trend,
        volatility=volatility,
        reasons=tuple(reasons + ["undefined structure"]),
        blockers=("UNDEFINED_STRUCTURE",),
    )


TREND_STRATEGIES = frozenset({"trend_pullback", "structure_continuation"})
BREAKOUT_STRATEGIES = frozenset({"breakout_retest", "momentum_breakout"})
RANGE_STRATEGIES = frozenset({"range_reversal", "mean_reversion"})
REVERSAL_STRATEGIES = frozenset({"reversal"})


def strategy_allowed_for_regime(strategy: str, regime: MarketRegime) -> bool:
    normalized = strategy.strip().lower()
    if regime in {MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN}:
        return normalized in TREND_STRATEGIES or normalized in REVERSAL_STRATEGIES
    if regime is MarketRegime.RANGING:
        return normalized in RANGE_STRATEGIES
    if regime is MarketRegime.BREAKOUT:
        return normalized in BREAKOUT_STRATEGIES
    if regime in {MarketRegime.HIGH_VOLATILITY, MarketRegime.LOW_VOLATILITY, MarketRegime.CHAOTIC}:
        return False
    return False

