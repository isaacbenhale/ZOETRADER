import unittest
from datetime import UTC, datetime, timedelta

from zoetrading.analysis import RegimeAssessment, StructureTrend, VolatilityState
from zoetrading.domain import Candle, InstrumentFamily, MarketRegime, RejectionReason, TradeAction
from zoetrading.strategies import (
    BreakoutRetestStrategy,
    MeanReversionStrategy,
    MomentumBreakoutStrategy,
    RangeReversalStrategy,
    ReversalStrategy,
    StrategyContext,
    StrategyEngine,
    StructureContinuationStrategy,
    TrendPullbackStrategy,
    default_strategies,
    parameters_for_family,
)


def make_candles(closes: list[float]) -> tuple[Candle, ...]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return tuple(
        Candle(
            instrument="EURUSD",
            timeframe="M1",
            timestamp=start + timedelta(minutes=index),
            open=close - 0.05,
            high=close + 0.1,
            low=close - 0.1,
            close=close,
            tick_volume=100,
            spread=10,
            real_volume=0,
        )
        for index, close in enumerate(closes)
    )


def context(
    regime: MarketRegime,
    candles: tuple[Candle, ...],
    *,
    family: InstrumentFamily = InstrumentFamily.FOREX,
    structure: StructureTrend = StructureTrend.UPTREND,
) -> StrategyContext:
    return StrategyContext(
        instrument="EURUSD",
        family=family,
        timeframe="M1",
        candles=candles,
        regime=RegimeAssessment(
            regime=regime,
            structure_trend=structure,
            volatility=VolatilityState.NORMAL,
            reasons=("fixture",),
        ),
    )


UPTREND_CANDLES = make_candles(
    [
        10,
        11,
        13,
        10,
        9,
        12,
        15,
        12,
        11,
        14,
        17,
        14,
        13,
        16,
        19,
        16,
        15,
        18,
        21,
        18,
        17,
        20,
    ]
)

BREAKOUT_CANDLES = make_candles(
    [
        10,
        10.2,
        10.1,
        10.3,
        10.0,
        10.4,
        10.2,
        10.3,
        10.1,
        10.5,
        11.0,
        10.55,
        10.7,
        10.8,
        11.2,
    ]
)

RANGE_CANDLES = make_candles(
    [
        10,
        12,
        10,
        12,
        10,
        12,
        10,
        12,
        10,
        12,
        10,
        12,
        10,
        12,
        10,
        12,
        10,
        12,
        10,
        12,
        10,
        10.05,
    ]
)

# A support forms right at entry, but the only confirmed resistance sits far
# below entry (an earlier, lower-level range) -- there is no confirmed edge
# above entry to target. Regression fixture for a bug where the strategy
# capped the BUY take-profit at that stale resistance, producing a take
# profit below the stop loss (see tasks/21-auto-mode-execution.md context).
RANGE_NO_TARGET_ABOVE_ENTRY_CANDLES = make_candles(
    [
        10.0, 10.0, 10.0,
        10.0, 10.3, 10.0, 10.3, 10.0, 10.05,
        12.0,
        14.3, 14.0, 14.6, 14.0, 14.05,
    ]
)

STRUCTURE_CONTINUATION_CANDLES = make_candles(
    [10, 10.5, 10.2, 10.8, 10.4, 11.2, 10.9, 11.8, 11.4, 12.5, 12.1, 13.2, 12.8, 14.0, 13.6]
)

MOMENTUM_BREAKOUT_CANDLES = make_candles(
    [
        10, 10.05, 9.95, 10.1, 9.9, 10.05, 9.95, 10.1, 9.9, 10.05,
        9.95, 10.1, 9.9, 10.05, 9.95,
        10.8, 11.5, 12.3, 13.2, 14.2,
    ]
)

