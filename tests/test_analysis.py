from datetime import UTC, datetime, timedelta
import unittest

from zoetrading.analysis import (
    StructureTrend,
    VolatilityState,
    atr,
    classify_volatility,
    detect_breakout,
    detect_retest,
    detect_swings,
    ema,
    find_price_levels,
    infer_market_structure,
    macd,
    rate_of_change,
    rsi,
    sma,
)
from zoetrading.domain import Candle


def make_candles(prices: list[tuple[float, float, float, float]]) -> tuple[Candle, ...]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return tuple(
        Candle(
            instrument="EURUSD",
            timeframe="M1",
            timestamp=start + timedelta(minutes=index),
            open=open_,
            high=high,
            low=low,
            close=close,
            tick_volume=100,
            spread=10,
            real_volume=0,
        )
        for index, (open_, high, low, close) in enumerate(prices)
    )


class AnalysisIndicatorTests(unittest.TestCase):
    def test_sma_ema_and_roc_are_deterministic(self) -> None:
        values = [1, 2, 3, 4, 5]

        self.assertEqual(sma(values, 3), [None, None, 2.0, 3.0, 4.0])
        self.assertEqual(ema(values, 3), [None, None, 2.0, 3.0, 4.0])
        self.assertEqual(rate_of_change(values, 2), [None, None, 200.0, 100.0, 66.66666666666666])

    def test_rsi_reaches_100_when_no_losses_exist(self) -> None:
        values = list(range(1, 18))

        output = rsi(values, period=14)

        self.assertEqual(output[:14], [None] * 14)
        self.assertEqual(output[14], 100.0)
        self.assertEqual(output[-1], 100.0)

    def test_atr_uses_true_range(self) -> None:
        candles = make_candles(
            [
                (10, 12, 9, 11),
                (11, 13, 10, 12),
                (12, 14, 11, 13),
                (13, 15, 12, 14),
            ]
        )

        output = atr(candles, period=2)

        self.assertEqual(output[:2], [None, None])
        self.assertEqual(output[2], 3.0)
        self.assertEqual(output[3], 3.0)

    def test_macd_returns_aligned_series(self) -> None:
        values = [float(index) for index in range(1, 40)]

        macd_line, signal_line, histogram = macd(values)

        self.assertEqual(len(macd_line), len(values))
        self.assertEqual(len(signal_line), len(values))
        self.assertEqual(len(histogram), len(values))
        self.assertIsNone(macd_line[24])
        self.assertIsNotNone(macd_line[25])
        self.assertIsNotNone(histogram[-1])


class AnalysisStructureTests(unittest.TestCase):
    def test_detect_swings_and_uptrend_structure(self) -> None:
        candles = make_candles(
            [
                (10, 10, 8, 9),
                (9, 11, 8.5, 10),
                (10, 15, 9, 14),
                (14, 13, 9.5, 10),
                (10, 12, 7, 8),
                (8, 14, 8, 13),
                (13, 18, 12, 17),
                (17, 16, 13, 14),
                (14, 15, 10, 11),
                (11, 17, 11, 16),
            ]
        )

        swings = detect_swings(candles, left=1, right=1)
        structure = infer_market_structure(swings)

        self.assertEqual([(swing.kind, swing.index, swing.price) for swing in swings], [
            ("HIGH", 2, 15),
            ("LOW", 4, 7),
            ("HIGH", 6, 18),
            ("LOW", 8, 10),
        ])
        self.assertEqual(structure.trend, StructureTrend.UPTREND)
        self.assertEqual(structure.description, "HH/HL")

    def test_find_support_and_resistance_levels(self) -> None:
        candles = make_candles(
            [
                (10, 10, 8, 9),
                (9, 15, 8.5, 14),
                (14, 13, 9.5, 10),
                (10, 12, 7, 8),
                (8, 15.1, 8, 13),
                (13, 14, 9.6, 10),
                (10, 12, 7.1, 8),
                (8, 16, 8, 15),
            ]
        )

        levels = find_price_levels(detect_swings(candles, left=1, right=1), tolerance=0.2)

        self.assertEqual(len(levels), 2)
        self.assertEqual(levels[0].kind, "RESISTANCE")
        self.assertAlmostEqual(levels[0].price, 15.05)
        self.assertEqual(levels[1].kind, "SUPPORT")
        self.assertAlmostEqual(levels[1].price, 7.05)

    def test_breakout_and_retest_detection(self) -> None:
        candles = make_candles(
            [
                (10, 11, 9, 10),
                (10, 12, 9, 11),
                (11, 13, 10, 12.6),
                (12.6, 13, 11.9, 12.55),
            ]
        )

        breakout = detect_breakout(candles, resistance=12.5, support=9.0, lookback=2)

        self.assertIsNotNone(breakout)
        assert breakout is not None
        self.assertEqual(breakout.direction, "UP")
        self.assertTrue(detect_retest(candles, breakout, tolerance=0.6))

    def test_classify_volatility_from_atr_series(self) -> None:
        self.assertEqual(
            classify_volatility([1.0] * 20 + [2.0], lookback=20, high_ratio=1.5),
            VolatilityState.HIGH,
        )
        self.assertEqual(
            classify_volatility([1.0] * 20 + [0.4], lookback=20, low_ratio=0.7),
            VolatilityState.LOW,
        )


if __name__ == "__main__":
    unittest.main()
