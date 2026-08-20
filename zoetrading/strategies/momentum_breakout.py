"""Momentum breakout strategy: breakout sustained by momentum and volatility expansion."""

from __future__ import annotations

from zoetrading.analysis import atr as atr_series, detect_breakout, rate_of_change
from zoetrading.analysis.series import closes
from zoetrading.domain import MarketRegime, Signal, TradeAction
from zoetrading.journal import new_signal_id
from zoetrading.strategies.base import Strategy, StrategyContext
from zoetrading.strategies.helpers import latest_atr, no_trade_signal, rr_target
from zoetrading.strategies.parameters import parameters_for_family


class MomentumBreakoutStrategy(Strategy):
    name = "momentum_breakout"
    allowed_regimes = frozenset({MarketRegime.BREAKOUT})

    RECENT_WINDOW = 5
    BASE_WINDOW = 10
    MOMENTUM_PERIOD = 5
    MOMENTUM_THRESHOLD_PCT = 0.15
    VOLATILITY_EXPANSION_RATIO = 1.1

    def evaluate(self, context: StrategyContext) -> Signal:
        if not self.is_active_for(context.regime.regime):
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason=f"{self.name} inactive for regime {context.regime.regime.value}",
            )

        params = parameters_for_family(context.family)
        window = self.RECENT_WINDOW + self.BASE_WINDOW
        if len(context.candles) < window + self.MOMENTUM_PERIOD:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="not enough candles for momentum breakout",
            )

        previous = context.candles[-window:-self.RECENT_WINDOW]
        resistance = max(candle.high for candle in previous)
        support = min(candle.low for candle in previous)
        breakout = detect_breakout(
            context.candles,
            resistance=resistance,
            support=support,
            lookback=self.RECENT_WINDOW,
        )
        if breakout is None:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="no confirmed breakout",
            )

        roc_values = rate_of_change(closes(context.candles), period=self.MOMENTUM_PERIOD)
        latest_roc = roc_values[-1]
        if latest_roc is None:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="momentum is unavailable",
            )
        if breakout.direction == "UP" and latest_roc < self.MOMENTUM_THRESHOLD_PCT:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="momentum does not confirm upside breakout",
            )
        if breakout.direction == "DOWN" and latest_roc > -self.MOMENTUM_THRESHOLD_PCT:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="momentum does not confirm downside breakout",
            )

        atr_values = atr_series(context.candles, period=14)
        recent_atr = [value for value in atr_values[-self.RECENT_WINDOW :] if value is not None]
        older_atr = [value for value in atr_values[-window : -self.RECENT_WINDOW] if value is not None]
        if not recent_atr or not older_atr:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="volatility data is unavailable",
            )
        expansion = (sum(recent_atr) / len(recent_atr)) / (sum(older_atr) / len(older_atr))
        if expansion < self.VOLATILITY_EXPANSION_RATIO:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="volatility is not expanding to sustain breakout",
            )

        atr_value = latest_atr(context.candles)
        entry = context.candles[-1].close
        action = TradeAction.BUY if breakout.direction == "UP" else TradeAction.SELL
        invalidation = breakout.level
        if action is TradeAction.BUY:
            stop_loss = invalidation - (atr_value * params.stop_buffer_atr)
        else:
            stop_loss = invalidation + (atr_value * params.stop_buffer_atr)
        take_profit = rr_target(entry, stop_loss, action, params.target_rr)
        score = max(0, min(100, 80 + int(min(abs(latest_roc), 10))))
        return Signal(
            signal_id=new_signal_id(),
            instrument=context.instrument,
            action=action,
            strategy=self.name,
            setup_score=score,
            regime=context.regime.regime,
            entry=entry,
            invalidation=invalidation,
            proposed_sl=stop_loss,
            proposed_tp=take_profit,
            expected_rr=params.target_rr,
            reasons=(f"breakout {breakout.direction}", "momentum confirms breakout", "volatility expanding"),
        )
