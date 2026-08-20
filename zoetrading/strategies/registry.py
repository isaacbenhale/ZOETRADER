"""Strategy registry."""

from __future__ import annotations

from zoetrading.strategies.base import Strategy
from zoetrading.strategies.breakout_retest import BreakoutRetestStrategy
from zoetrading.strategies.mean_reversion import MeanReversionStrategy
from zoetrading.strategies.momentum_breakout import MomentumBreakoutStrategy
from zoetrading.strategies.range_reversal import RangeReversalStrategy
from zoetrading.strategies.reversal import ReversalStrategy
from zoetrading.strategies.structure_continuation import StructureContinuationStrategy
from zoetrading.strategies.trend_pullback import TrendPullbackStrategy


def default_strategies() -> tuple[Strategy, ...]:
    return (
        TrendPullbackStrategy(),
        StructureContinuationStrategy(),
        BreakoutRetestStrategy(),
        MomentumBreakoutStrategy(),
        RangeReversalStrategy(),
        MeanReversionStrategy(),
        ReversalStrategy(),
    )

