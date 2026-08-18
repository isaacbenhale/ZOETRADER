"""Base contracts for deterministic strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from zoetrading.analysis import MultiTimeframeContext, RegimeAssessment
from zoetrading.domain import Candle, InstrumentFamily, MarketRegime, Signal


@dataclass(frozen=True)
class StrategyContext:
    instrument: str
    family: InstrumentFamily
    timeframe: str
    candles: tuple[Candle, ...]
    regime: RegimeAssessment
    mtf: MultiTimeframeContext | None = None


@dataclass(frozen=True)
class StrategyStats:
    strategy: str
    evaluated: int = 0
    produced_signals: int = 0
    blocked: int = 0

    def record_signal(self, signal: Signal) -> "StrategyStats":
        return StrategyStats(
            strategy=self.strategy,
            evaluated=self.evaluated + 1,
            produced_signals=self.produced_signals + (0 if signal.action.value == "NO_TRADE" else 1),
            blocked=self.blocked + (1 if signal.action.value == "NO_TRADE" else 0),
        )


class Strategy(ABC):
    name: str
    allowed_regimes: frozenset[MarketRegime]

    @abstractmethod
    def evaluate(self, context: StrategyContext) -> Signal:
        """Return a normalized trade proposal or a motivated NO_TRADE signal."""

    def is_active_for(self, regime: MarketRegime) -> bool:
        return regime in self.allowed_regimes

