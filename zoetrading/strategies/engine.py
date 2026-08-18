"""Strategy engine orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from zoetrading.domain import Signal, TradeAction
from zoetrading.strategies.base import Strategy, StrategyContext, StrategyStats
from zoetrading.strategies.helpers import no_trade_signal


@dataclass(frozen=True)
class StrategyRunResult:
    signals: tuple[Signal, ...]
    stats: dict[str, StrategyStats]

    @property
    def trade_signals(self) -> tuple[Signal, ...]:
        return tuple(signal for signal in self.signals if signal.action is not TradeAction.NO_TRADE)


class StrategyEngine:
    def __init__(self, strategies: tuple[Strategy, ...]) -> None:
        if not strategies:
            raise ValueError("at least one strategy is required")
        self.strategies = strategies

    def evaluate(self, context: StrategyContext) -> StrategyRunResult:
        signals: list[Signal] = []
        stats: dict[str, StrategyStats] = {}
        for strategy in self.strategies:
            if not strategy.is_active_for(context.regime.regime):
                signal = no_trade_signal(
                    instrument=context.instrument,
                    strategy=strategy.name,
                    regime=context.regime.regime,
                    reason=f"{strategy.name} inactive for regime {context.regime.regime.value}",
                )
            else:
                signal = strategy.evaluate(context)
            signals.append(signal)
            stats[strategy.name] = stats.get(
                strategy.name,
                StrategyStats(strategy=strategy.name),
            ).record_signal(signal)
        return StrategyRunResult(signals=tuple(signals), stats=stats)

