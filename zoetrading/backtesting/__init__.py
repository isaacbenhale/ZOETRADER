"""Backtesting and validation helpers."""

from zoetrading.backtesting.engine import BacktestEngine, BacktestInput, BacktestResult
from zoetrading.backtesting.metrics import PerformanceMetrics, compute_metrics
from zoetrading.backtesting.monte_carlo import MonteCarloResult, monte_carlo_drawdowns
from zoetrading.backtesting.runner import StrategyBacktestReport, run_library_backtest
from zoetrading.backtesting.walk_forward import WalkForwardSplit, make_walk_forward_splits

__all__ = [
    "BacktestEngine",
    "BacktestInput",
    "BacktestResult",
    "MonteCarloResult",
    "PerformanceMetrics",
    "StrategyBacktestReport",
    "WalkForwardSplit",
    "compute_metrics",
    "make_walk_forward_splits",
    "monte_carlo_drawdowns",
    "run_library_backtest",
]

