"""Runs the backtest engine for every enabled instrument and every strategy.

This produces measured expectancy/profit-factor/win-rate numbers instead of
assuming any strategy performs well. Nothing here is a guarantee: results
depend entirely on the historical window fetched from MT5.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from zoetrading.analysis import classify_market_regime
from zoetrading.backtesting.engine import BacktestEngine, BacktestInput, BacktestResult
from zoetrading.config.models import AppConfig, InstrumentConfig
from zoetrading.domain import Candle, Signal
from zoetrading.market import MarketDataEngine, MarketDataError
from zoetrading.strategies import Strategy, StrategyContext, default_strategies

MIN_CANDLES_FOR_REGIME = 20


@dataclass(frozen=True)
class StrategyBacktestReport:
    results: tuple[BacktestResult, ...]
    skipped: tuple[str, ...]

    @property
    def ranked_by_expectancy(self) -> tuple[BacktestResult, ...]:
        return tuple(sorted(self.results, key=lambda result: result.metrics.expectancy, reverse=True))


def run_library_backtest(
    config: AppConfig,
    market: MarketDataEngine,
    *,
    candle_count: int = 500,
    lookahead_bars: int = 20,
    spread_cost_r: float = 0.05,
    slippage_cost_r: float = 0.02,
    strategies: tuple[Strategy, ...] | None = None,
) -> StrategyBacktestReport:
    strategies = strategies or default_strategies()
    engine = BacktestEngine()
    results: list[BacktestResult] = []
    skipped: list[str] = []

    for instrument in config.instruments.instruments:
        if not instrument.enabled:
            continue
        timeframe = _first_available_timeframe(
            config.settings.market.setup_timeframes,
            instrument.timeframes,
        )
        if timeframe is None:
            skipped.append(f"{instrument.symbol}: no setup timeframe configured")
            continue
        try:
            candles = market.client.get_candles(instrument.symbol, timeframe, candle_count)
        except MarketDataError as exc:
            skipped.append(f"{instrument.symbol} {timeframe}: {exc}")
            continue
        if len(candles) < MIN_CANDLES_FOR_REGIME + lookahead_bars:
            skipped.append(f"{instrument.symbol} {timeframe}: not enough history")
            continue

        for strategy in strategies:
            data = BacktestInput(
                instrument=instrument.symbol,
                strategy=strategy.name,
                timeframe=timeframe,
                candles=candles,
                spread_cost_r=spread_cost_r,
                slippage_cost_r=slippage_cost_r,
            )
            result = engine.run(
                data,
                _strategy_signal_factory(strategy, instrument, timeframe),
                lookahead_bars=lookahead_bars,
            )
            results.append(result)

    return StrategyBacktestReport(results=tuple(results), skipped=tuple(skipped))


def _strategy_signal_factory(strategy: Strategy, instrument: InstrumentConfig, timeframe: str):
    def factory(candles: Sequence[Candle], index: int) -> Signal | None:
        if len(candles) < MIN_CANDLES_FOR_REGIME:
            return None
        regime = classify_market_regime(candles)
        if not strategy.is_active_for(regime.regime):
            return None
        context = StrategyContext(
            instrument=instrument.symbol,
            family=instrument.family,
            timeframe=timeframe,
            candles=tuple(candles),
            regime=regime,
        )
        return strategy.evaluate(context)

    return factory


def _first_available_timeframe(preferred: tuple[str, ...], available: tuple[str, ...]) -> str | None:
    for timeframe in preferred:
        if timeframe in available:
            return timeframe
    return available[0] if available else None
