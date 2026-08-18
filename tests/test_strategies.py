from datetime import UTC, datetime, timedelta
import unittest

from zoetrading.analysis import RegimeAssessment, StructureTrend, VolatilityState
from zoetrading.domain import Candle, InstrumentFamily, MarketRegime, RejectionReason, TradeAction
from zoetrading.strategies import (
    BreakoutRetestStrategy,
    RangeReversalStrategy,
    StrategyContext,
    StrategyEngine,
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

        self.assertEqual(len(result.signals), 3)
        self.assertEqual(len(result.trade_signals), 1)
        self.assertEqual(result.stats["trend_pullback"].produced_signals, 1)
        self.assertEqual(result.stats["breakout_retest"].blocked, 1)
        self.assertEqual(result.stats["range_reversal"].blocked, 1)


if __name__ == "__main__":
    unittest.main()