MEAN_REVERSION_CANDLES = make_candles(
    [
        10.0, 10.281, 10.514, 10.649, 10.649, 10.514, 10.281, 10.0, 9.719, 9.486,
        9.351, 9.351, 9.486, 9.719, 10.0, 10.281, 10.514, 10.649, 10.649,
        9.2, 8.7, 8.2,
    ]
)

REVERSAL_CANDLES = make_candles(
    [10, 10.3, 10.1, 10.6, 10.4, 11.0, 10.8, 11.6, 11.3, 12.2, 12.0, 13.0, 12.7, 13.6, 13.3]
    + [14.0, 14.2, 14.0, 14.15, 14.1]
)


class StrategyTests(unittest.TestCase):
    def test_trend_pullback_returns_normalized_trade_signal(self) -> None:
        signal = TrendPullbackStrategy().evaluate(
            context(MarketRegime.TRENDING_UP, UPTREND_CANDLES, structure=StructureTrend.UPTREND)
        )

        self.assertEqual(signal.action, TradeAction.BUY)
        self.assertEqual(signal.strategy, "trend_pullback")
        self.assertGreaterEqual(signal.setup_score, 0)
        self.assertIsNotNone(signal.entry)
        self.assertIsNotNone(signal.proposed_sl)
        self.assertIsNotNone(signal.proposed_tp)
        self.assertEqual(signal.blockers, ())

    def test_inactive_strategy_returns_no_trade_with_reason(self) -> None:
        signal = TrendPullbackStrategy().evaluate(
            context(MarketRegime.RANGING, RANGE_CANDLES, structure=StructureTrend.RANGE)
        )

        self.assertEqual(signal.action, TradeAction.NO_TRADE)
        self.assertIn(RejectionReason.STRATEGY_BLOCKED, signal.blockers)
        self.assertIn("inactive", signal.reasons[0])

    def test_breakout_retest_returns_trade_in_breakout_regime(self) -> None:
        signal = BreakoutRetestStrategy().evaluate(
            context(MarketRegime.BREAKOUT, BREAKOUT_CANDLES, structure=StructureTrend.RANGE)
        )

        self.assertEqual(signal.action, TradeAction.BUY)
        self.assertEqual(signal.strategy, "breakout_retest")
        self.assertIn("retest confirmed", signal.reasons)

    def test_range_reversal_returns_trade_near_range_edge(self) -> None:
        signal = RangeReversalStrategy().evaluate(
            context(MarketRegime.RANGING, RANGE_CANDLES, structure=StructureTrend.RANGE)
        )

        self.assertEqual(signal.action, TradeAction.BUY)
        self.assertEqual(signal.strategy, "range_reversal")
        self.assertIn("range support confirmed", signal.reasons)
        self.assertLess(signal.proposed_sl, signal.entry)
        self.assertGreater(signal.proposed_tp, signal.entry)

    def test_range_reversal_refuses_a_target_below_entry(self) -> None:
        signal = RangeReversalStrategy().evaluate(
            context(MarketRegime.RANGING, RANGE_NO_TARGET_ABOVE_ENTRY_CANDLES, structure=StructureTrend.RANGE)
        )

        self.assertEqual(signal.action, TradeAction.NO_TRADE)
        self.assertIn(RejectionReason.STRATEGY_BLOCKED, signal.blockers)

    def test_structure_continuation_returns_trade_after_break_of_structure(self) -> None:
        signal = StructureContinuationStrategy().evaluate(
            context(MarketRegime.TRENDING_UP, STRUCTURE_CONTINUATION_CANDLES, structure=StructureTrend.UPTREND)
        )

        self.assertEqual(signal.action, TradeAction.BUY)
        self.assertEqual(signal.strategy, "structure_continuation")
        self.assertIn("break of structure confirmed", signal.reasons)

    def test_structure_continuation_blocked_without_break_of_structure(self) -> None:
        signal = StructureContinuationStrategy().evaluate(
            context(MarketRegime.TRENDING_UP, UPTREND_CANDLES, structure=StructureTrend.UPTREND)
        )

        self.assertEqual(signal.action, TradeAction.NO_TRADE)

    def test_momentum_breakout_returns_trade_with_momentum_and_volatility_confirmation(self) -> None:
        signal = MomentumBreakoutStrategy().evaluate(
            context(MarketRegime.BREAKOUT, MOMENTUM_BREAKOUT_CANDLES, structure=StructureTrend.RANGE)
        )

        self.assertEqual(signal.action, TradeAction.BUY)
        self.assertEqual(signal.strategy, "momentum_breakout")
        self.assertIn("momentum confirms breakout", signal.reasons)
        self.assertIn("volatility expanding", signal.reasons)

    def test_momentum_breakout_blocked_without_momentum(self) -> None:
        signal = MomentumBreakoutStrategy().evaluate(
            context(MarketRegime.BREAKOUT, BREAKOUT_CANDLES, structure=StructureTrend.RANGE)
        )

        self.assertEqual(signal.action, TradeAction.NO_TRADE)

    def test_mean_reversion_returns_trade_when_oversold_and_extended(self) -> None:
        signal = MeanReversionStrategy().evaluate(
            context(MarketRegime.RANGING, MEAN_REVERSION_CANDLES, structure=StructureTrend.RANGE)
        )

        self.assertEqual(signal.action, TradeAction.BUY)
        self.assertEqual(signal.strategy, "mean_reversion")
        self.assertIn("price oversold and extended below mean", signal.reasons)
        self.assertIsNotNone(signal.proposed_sl)

    def test_mean_reversion_blocked_when_not_extended(self) -> None:
        signal = MeanReversionStrategy().evaluate(
            context(MarketRegime.RANGING, RANGE_CANDLES, structure=StructureTrend.RANGE)
        )

        self.assertEqual(signal.action, TradeAction.NO_TRADE)

    def test_reversal_returns_trade_on_structural_and_momentum_confirmation(self) -> None:
        signal = ReversalStrategy().evaluate(
            context(MarketRegime.TRENDING_UP, REVERSAL_CANDLES, structure=StructureTrend.UPTREND)
        )

        self.assertEqual(signal.action, TradeAction.SELL)
        self.assertEqual(signal.strategy, "reversal")
        self.assertIn("lower high breaks trend structure", signal.reasons)

    def test_reversal_blocked_without_confirmation(self) -> None:
        signal = ReversalStrategy().evaluate(
            context(MarketRegime.TRENDING_UP, UPTREND_CANDLES, structure=StructureTrend.UPTREND)
        )

        self.assertEqual(signal.action, TradeAction.NO_TRADE)

    def test_parameters_are_separated_by_instrument_family(self) -> None:
        forex = parameters_for_family(InstrumentFamily.FOREX)
        synthetic = parameters_for_family(InstrumentFamily.SYNTHETIC)

        self.assertNotEqual(forex.target_rr, synthetic.target_rr)
        self.assertLess(forex.stop_buffer_atr, synthetic.stop_buffer_atr)

    def test_strategy_engine_records_stats_and_blocks_inactive_strategies(self) -> None:
        engine = StrategyEngine(default_strategies())
        result = engine.evaluate(
            context(MarketRegime.TRENDING_UP, UPTREND_CANDLES, structure=StructureTrend.UPTREND)
        )

        self.assertEqual(len(result.signals), 7)
        self.assertGreaterEqual(len(result.trade_signals), 1)
        self.assertEqual(result.stats["trend_pullback"].produced_signals, 1)
        self.assertEqual(result.stats["breakout_retest"].blocked, 1)
        self.assertEqual(result.stats["momentum_breakout"].blocked, 1)
        self.assertEqual(result.stats["range_reversal"].blocked, 1)
        self.assertEqual(result.stats["mean_reversion"].blocked, 1)


if __name__ == "__main__":
    unittest.main()

