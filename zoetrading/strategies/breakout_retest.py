"""Breakout + retest strategy."""

from __future__ import annotations

from zoetrading.analysis import detect_breakout, detect_retest
from zoetrading.domain import MarketRegime, Signal, TradeAction
from zoetrading.journal import new_signal_id
from zoetrading.strategies.base import Strategy, StrategyContext
from zoetrading.strategies.helpers import latest_atr, no_trade_signal, rr_target
from zoetrading.strategies.parameters import parameters_for_family


class BreakoutRetestStrategy(Strategy):
    name = "breakout_retest"
    allowed_regimes = frozenset({MarketRegime.BREAKOUT})

    def evaluate(self, context: StrategyContext) -> Signal:
        if not self.is_active_for(context.regime.regime):
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason=f"{self.name} inactive for regime {context.regime.regime.value}",
            )

        params = parameters_for_family(context.family)
        recent_window = 5
        base_window = 10
        if len(context.candles) < recent_window + base_window:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="not enough candles for breakout retest",
            )

        previous = context.candles[-(recent_window + base_window) : -recent_window]
        resistance = max(candle.high for candle in previous)
        support = min(candle.low for candle in previous)
        breakout = detect_breakout(
            context.candles,
            resistance=resistance,
            support=support,
            lookback=recent_window,
        )
        if breakout is None:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="no confirmed breakout",
            )

        atr_value = latest_atr(context.candles)
        tolerance = atr_value * params.retest_tolerance_atr
        if not detect_retest(context.candles, breakout, tolerance=tolerance):
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="breakout has not retested the level",
            )

        entry = context.candles[-1].close
        action = TradeAction.BUY if breakout.direction == "UP" else TradeAction.SELL
        if action is TradeAction.BUY:
            invalidation = breakout.level
            stop_loss = invalidation - (atr_value * params.stop_buffer_atr)
        else:
            invalidation = breakout.level
            stop_loss = invalidation + (atr_value * params.stop_buffer_atr)
        take_profit = rr_target(entry, stop_loss, action, params.target_rr)
        return Signal(
            signal_id=new_signal_id(),
            instrument=context.instrument,
            action=action,
            strategy=self.name,
            setup_score=85,
            regime=context.regime.regime,
            entry=entry,
            invalidation=invalidation,
            proposed_sl=stop_loss,
            proposed_tp=take_profit,
            expected_rr=params.target_rr,
            reasons=(f"breakout {breakout.direction}", "retest confirmed"),
        )
