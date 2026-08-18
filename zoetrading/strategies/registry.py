"""Strategy registry."""

from __future__ import annotations

from zoetrading.strategies.base import Strategy
from zoetrading.strategies.breakout_retest import BreakoutRetestStrategy
from zoetrading.strategies.range_reversal import RangeReversalStrategy
from zoetrading.strategies.trend_pullback import TrendPullbackStrategy


def default_strategies() -> tuple[Strategy, ...]:
    return (
        TrendPullbackStrategy(),
        BreakoutRetestStrategy(),
        RangeReversalStrategy(),
    )

