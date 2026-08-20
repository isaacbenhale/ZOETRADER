"""Reversal strategy: structural change confirmed by momentum divergence."""

from __future__ import annotations

from zoetrading.analysis import detect_swings, infer_market_structure, rsi
from zoetrading.analysis.series import closes
from zoetrading.domain import MarketRegime, Signal, TradeAction
from zoetrading.journal import new_signal_id
from zoetrading.strategies.base import Strategy, StrategyContext
from zoetrading.strategies.helpers import latest_atr, no_trade_signal, rr_target
from zoetrading.strategies.parameters import parameters_for_family


class ReversalStrategy(Strategy):
    name = "reversal"
    allowed_regimes = frozenset({MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN})

    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 65
    RSI_OVERSOLD = 35

    def evaluate(self, context: StrategyContext) -> Signal:
        if not self.is_active_for(context.regime.regime):
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason=f"{self.name} inactive for regime {context.regime.regime.value}",
            )

        structure = infer_market_structure(detect_swings(context.candles, left=1, right=1))
        if not (structure.last_high and structure.previous_high and structure.last_low and structure.previous_low):
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="not enough swing structure for reversal",
            )

        close_values = closes(context.candles)
        if len(close_values) < self.RSI_PERIOD + 2:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="not enough candles for momentum confirmation",
            )
        rsi_values = [value for value in rsi(close_values, self.RSI_PERIOD) if value is not None]
        if len(rsi_values) < 2:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="momentum reading is unavailable",
            )
        last_rsi, previous_rsi = rsi_values[-1], rsi_values[-2]

        params = parameters_for_family(context.family)
        atr_value = latest_atr(context.candles)
        entry = context.candles[-1].close

        bearish_structure = structure.last_high.price < structure.previous_high.price
        bearish_momentum = last_rsi >= self.RSI_OVERBOUGHT and last_rsi < previous_rsi
        if bearish_structure and bearish_momentum:
            invalidation = structure.last_high.price
            if entry >= invalidation:
                return no_trade_signal(
                    instrument=context.instrument,
                    strategy=self.name,
                    regime=context.regime.regime,
                    reason="entry is above bearish invalidation",
                )
            stop_loss = invalidation + (atr_value * params.stop_buffer_atr)
            take_profit = rr_target(entry, stop_loss, TradeAction.SELL, params.target_rr)
            return Signal(
                signal_id=new_signal_id(),
                instrument=context.instrument,
                action=TradeAction.SELL,
                strategy=self.name,
                setup_score=_score_reversal(last_rsi, self.RSI_OVERBOUGHT),
                regime=context.regime.regime,
                entry=entry,
                invalidation=invalidation,
                proposed_sl=stop_loss,
                proposed_tp=take_profit,
                expected_rr=params.target_rr,
                reasons=("lower high breaks trend structure", "RSI momentum rolling over from overbought"),
            )

        bullish_structure = structure.last_low.price > structure.previous_low.price
        bullish_momentum = last_rsi <= self.RSI_OVERSOLD and last_rsi > previous_rsi
        if bullish_structure and bullish_momentum:
            invalidation = structure.last_low.price
            if entry <= invalidation:
                return no_trade_signal(
                    instrument=context.instrument,
                    strategy=self.name,
                    regime=context.regime.regime,
                    reason="entry is below bullish invalidation",
                )
            stop_loss = invalidation - (atr_value * params.stop_buffer_atr)
            take_profit = rr_target(entry, stop_loss, TradeAction.BUY, params.target_rr)
            return Signal(
                signal_id=new_signal_id(),
                instrument=context.instrument,
                action=TradeAction.BUY,
                strategy=self.name,
                setup_score=_score_reversal(last_rsi, self.RSI_OVERSOLD),
                regime=context.regime.regime,
                entry=entry,
                invalidation=invalidation,
                proposed_sl=stop_loss,
                proposed_tp=take_profit,
                expected_rr=params.target_rr,
                reasons=("higher low breaks trend structure", "RSI momentum turning up from oversold"),
            )

        return no_trade_signal(
            instrument=context.instrument,
            strategy=self.name,
            regime=context.regime.regime,
            reason="no confirmed reversal signal",
        )


def _score_reversal(rsi_value: float, threshold: float) -> int:
    distance = abs(rsi_value - threshold)
    return max(0, min(100, 75 + int(distance)))
