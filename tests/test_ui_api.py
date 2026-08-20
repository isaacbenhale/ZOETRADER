from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from fastapi.testclient import TestClient

from zoetrading.market import MT5Client
from zoetrading.ui import create_app


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
            10, 11, 13, 10, 9, 12, 15, 12, 11, 14, 17, 14, 13, 16, 19, 16, 15, 18, 21, 18, 17, 20,
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


class FakeUnavailableMT5:
    def initialize(self, **kwargs) -> bool:
        return False

    def last_error(self):
        return (1, "no terminal")


class UiApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.journal_db = root / "trading.db"
        self.status_file = root / "zoetrading_status.csv"
        self.report_file = root / "backtest_report.json"

    def _client(self, mt5_client_factory=None) -> TestClient:
        app = create_app(
            config_dir="config",
            journal_db=str(self.journal_db),
            status_file=str(self.status_file),
            report_file=str(self.report_file),
            mt5_client_factory=mt5_client_factory or (lambda: MT5Client(FakeOperationalMT5())),
        )
        return TestClient(app)

    def test_health(self) -> None:
        response = self._client().get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_bootstrap_action(self) -> None:
        response = self._client().post("/api/actions/bootstrap", json={"mode": "MONITORING"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("bootstrap OK", response.json()["output"])

    def test_bootstrap_rejects_auto(self) -> None:
        response = self._client().post("/api/actions/bootstrap", json={"mode": "AUTO"})
        self.assertEqual(response.status_code, 400)

    def test_scan_rejects_auto_without_touching_mt5(self) -> None:
        response = self._client().post("/api/actions/scan", json={"mode": "AUTO", "equity": 10000})
        self.assertEqual(response.status_code, 400)

    def test_healthcheck_scan_status_and_decisions_round_trip(self) -> None:
        client = self._client()

        health = client.post("/api/actions/healthcheck")
        self.assertEqual(health.status_code, 200)
        self.assertTrue(health.json()["ok"])

        scan = client.post(
            "/api/actions/scan",
            json={"mode": "MONITORING", "equity": 10000, "candle_count": 22},
        )
        self.assertEqual(scan.status_code, 200)
        self.assertGreater(scan.json()["scanned"], 0)

        status = client.get("/api/status")
        self.assertEqual(status.status_code, 200)
        self.assertIn("status", status.json()["status_file"])
        self.assertGreater(status.json()["journal"]["decisions"], 0)

        decisions = client.get("/api/decisions")
        self.assertEqual(decisions.status_code, 200)
        self.assertGreater(len(decisions.json()["decisions"]), 0)

    def test_backtest_action_writes_report_and_is_readable(self) -> None:
        client = self._client()

        response = client.post("/api/actions/backtest", json={"candle_count": 22, "lookahead_bars": 4})
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.json())
        self.assertTrue(self.report_file.exists())

        report = client.get("/api/backtest-report")
        self.assertEqual(report.status_code, 200)
        self.assertIn("results", report.json()["report"])

    def test_backtest_report_missing_before_any_run(self) -> None:
        response = self._client().get("/api/backtest-report")
        self.assertEqual(response.status_code, 404)

    def test_mt5_unavailable_returns_502_not_500(self) -> None:
        client = self._client(mt5_client_factory=lambda: MT5Client(FakeUnavailableMT5()))

        response = client.post("/api/actions/healthcheck")

        self.assertEqual(response.status_code, 502)


if __name__ == "__main__":
    unittest.main()
