"""Range edge reversal strategy."""

from __future__ import annotations

from zoetrading.analysis import find_price_levels
from zoetrading.domain import MarketRegime, Signal, TradeAction
from zoetrading.journal import new_signal_id
from zoetrading.strategies.base import Strategy, StrategyContext
from zoetrading.strategies.helpers import latest_atr, no_trade_signal, recent_swings, rr_target
from zoetrading.strategies.parameters import parameters_for_family


class RangeReversalStrategy(Strategy):
    name = "range_reversal"
    allowed_regimes = frozenset({MarketRegime.RANGING})

    def evaluate(self, context: StrategyContext) -> Signal:
        if not self.is_active_for(context.regime.regime):
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason=f"{self.name} inactive for regime {context.regime.regime.value}",
            )

        params = parameters_for_family(context.family)
        atr_value = latest_atr(context.candles)
        levels = find_price_levels(
            recent_swings(context.candles),
            tolerance=atr_value * params.range_edge_tolerance_atr,
        )
        supports = [level for level in levels if level.kind == "SUPPORT"]
        resistances = [level for level in levels if level.kind == "RESISTANCE"]
        if not supports or not resistances:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="range edges are not confirmed",
            )

        entry = context.candles[-1].close
        support = min(supports, key=lambda level: abs(entry - level.price))
        resistance = min(resistances, key=lambda level: abs(entry - level.price))
        edge_tolerance = atr_value * params.range_edge_tolerance_atr

        if abs(entry - support.price) <= edge_tolerance:
            # The take-profit target must sit on the far side of the range, above
            # entry: a resistance level below/at entry cannot cap a BUY target
            # without producing an invalid (or even inverted) take profit.
            resistances_above_entry = [level for level in resistances if level.price > entry]
            if not resistances_above_entry:
                return no_trade_signal(
                    instrument=context.instrument,
                    strategy=self.name,
                    regime=context.regime.regime,
                    reason="no confirmed range resistance above entry to target",
                )
            target = min(resistances_above_entry, key=lambda level: level.price)
            stop_loss = support.price - (atr_value * params.stop_buffer_atr)
            take_profit = min(rr_target(entry, stop_loss, TradeAction.BUY, params.target_rr), target.price)
            if not stop_loss < entry < take_profit:
                return no_trade_signal(
                    instrument=context.instrument,
                    strategy=self.name,
                    regime=context.regime.regime,
                    reason="range reversal setup failed sl/tp sanity check",
                )
            return Signal(
                signal_id=new_signal_id(),
                instrument=context.instrument,
                action=TradeAction.BUY,
                strategy=self.name,
                setup_score=80,
                regime=context.regime.regime,
                entry=entry,
                invalidation=support.price,
                proposed_sl=stop_loss,
                proposed_tp=take_profit,
                expected_rr=params.target_rr,
                reasons=("range support confirmed", "price near lower range edge"),
            )

        if abs(entry - resistance.price) <= edge_tolerance:
            # Symmetric guard: the SELL target must sit on the far side of the
            # range, below entry.
            supports_below_entry = [level for level in supports if level.price < entry]
            if not supports_below_entry:
                return no_trade_signal(
                    instrument=context.instrument,
                    strategy=self.name,
                    regime=context.regime.regime,
                    reason="no confirmed range support below entry to target",
                )
            target = max(supports_below_entry, key=lambda level: level.price)
            stop_loss = resistance.price + (atr_value * params.stop_buffer_atr)
            take_profit = max(rr_target(entry, stop_loss, TradeAction.SELL, params.target_rr), target.price)
            if not stop_loss > entry > take_profit:
                return no_trade_signal(
                    instrument=context.instrument,
                    strategy=self.name,
                    regime=context.regime.regime,
                    reason="range reversal setup failed sl/tp sanity check",
                )
            return Signal(
                signal_id=new_signal_id(),
                instrument=context.instrument,
                action=TradeAction.SELL,
                strategy=self.name,
                setup_score=80,
                regime=context.regime.regime,
                entry=entry,
                invalidation=resistance.price,
                proposed_sl=stop_loss,
                proposed_tp=take_profit,
                expected_rr=params.target_rr,
                reasons=("range resistance confirmed", "price near upper range edge"),
            )

        return no_trade_signal(
            instrument=context.instrument,
            strategy=self.name,
            regime=context.regime.regime,
            reason="price is not near a confirmed range edge",
        )

