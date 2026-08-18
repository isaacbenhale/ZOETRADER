"""Multi-timeframe bias and alignment helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from zoetrading.analysis.regime import RegimeAssessment, classify_market_regime
from zoetrading.domain import Candle, MarketRegime, RejectionReason, TradeAction


class Bias(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    CHAOTIC = "CHAOTIC"


@dataclass(frozen=True)
class TimeframeBias:
    timeframe: str
    assessment: RegimeAssessment
    bias: Bias


@dataclass(frozen=True)
class MultiTimeframeContext:
    instrument: str
    biases: tuple[TimeframeBias, ...]
    context_bias: Bias
    setup_bias: Bias
    timing_bias: Bias
    aligned: bool
    conflict: bool
    recommended_action: TradeAction
    blockers: tuple[RejectionReason, ...] = ()


def bias_from_regime(regime: MarketRegime) -> Bias:
    if regime is MarketRegime.TRENDING_UP:
        return Bias.BULLISH
    if regime is MarketRegime.TRENDING_DOWN:
        return Bias.BEARISH
    if regime is MarketRegime.CHAOTIC:
        return Bias.CHAOTIC
    return Bias.NEUTRAL


def assess_timeframe(timeframe: str, candles: Sequence[Candle]) -> TimeframeBias:
    assessment = classify_market_regime(candles)
    return TimeframeBias(
        timeframe=timeframe.upper(),
        assessment=assessment,
        bias=bias_from_regime(assessment.regime),
    )


def assess_multi_timeframe(
    instrument: str,
    candles_by_timeframe: Mapping[str, Sequence[Candle]],
    *,
    context_timeframes: Sequence[str],
    setup_timeframes: Sequence[str],
    timing_timeframes: Sequence[str],
) -> MultiTimeframeContext:
    biases = tuple(
        assess_timeframe(timeframe, candles_by_timeframe[timeframe])
        for timeframe in candles_by_timeframe
    )
    bias_by_timeframe = {item.timeframe: item.bias for item in biases}

    context_bias = _aggregate_bias(context_timeframes, bias_by_timeframe)
    setup_bias = _aggregate_bias(setup_timeframes, bias_by_timeframe)
    timing_bias = _aggregate_bias(timing_timeframes, bias_by_timeframe)
    conflict = _has_major_conflict(context_bias, setup_bias, timing_bias)
    aligned = not conflict and context_bias in {Bias.BULLISH, Bias.BEARISH} and context_bias == setup_bias
    blockers: list[RejectionReason] = []
    if Bias.CHAOTIC in {context_bias, setup_bias, timing_bias}:
        blockers.append(RejectionReason.STRATEGY_BLOCKED)
    if conflict:
        blockers.append(RejectionReason.STRATEGY_BLOCKED)

    recommended_action = TradeAction.NO_TRADE
    if aligned and context_bias is Bias.BULLISH:
        recommended_action = TradeAction.BUY
    elif aligned and context_bias is Bias.BEARISH:
        recommended_action = TradeAction.SELL

    return MultiTimeframeContext(
        instrument=instrument,
        biases=biases,
        context_bias=context_bias,
        setup_bias=setup_bias,
        timing_bias=timing_bias,
        aligned=aligned,
        conflict=conflict,
        recommended_action=recommended_action,
        blockers=tuple(blockers),
    )


def _aggregate_bias(timeframes: Sequence[str], bias_by_timeframe: Mapping[str, Bias]) -> Bias:
    values = [bias_by_timeframe.get(timeframe.upper()) for timeframe in timeframes]
    known = [value for value in values if value is not None]
    if not known:
        return Bias.CHAOTIC
    if Bias.CHAOTIC in known:
        return Bias.CHAOTIC
    bullish = known.count(Bias.BULLISH)
    bearish = known.count(Bias.BEARISH)
    if bullish > bearish:
        return Bias.BULLISH
    if bearish > bullish:
        return Bias.BEARISH
    return Bias.NEUTRAL


def _has_major_conflict(*biases: Bias) -> bool:
    return Bias.BULLISH in biases and Bias.BEARISH in biases

