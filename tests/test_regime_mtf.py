from datetime import UTC, datetime, timedelta
import unittest

from zoetrading.analysis import (
    Bias,
    classify_market_regime,
    assess_multi_timeframe,
    strategy_allowed_for_regime,
)
from zoetrading.domain import Candle, MarketRegime, RejectionReason, TradeAction


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


class RegimeAndMTFTests(unittest.TestCase):
    def test_insufficient_data_is_chaotic_and_not_tradable(self) -> None:
        assessment = classify_market_regime(make_candles([1.0, 1.1, 1.2]), min_candles=20)

        self.assertEqual(assessment.regime, MarketRegime.CHAOTIC)
        self.assertFalse(assessment.tradable)
        self.assertIn("INSUFFICIENT_DATA", assessment.blockers)

    def test_trend_strategy_is_blocked_in_range_regime(self) -> None:
        self.assertFalse(strategy_allowed_for_regime("trend_pullback", MarketRegime.RANGING))
        self.assertTrue(strategy_allowed_for_regime("range_reversal", MarketRegime.RANGING))

    def test_breakout_strategy_is_only_allowed_in_breakout_regime(self) -> None:
        self.assertTrue(strategy_allowed_for_regime("breakout_retest", MarketRegime.BREAKOUT))
        self.assertFalse(strategy_allowed_for_regime("breakout_retest", MarketRegime.TRENDING_UP))

    def test_multi_timeframe_alignment_recommends_buy(self) -> None:
        uptrend = make_candles(
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

        context = assess_multi_timeframe(
            "EURUSD",
            {"H1": uptrend, "M15": uptrend, "M5": uptrend},
            context_timeframes=("H1",),
            setup_timeframes=("M15",),
            timing_timeframes=("M5",),
        )

        self.assertEqual(context.context_bias, Bias.BULLISH)
        self.assertEqual(context.setup_bias, Bias.BULLISH)
        self.assertTrue(context.aligned)
        self.assertFalse(context.conflict)
        self.assertEqual(context.recommended_action, TradeAction.BUY)

    def test_major_mtf_conflict_produces_no_trade(self) -> None:
        uptrend = make_candles(
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
        downtrend = make_candles(
            [
                30,
                29,
                27,
                30,
                31,
                28,
                25,
                28,
                29,
                26,
                23,
                26,
                27,
                24,
                21,
                24,
                25,
                22,
                19,
                22,
                23,
                20,
            ]
        )

        context = assess_multi_timeframe(
            "EURUSD",
            {"H1": uptrend, "M15": downtrend, "M5": downtrend},
            context_timeframes=("H1",),
            setup_timeframes=("M15",),
            timing_timeframes=("M5",),
        )

        self.assertTrue(context.conflict)
        self.assertFalse(context.aligned)
        self.assertEqual(context.recommended_action, TradeAction.NO_TRADE)
        self.assertIn(RejectionReason.STRATEGY_BLOCKED, context.blockers)


if __name__ == "__main__":
    unittest.main()

