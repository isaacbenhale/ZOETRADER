from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
import unittest

from zoetrading.market import (
    CandleCache,
    MT5Client,
    MT5ConnectionError,
    MarketDataEngine,
    StaleMarketDataError,
    SymbolUnavailableError,
)


class FakeMT5:
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_M30 = 30
    TIMEFRAME_H1 = 60
    TIMEFRAME_H4 = 240
    TIMEFRAME_D1 = 1440
    POSITION_TYPE_BUY = 0

    def __init__(self) -> None:
        self.connected = False
        self.symbols = {
            "EURUSD": SimpleNamespace(
                visible=True,
                trade_mode=1,
                digits=5,
                point=0.00001,
                volume_min=0.01,
                volume_max=100.0,
                volume_step=0.01,
            )
        }
        self.candle_calls = 0
        self.fail_candles = False
        self.selected_symbols: list[str] = []

    def initialize(self, **kwargs) -> bool:
        self.connected = True
        return True

    def shutdown(self) -> None:
        self.connected = False

    def terminal_info(self):
        if not self.connected:
            return None
        return SimpleNamespace(connected=True)

    def last_error(self):
        return (1, "fake error")

    def symbol_info(self, symbol: str):
        return self.symbols.get(symbol)

    def symbol_select(self, symbol: str, enabled: bool) -> bool:
        if symbol not in self.symbols:
            return False
        self.selected_symbols.append(symbol)
        self.symbols[symbol].visible = enabled
        return True

    def symbol_info_tick(self, symbol: str):
        if symbol not in self.symbols:
            return None
        return SimpleNamespace(
            time=1_700_000_000,
            bid=1.10000,
            ask=1.10020,
            last=1.10010,
            volume=120,
        )

    def copy_rates_from_pos(self, symbol: str, timeframe: int, start: int, count: int):
        if self.fail_candles:
            return None
        self.candle_calls += 1
        now = int(datetime.now(UTC).timestamp())
        return [
            {
                "time": now - 60,
                "open": 1.1,
                "high": 1.101,
                "low": 1.099,
                "close": 1.1005,
                "tick_volume": 100,
                "spread": 20,
                "real_volume": 0,
            }
        ][:count]

    def positions_get(self, **kwargs):
        symbol = kwargs.get("symbol", "EURUSD")
        return (
            SimpleNamespace(
                ticket=123,
                symbol=symbol,
                type=self.POSITION_TYPE_BUY,
                volume=0.01,
                price_open=1.1,
                time=1_700_000_000,
                sl=1.09,
                tp=1.12,
                profit=2.5,
            ),
        )


class MarketDataTests(unittest.TestCase):
    def test_disconnected_mt5_is_explicit(self) -> None:
        client = MT5Client(FakeMT5())

        with self.assertRaisesRegex(MT5ConnectionError, "not connected"):
            client.get_tick("EURUSD")

    def test_symbol_unavailable_is_explicit(self) -> None:
        fake = FakeMT5()
        client = MT5Client(fake)
        client.connect()

        with self.assertRaisesRegex(SymbolUnavailableError, "Symbol unavailable"):
            client.get_symbol_info("UNKNOWN")

    def test_client_reads_tick_candles_symbol_info_and_positions(self) -> None:
        fake = FakeMT5()
        client = MT5Client(fake)
        client.connect()

        symbol_info = client.get_symbol_info("EURUSD")
        tick = client.get_tick("EURUSD")
        candles = client.get_candles("EURUSD", "M1", 1)
        positions = client.get_open_positions("EURUSD")

        self.assertEqual(symbol_info.instrument, "EURUSD")
        self.assertEqual(tick.spread, 0.00019999999999997797)
        self.assertEqual(candles[0].timeframe, "M1")
        self.assertEqual(positions[0].position_id, "123")

    def test_collect_instrument_keeps_symbol_errors_isolated(self) -> None:
        fake = FakeMT5()
        client = MT5Client(fake)
        client.connect()
        engine = MarketDataEngine(client)

        failed = engine.collect_instrument("UNKNOWN", ("M1",))
        ok = engine.collect_instrument("EURUSD", ("M1",))

        self.assertFalse(failed.ok)
        self.assertTrue(ok.ok)
        self.assertIn("M1", ok.candles_by_timeframe)

    def test_candle_cache_is_used_when_refresh_fails(self) -> None:
        fake = FakeMT5()
        client = MT5Client(fake)
        client.connect()
        engine = MarketDataEngine(client)

        first = engine.collect_instrument("EURUSD", ("M1",))
        fake.fail_candles = True
        second = engine.collect_instrument("EURUSD", ("M1",))

        self.assertTrue(first.ok)
        self.assertFalse(second.ok)
        self.assertEqual(first.candles_by_timeframe["M1"], second.candles_by_timeframe["M1"])

    def test_stale_snapshot_is_rejected_before_decision_pipeline(self) -> None:
        fake = FakeMT5()
        client = MT5Client(fake)
        client.connect()
        cache = CandleCache()
        engine = MarketDataEngine(client, cache)
        fresh = engine.collect_instrument("EURUSD", ("M1",))
        old_candle = fresh.candles_by_timeframe["M1"][0]
        cache.put(
            "EURUSD",
            "M1",
            (
                old_candle.__class__(
                    instrument=old_candle.instrument,
                    timeframe=old_candle.timeframe,
                    timestamp=datetime.now(UTC) - timedelta(hours=1),
                    open=old_candle.open,
                    high=old_candle.high,
                    low=old_candle.low,
                    close=old_candle.close,
                    tick_volume=old_candle.tick_volume,
                    spread=old_candle.spread,
                    real_volume=old_candle.real_volume,
                ),
            ),
        )

        with self.assertRaisesRegex(StaleMarketDataError, "Stale market data"):
            engine.build_snapshot("EURUSD", "M1", max_age_seconds=30)


if __name__ == "__main__":
    unittest.main()

