"""Structure continuation strategy: BOS, retracement, then structural resumption."""

from __future__ import annotations

from zoetrading.analysis import Bias, StructureTrend, detect_swings, infer_market_structure
from zoetrading.domain import MarketRegime, RejectionReason, Signal, TradeAction
from zoetrading.journal import new_signal_id
from zoetrading.strategies.base import Strategy, StrategyContext
from zoetrading.strategies.helpers import latest_atr, no_trade_signal, rr_target
from zoetrading.strategies.parameters import parameters_for_family


class StructureContinuationStrategy(Strategy):
    name = "structure_continuation"
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

        structure = infer_market_structure(detect_swings(context.candles, left=1, right=1))
        if not structure.broke_structure:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="no recent break of structure to continue",
            )
        if structure.last_high is None or structure.last_low is None:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="not enough swing structure for continuation",
            )

        params = parameters_for_family(context.family)
        atr_value = latest_atr(context.candles)
        entry = context.candles[-1].close

        bullish = structure.trend is StructureTrend.UPTREND
        bearish = structure.trend is StructureTrend.DOWNTREND
        if context.mtf and context.mtf.context_bias is Bias.BULLISH:
            bullish = True
        if context.mtf and context.mtf.context_bias is Bias.BEARISH:
            bearish = True

        if bullish:
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
            score = _score_continuation(
                last_price=structure.last_high.price,
                previous_price=structure.previous_high.price if structure.previous_high else None,
                atr_value=atr_value,
            )
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
                reasons=("break of structure confirmed", "continuation after retracement"),
            )

        if bearish:
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
            score = _score_continuation(
                last_price=structure.last_low.price,
                previous_price=structure.previous_low.price if structure.previous_low else None,
                atr_value=atr_value,
            )
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
                reasons=("break of structure confirmed", "continuation after retracement"),
            )

        return no_trade_signal(
            instrument=context.instrument,
            strategy=self.name,
            regime=context.regime.regime,
            reason="structure direction is not usable",
            blocker=RejectionReason.STRATEGY_BLOCKED,
        )


def _score_continuation(*, last_price: float | None, previous_price: float | None, atr_value: float) -> int:
    if last_price is None or previous_price is None or atr_value == 0:
        return 70
    strength_atr = abs(last_price - previous_price) / atr_value
    score = 75 + int(min(strength_atr, 2.0) * 8)
    return max(0, min(100, score))
