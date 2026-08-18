"""Trend pullback strategy."""

from __future__ import annotations

from zoetrading.analysis import Bias, StructureTrend
from zoetrading.domain import MarketRegime, RejectionReason, Signal, TradeAction
from zoetrading.journal import new_signal_id
from zoetrading.strategies.base import Strategy, StrategyContext
from zoetrading.strategies.helpers import latest_atr, no_trade_signal, recent_swings, rr_target
from zoetrading.strategies.parameters import parameters_for_family


class TrendPullbackStrategy(Strategy):
    name = "trend_pullback"
    allowed_regimes = frozenset({MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN})

    def evaluate(self, context: StrategyContext) -> Signal:
        if not self.is_active_for(context.regime.regime):
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason=f"{self.name} inactive for regime {context.regime.regime.value}",
            )
        if context.mtf and context.mtf.conflict:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="major multi-timeframe conflict",
            )

        params = parameters_for_family(context.family)
        swings = recent_swings(context.candles)
        lows = [swing for swing in swings if swing.kind == "LOW"]
        highs = [swing for swing in swings if swing.kind == "HIGH"]
        if len(lows) < 2 or len(highs) < 2:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="not enough swing structure for pullback",
            )

        atr_value = latest_atr(context.candles)
        entry = context.candles[-1].close
        bullish = context.regime.structure_trend is StructureTrend.UPTREND
        bearish = context.regime.structure_trend is StructureTrend.DOWNTREND
        if context.mtf and context.mtf.context_bias is Bias.BULLISH:
            bullish = True
        if context.mtf and context.mtf.context_bias is Bias.BEARISH:
            bearish = True

        if bullish:
            invalidation = lows[-1].price
            if entry <= invalidation:
                return no_trade_signal(
                    instrument=context.instrument,
                    strategy=self.name,
                    regime=context.regime.regime,
                    reason="entry is below bullish invalidation",
                )
            stop_loss = invalidation - (atr_value * params.stop_buffer_atr)
            take_profit = rr_target(entry, stop_loss, TradeAction.BUY, params.target_rr)
            score = _score_pullback(entry=entry, reference=lows[-1].price, atr_value=atr_value)
            return Signal(
                signal_id=new_signal_id(),
                instrument=context.instrument,
                action=TradeAction.BUY,
                strategy=self.name,
                setup_score=score,
                regime=context.regime.regime,
                entry=entry,
                invalidation=invalidation,
                proposed_sl=stop_loss,
                proposed_tp=take_profit,
                expected_rr=params.target_rr,
                reasons=("trend structure bullish", "pullback near last higher low"),
            )

        if bearish:
            invalidation = highs[-1].price
            if entry >= invalidation:
                return no_trade_signal(
                    instrument=context.instrument,
                    strategy=self.name,
                    regime=context.regime.regime,
                    reason="entry is above bearish invalidation",
                )
            stop_loss = invalidation + (atr_value * params.stop_buffer_atr)
            take_profit = rr_target(entry, stop_loss, TradeAction.SELL, params.target_rr)
            score = _score_pullback(entry=entry, reference=highs[-1].price, atr_value=atr_value)
            return Signal(
                signal_id=new_signal_id(),
                instrument=context.instrument,
                action=TradeAction.SELL,
                strategy=self.name,
                setup_score=score,
                regime=context.regime.regime,
                entry=entry,
                invalidation=invalidation,
                proposed_sl=stop_loss,
                proposed_tp=take_profit,
                expected_rr=params.target_rr,
                reasons=("trend structure bearish", "pullback near last lower high"),
            )

        return no_trade_signal(
            instrument=context.instrument,
            strategy=self.name,
            regime=context.regime.regime,
            reason="trend direction is not usable",
            blocker=RejectionReason.STRATEGY_BLOCKED,
        )


def _score_pullback(*, entry: float, reference: float, atr_value: float) -> int:
    distance_atr = abs(entry - reference) / atr_value if atr_value else 99
    score = 90 - int(distance_atr * 10)
    return max(0, min(100, score))

