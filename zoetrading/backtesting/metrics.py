"""Performance metrics used to validate strategies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceMetrics:
    trades: int
    win_rate: float
    expectancy: float
    profit_factor: float
    max_drawdown: float
    average_win: float
    average_loss: float
    mfe: float
    mae: float

    @property
    def profitable(self) -> bool:
        return self.expectancy > 0 and self.profit_factor > 1


def compute_metrics(r_multiples: tuple[float, ...], *, mfe: tuple[float, ...] = (), mae: tuple[float, ...] = ()) -> PerformanceMetrics:
    trades = len(r_multiples)
    if trades == 0:
        return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)

    wins = [value for value in r_multiples if value > 0]
    losses = [value for value in r_multiples if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in r_multiples:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)

    return PerformanceMetrics(
        trades=trades,
        win_rate=len(wins) / trades,
        expectancy=sum(r_multiples) / trades,
        profit_factor=gross_profit / gross_loss if gross_loss else float("inf"),
        max_drawdown=max_drawdown,
        average_win=sum(wins) / len(wins) if wins else 0.0,
        average_loss=sum(losses) / len(losses) if losses else 0.0,
        mfe=sum(mfe) / len(mfe) if mfe else 0.0,
        mae=sum(mae) / len(mae) if mae else 0.0,
    )

