"""Simple deterministic backtest harness."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from zoetrading.backtesting.metrics import PerformanceMetrics, compute_metrics
from zoetrading.domain import Candle, Signal, TradeAction


SignalFactory = Callable[[Sequence[Candle], int], Signal | None]


@dataclass(frozen=True)
class BacktestInput:
    instrument: str
    strategy: str
    timeframe: str
    candles: tuple[Candle, ...]
    spread_cost_r: float = 0.0
    slippage_cost_r: float = 0.0


@dataclass(frozen=True)
class BacktestResult:
    instrument: str
    strategy: str
    timeframe: str
    metrics: PerformanceMetrics
    r_multiples: tuple[float, ...]
    assumptions: dict[str, float]


class BacktestEngine:
    def run(
        self,
        data: BacktestInput,
        signal_factory: SignalFactory,
        *,
        lookahead_bars: int = 10,
    ) -> BacktestResult:
        if lookahead_bars <= 0:
            raise ValueError("lookahead_bars must be positive")
        r_multiples: list[float] = []
        mfe_values: list[float] = []
        mae_values: list[float] = []
        total_cost = data.spread_cost_r + data.slippage_cost_r

        for index in range(1, len(data.candles) - lookahead_bars):
            signal = signal_factory(data.candles[: index + 1], index)
            if signal is None or signal.action is TradeAction.NO_TRADE:
                continue
            assert signal.entry is not None
            assert signal.proposed_sl is not None
            assert signal.proposed_tp is not None
            risk = abs(signal.entry - signal.proposed_sl)
            if risk <= 0:
                continue

            future = data.candles[index + 1 : index + 1 + lookahead_bars]
            outcome, mfe, mae = _simulate_trade(signal, future, risk)
            r_multiples.append(outcome - total_cost)
            mfe_values.append(mfe)
            mae_values.append(mae)

        return BacktestResult(
            instrument=data.instrument,
            strategy=data.strategy,
            timeframe=data.timeframe,
            metrics=compute_metrics(tuple(r_multiples), mfe=tuple(mfe_values), mae=tuple(mae_values)),
            r_multiples=tuple(r_multiples),
            assumptions={
                "spread_cost_r": data.spread_cost_r,
                "slippage_cost_r": data.slippage_cost_r,
                "lookahead_bars": float(lookahead_bars),
            },
        )


def _simulate_trade(signal: Signal, future: Sequence[Candle], risk: float) -> tuple[float, float, float]:
    assert signal.entry is not None
    assert signal.proposed_sl is not None
    assert signal.proposed_tp is not None
    if signal.action is TradeAction.BUY:
        mfe = max((candle.high - signal.entry) / risk for candle in future)
        mae = min((candle.low - signal.entry) / risk for candle in future)
        for candle in future:
            if candle.low <= signal.proposed_sl:
                return -1.0, mfe, mae
            if candle.high >= signal.proposed_tp:
                return abs(signal.proposed_tp - signal.entry) / risk, mfe, mae
    else:
        mfe = max((signal.entry - candle.low) / risk for candle in future)
        mae = min((signal.entry - candle.high) / risk for candle in future)
        for candle in future:
            if candle.high >= signal.proposed_sl:
                return -1.0, mfe, mae
            if candle.low <= signal.proposed_tp:
                return abs(signal.entry - signal.proposed_tp) / risk, mfe, mae
    return max(min(mfe, 1.0), -1.0), mfe, mae

