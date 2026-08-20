"""Mean reversion strategy: statistical extension reverting toward the moving average."""

from __future__ import annotations

from zoetrading.analysis import rsi, sma
from zoetrading.analysis.series import closes
from zoetrading.domain import MarketRegime, Signal, TradeAction
from zoetrading.journal import new_signal_id
from zoetrading.strategies.base import Strategy, StrategyContext
from zoetrading.strategies.helpers import latest_atr, no_trade_signal
from zoetrading.strategies.parameters import parameters_for_family


class MeanReversionStrategy(Strategy):
    name = "mean_reversion"
    allowed_regimes = frozenset({MarketRegime.RANGING})

    MEAN_PERIOD = 20
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    MIN_DEVIATION_ATR = 1.0
    INVALIDATION_LOOKBACK = 5

    def evaluate(self, context: StrategyContext) -> Signal:
        if not self.is_active_for(context.regime.regime):
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason=f"{self.name} inactive for regime {context.regime.regime.value}",
            )

        close_values = closes(context.candles)
        if len(close_values) < max(self.MEAN_PERIOD, self.RSI_PERIOD + 1):
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="not enough candles for mean reversion",
            )

        mean = sma(close_values, self.MEAN_PERIOD)[-1]
        rsi_value = rsi(close_values, self.RSI_PERIOD)[-1]
        if mean is None or rsi_value is None:
            return no_trade_signal(
                instrument=context.instrument,
                strategy=self.name,
                regime=context.regime.regime,
                reason="mean or momentum reading is unavailable",
            )

        atr_value = latest_atr(context.candles)
        entry = context.candles[-1].close
        deviation_atr = (entry - mean) / atr_value if atr_value else 0.0
        params = parameters_for_family(context.family)
        window = context.candles[-self.INVALIDATION_LOOKBACK :]

        if rsi_value <= self.RSI_OVERSOLD and deviation_atr <= -self.MIN_DEVIATION_ATR:
            invalidation = min(candle.low for candle in window)
            if entry <= invalidation:
                return no_trade_signal(
                    instrument=context.instrument,
                    strategy=self.name,
                    regime=context.regime.regime,
                    reason="entry is below recent invalidation",
                )
            stop_loss = invalidation - (atr_value * params.stop_buffer_atr)
            take_profit = mean
            return Signal(
                signal_id=new_signal_id(),
                instrument=context.instrument,
                action=TradeAction.BUY,
                strategy=self.name,
                setup_score=_score_extension(rsi_value, self.RSI_OVERSOLD, deviation_atr),
                regime=context.regime.regime,
                entry=entry,
                invalidation=invalidation,
                proposed_sl=stop_loss,
                proposed_tp=take_profit,
                expected_rr=_reward_risk(entry, stop_loss, take_profit),
                reasons=("price oversold and extended below mean", "target reversion to moving average"),
            )

        if rsi_value >= self.RSI_OVERBOUGHT and deviation_atr >= self.MIN_DEVIATION_ATR:
            invalidation = max(candle.high for candle in window)
            if entry >= invalidation:
                return no_trade_signal(
                    instrument=context.instrument,
                    strategy=self.name,
                    regime=context.regime.regime,
                    reason="entry is above recent invalidation",
                )
            stop_loss = invalidation + (atr_value * params.stop_buffer_atr)
            take_profit = mean
            return Signal(
                signal_id=new_signal_id(),
                instrument=context.instrument,
                action=TradeAction.SELL,
                strategy=self.name,
                setup_score=_score_extension(rsi_value, self.RSI_OVERBOUGHT, deviation_atr),
                regime=context.regime.regime,
                entry=entry,
                invalidation=invalidation,
                proposed_sl=stop_loss,
                proposed_tp=take_profit,
                expected_rr=_reward_risk(entry, stop_loss, take_profit),
                reasons=("price overbought and extended above mean", "target reversion to moving average"),
            )

        return no_trade_signal(
            instrument=context.instrument,
            strategy=self.name,
            regime=context.regime.regime,
            reason="price is not statistically extended from the mean",
        )


def _score_extension(rsi_value: float, threshold: float, deviation_atr: float) -> int:
    rsi_distance = abs(rsi_value - threshold)
    score = 70 + int(rsi_distance) + int(min(abs(deviation_atr), 3.0) * 5)
    return max(0, min(100, score))


def _reward_risk(entry: float, stop_loss: float, take_profit: float) -> float:
    risk = abs(entry - stop_loss)
    reward = abs(take_profit - entry)
    return round(reward / risk, 2) if risk else 0.0
