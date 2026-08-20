from datetime import UTC, datetime
import math
from pathlib import Path
from types import SimpleNamespace
import unittest

from zoetrading.backtesting import run_library_backtest
from zoetrading.config.models import (
    AppConfig,
    DecisionConfig,
    ExecutionConfig,
    InstrumentConfig,
    InstrumentsConfig,
    MarketConfig,
    RiskConfig,
    SettingsConfig,
)
from zoetrading.domain import InstrumentFamily, RuntimeMode
from zoetrading.market import MT5Client, MarketDataEngine


class FakeHistoryMT5:
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_M30 = 30
    TIMEFRAME_H1 = 60
    TIMEFRAME_H4 = 240
    TIMEFRAME_D1 = 1440

    def __init__(self, closes: list[float]) -> None:
        self.closes = closes

    def initialize(self, **kwargs) -> bool:
        return True

    def terminal_info(self):
        return SimpleNamespace(connected=True)

    def symbol_info(self, symbol: str):
        return SimpleNamespace(
            visible=True,
            trade_mode=1,
            digits=5,
            point=0.00001,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
        )

    def symbol_select(self, symbol: str, enabled: bool) -> bool:
        return True

    def symbol_info_tick(self, symbol: str):
        return SimpleNamespace(time=int(datetime.now(UTC).timestamp()), bid=20.0, ask=20.2, last=20.1, volume=1)

    def copy_rates_from_pos(self, symbol: str, timeframe: int, start: int, count: int):
        now = int(datetime.now(UTC).timestamp())
        window = self.closes[-count:]
        rows = []
        for index, close in enumerate(window):
            rows.append(
                {
                    "time": now - ((len(window) - index) * 60),
                    "open": close - 0.05,
                    "high": close + 0.1,
                    "low": close - 0.1,
                    "close": close,
                    "tick_volume": 100,
                    "spread": 10,
                    "real_volume": 0,
                }
            )
        return rows

    def positions_get(self, **kwargs):
        return ()

    def last_error(self):
        return (0, "ok")


def _synthetic_series() -> list[float]:
    """A mixed uptrend / range / breakout / pullback series to exercise every regime."""

    values: list[float] = []
    price = 10.0
    for index in range(20):
        price += 0.3 if index % 2 == 0 else -0.1
        values.append(round(price, 3))

    base = values[-1]
    for index in range(20):
        values.append(round(base + 0.4 * math.sin(index / 2), 3))

    price = values[-1]
    for index in range(20):
        price += 0.35
        values.append(round(price, 3))

    price = values[-1]
    for index in range(20):
        price -= 0.25 if index % 3 != 0 else -0.05
        values.append(round(price, 3))
    return values


def _config(symbol: str = "EURUSD") -> AppConfig:
    return AppConfig(
        settings=SettingsConfig(
            environment="test",
            mode=RuntimeMode.MONITORING,
            log_dir=Path("logs"),
            data_dir=Path("data"),
            market=MarketConfig(
                refresh_interval_seconds=5,
                context_timeframes=("H1",),
                setup_timeframes=("M15",),
                timing_timeframes=("M5",),
            ),
            decision=DecisionConfig(minimum_setup_score=80, allow_no_trade=True),
            execution=ExecutionConfig(require_fresh_market_data=True, prevent_duplicate_orders=True),
        ),
        risk=RiskConfig(
            risk_per_trade_pct=0.5,
            max_daily_loss_pct=2.0,
            max_weekly_loss_pct=5.0,
            max_open_positions=3,
            max_consecutive_losses=3,
            cooldown_minutes_after_losses=60,
            stop_loss_required=True,
            martingale=False,
        ),
        instruments=InstrumentsConfig(
            instruments=(
                InstrumentConfig(symbol=symbol, family=InstrumentFamily.FOREX, enabled=True, timeframes=("M15",)),
            )
        ),
    )


class BacktestRunnerTests(unittest.TestCase):
    def test_run_library_backtest_produces_one_result_per_strategy(self) -> None:
        config = _config()
        client = MT5Client(FakeHistoryMT5(_synthetic_series()))
        client.connect()
        market = MarketDataEngine(client)

        report = run_library_backtest(config, market, candle_count=80, lookahead_bars=8)

        self.assertEqual(report.skipped, ())
        self.assertEqual(len(report.results), 7)
        for result in report.results:
            self.assertEqual(result.instrument, "EURUSD")
            self.assertEqual(result.timeframe, "M15")
            self.assertGreaterEqual(result.metrics.trades, 0)

        ranked = report.ranked_by_expectancy
        expectancies = [result.metrics.expectancy for result in ranked]
        self.assertEqual(expectancies, sorted(expectancies, reverse=True))

    def test_run_library_backtest_skips_instrument_without_enough_history(self) -> None:
        config = _config()
        client = MT5Client(FakeHistoryMT5(_synthetic_series()[:10]))
        client.connect()
        market = MarketDataEngine(client)

        report = run_library_backtest(config, market, candle_count=80, lookahead_bars=8)

        self.assertEqual(report.results, ())
        self.assertEqual(len(report.skipped), 1)
        self.assertIn("not enough history", report.skipped[0])


if __name__ == "__main__":
    unittest.main()
