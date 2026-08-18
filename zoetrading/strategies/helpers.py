"""Shared strategy helper functions."""

from __future__ import annotations

from collections.abc import Sequence

from zoetrading.analysis import atr, detect_swings
from zoetrading.domain import Candle, MarketRegime, RejectionReason, Signal, TradeAction
from zoetrading.journal import new_signal_id


def no_trade_signal(
    *,
    instrument: str,
    strategy: str,
    regime: MarketRegime,
    reason: str,
    blocker: RejectionReason = RejectionReason.STRATEGY_BLOCKED,
) -> Signal:
    return Signal(
        signal_id=new_signal_id(),
        instrument=instrument,
        action=TradeAction.NO_TRADE,
        strategy=strategy,
        setup_score=0,
        regime=regime,
        reasons=(reason,),
        blockers=(blocker,),
    )


def latest_atr(candles: Sequence[Candle], period: int = 14) -> float:
    values = atr(candles, period=period)
    latest = next((value for value in reversed(values) if value is not None), None)
    if latest is None:
        raise ValueError("ATR is unavailable")
    return latest


def last_close(candles: Sequence[Candle]) -> float:
    if not candles:
        raise ValueError("candles are required")
    return candles[-1].close


def recent_swings(candles: Sequence[Candle]):
    return detect_swings(candles, left=1, right=1)


def rr_target(entry: float, stop_loss: float, direction: TradeAction, target_rr: float) -> float:
    risk = abs(entry - stop_loss)
    if direction is TradeAction.BUY:
        return entry + (risk * target_rr)
    if direction is TradeAction.SELL:
        return entry - (risk * target_rr)
    raise ValueError("NO_TRADE has no target")

