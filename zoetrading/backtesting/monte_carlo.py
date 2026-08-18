"""Monte-Carlo stress helpers for trade sequences."""

from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class MonteCarloResult:
    runs: int
    worst_drawdown: float
    median_drawdown: float


def monte_carlo_drawdowns(r_multiples: tuple[float, ...], *, runs: int = 100, seed: int = 42) -> MonteCarloResult:
    if runs <= 0:
        raise ValueError("runs must be positive")
    if not r_multiples:
        return MonteCarloResult(runs=runs, worst_drawdown=0.0, median_drawdown=0.0)
    rng = random.Random(seed)
    drawdowns: list[float] = []
    for _ in range(runs):
        sample = list(r_multiples)
        rng.shuffle(sample)
        drawdowns.append(_max_drawdown(sample))
    ordered = sorted(drawdowns)
    return MonteCarloResult(
        runs=runs,
        worst_drawdown=max(ordered),
        median_drawdown=ordered[len(ordered) // 2],
    )


def _max_drawdown(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown

