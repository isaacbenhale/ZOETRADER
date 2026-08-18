from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from zoetrading.config import load_app_config
from zoetrading.domain import RuntimeMode
from zoetrading.journal import JournalStore
from zoetrading.market import MT5Client
from zoetrading.risk import AccountRiskState
from zoetrading.runtime import RuntimeEngine
from zoetrading.main import cli


class FakeOperationalMT5:
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

    def initialize(self, **kwargs) -> bool:
        self.connected = True
        return True

    def terminal_info(self):
        return SimpleNamespace(connected=True) if self.connected else None

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
        closes = [
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
        rows = []
        for index, close in enumerate(closes[-count:]):
            rows.append(
                {
                    "time": now - ((len(closes) - index) * 60),
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


class RuntimeCliTests(unittest.TestCase):
    def test_cli_default_bootstrap_still_works(self) -> None:
        self.assertEqual(cli([]), 0)

    def test_runtime_healthcheck_and_scan_once_with_fake_mt5(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            journal_path = root / "trading.db"
            status_file = root / "zoetrading_status.csv"
            config = load_app_config("config")
            client = MT5Client(FakeOperationalMT5())
            client.connect()
            with JournalStore(journal_path) as journal:
                engine = RuntimeEngine(config, mt5_client=client, journal=journal, status_file=status_file)
                ok, errors = engine.healthcheck()
                result = engine.scan_once(
                    mode=RuntimeMode.MONITORING,
                    account_state=AccountRiskState(equity=10_000),
                    candle_count=22,
                )
                summary = journal.analytics_summary()

            self.assertTrue(ok)
            self.assertEqual(errors, ())
            self.assertGreater(result.scanned, 0)
            self.assertTrue(status_file.exists())
            self.assertIn("status,RUNNING", status_file.read_text(encoding="ascii"))
            self.assertGreater(summary["decisions"], 0)


if __name__ == "__main__":
    unittest.main()

