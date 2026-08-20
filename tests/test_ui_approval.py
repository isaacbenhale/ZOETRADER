from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
import unittest

from fastapi.testclient import TestClient

from zoetrading.market import MT5Client
from zoetrading.ui import create_app


class FakeManualMT5:
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_M30 = 30
    TIMEFRAME_H1 = 60
    TIMEFRAME_H4 = 240
    TIMEFRAME_D1 = 1440
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    TRADE_ACTION_DEAL = 1
    TRADE_RETCODE_DONE = 10009

    def __init__(self) -> None:
        self.connected = False
        self.orders: list[dict] = []

    def initialize(self, **kwargs) -> bool:
        self.connected = True
        return True

    def shutdown(self) -> None:
        self.connected = False

    def terminal_info(self):
        return SimpleNamespace(connected=True) if self.connected else None

    def symbol_info(self, symbol: str):
        return SimpleNamespace(
            visible=True, trade_mode=1, digits=5, point=0.00001, volume_min=0.01, volume_max=100.0, volume_step=0.01
        )

    def symbol_select(self, symbol: str, enabled: bool) -> bool:
        return True

    def symbol_info_tick(self, symbol: str):
        return SimpleNamespace(time=int(datetime.now(UTC).timestamp()), bid=20.0, ask=20.2, last=20.1, volume=1)

    def copy_rates_from_pos(self, symbol: str, timeframe: int, start: int, count: int):
        now = int(datetime.now(UTC).timestamp())
        closes = [10, 11, 13, 10, 9, 12, 15, 12, 11, 14, 17, 14, 13, 16, 19, 16, 15, 18, 21, 18, 17, 20]
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

    def order_send(self, request: dict):
        self.orders.append(request)
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=123, comment="done")

    def last_error(self):
        return (0, "ok")


class FakeUnavailableMT5:
    def initialize(self, **kwargs) -> bool:
        return False

    def shutdown(self) -> None:
        pass

    def last_error(self):
        return (1, "no terminal")


def wait_until(predicate, *, timeout: float = 5.0, interval: float = 0.05) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


class UiApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.journal_db = root / "trading.db"
        self.status_file = root / "status.csv"
        self.command_file = root / "command.csv"
        self.report_file = root / "backtest_report.json"
        self._runners_to_stop: list = []
        self.addCleanup(self._stop_all_runners)

    def _stop_all_runners(self) -> None:
        for runner in self._runners_to_stop:
            runner.stop()
            runner.join(timeout=2)

    def _client(self, mt5_client_factory=None) -> TestClient:
        app = create_app(
            config_dir="config",
            journal_db=str(self.journal_db),
            status_file=str(self.status_file),
            command_file=str(self.command_file),
            report_file=str(self.report_file),
            mt5_client_factory=mt5_client_factory or (lambda: MT5Client(FakeManualMT5())),
            approval_timeout_seconds=2.0,
            approval_poll_interval_seconds=0.05,
        )
        client = TestClient(app)
        client._zoe_app = app  # keep a handle to reach app.state.approval_runner for cleanup
        return client

    def _register_for_cleanup(self, client: TestClient) -> None:
        runner = client._zoe_app.state.approval_runner
        if runner is not None:
            self._runners_to_stop.append(runner)

    def test_status_before_start(self) -> None:
        client = self._client()
        response = client.get("/api/approval/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "running": False,
            "kill_switch": False,
            "pending_decision": None,
            "last_outcome": None,
            "start_error": None,
        })

    def test_start_with_unavailable_mt5_returns_502(self) -> None:
        client = self._client(mt5_client_factory=lambda: MT5Client(FakeUnavailableMT5()))

        response = client.post("/api/approval/start", json={"equity": 10_000})

        self.assertEqual(response.status_code, 502)

    def test_approve_and_reject_require_a_pending_decision(self) -> None:
        client = self._client()

        approve = client.post("/api/approval/approve")
        reject = client.post("/api/approval/reject")

        self.assertEqual(approve.status_code, 409)
        self.assertEqual(reject.status_code, 409)

    def test_pause_and_kill_do_not_require_a_pending_decision(self) -> None:
        client = self._client()

        pause = client.post("/api/approval/pause")
        kill = client.post("/api/approval/kill")

        self.assertEqual(pause.status_code, 200)
        self.assertEqual(kill.status_code, 200)

    def test_start_shows_pending_decision_then_approve_executes_order(self) -> None:
        client = self._client()

        start = client.post("/api/approval/start", json={"equity": 10_000, "candle_count": 22})
        self.assertEqual(start.status_code, 200)
        self._register_for_cleanup(client)

        has_pending = wait_until(
            lambda: client.get("/api/approval/status").json()["pending_decision"] is not None
        )
        self.assertTrue(has_pending, "no pending decision appeared in time")

        status = client.get("/api/approval/status").json()
        self.assertIn(status["pending_decision"]["final_action"], {"BUY", "SELL"})

        approve = client.post("/api/approval/approve")
        self.assertEqual(approve.status_code, 200)

        approved = wait_until(lambda: client.get("/api/approval/status").json()["last_outcome"] == "approved")
        self.assertTrue(approved, "approval was never applied")

        client.post("/api/approval/stop")

    def test_starting_twice_returns_409(self) -> None:
        client = self._client()
        first = client.post("/api/approval/start", json={"equity": 10_000, "candle_count": 22})
        self.assertEqual(first.status_code, 200)
        self._register_for_cleanup(client)

        second = client.post("/api/approval/start", json={"equity": 10_000, "candle_count": 22})

        self.assertEqual(second.status_code, 409)
        client.post("/api/approval/stop")


if __name__ == "__main__":
    unittest.main()
