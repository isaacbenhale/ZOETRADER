from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from zoetrading.config import load_app_config
from zoetrading.domain import OrderStatus
from zoetrading.execution import ExecutionEngine
from zoetrading.journal import JournalStore
from zoetrading.market import MT5Client
from zoetrading.risk import AccountRiskState
from zoetrading.runtime import ManualApprovalLoop, RuntimeEngine


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


def write_command(path: Path, command: str, decision_id: str) -> None:
    path.write_text(f"command,{command}\ndecision_id,{decision_id}\ntime,2026.08.20 12:00:00\n", encoding="ascii")


class ApprovalLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.status_file = root / "status.csv"
        self.command_file = root / "command.csv"
        self.journal_db = root / "trading.db"

    def _build(self, journal: JournalStore, *, sleep=None):
        config = load_app_config("config")
        client = MT5Client(FakeManualMT5())
        client.connect()
        runtime_engine = RuntimeEngine(config, mt5_client=client, journal=journal, status_file=self.status_file)
        execution_engine = ExecutionEngine(client, config.settings.execution, journal=journal)
        loop = ManualApprovalLoop(
            runtime_engine,
            execution_engine,
            journal=journal,
            command_file=str(self.command_file),
            approval_timeout_seconds=0.05,
            poll_interval_seconds=0.01,
            sleep=sleep or (lambda seconds: None),
        )
        return loop

    def test_no_click_times_out_and_sends_no_order(self) -> None:
        with JournalStore(self.journal_db) as journal:
            loop = self._build(journal)
            result = loop.run_cycle(equity=10_000, candle_count=22)

        self.assertEqual(result.outcome, "timeout")
        self.assertIsNone(result.order_result)
        self.assertIsNotNone(result.display_decision)

    def test_approve_matching_decision_executes_the_order(self) -> None:
        with JournalStore(self.journal_db) as journal:
            def sleep_and_approve(_seconds: float) -> None:
                loop.pending_decision and write_command(
                    self.command_file, "APPROVE", loop.pending_decision.decision_id
                )

            loop = self._build(journal, sleep=sleep_and_approve)
            result = loop.run_cycle(equity=10_000, candle_count=22)

        self.assertEqual(result.outcome, "approved")
        self.assertIsNotNone(result.order_result)
        self.assertEqual(result.order_result.status, OrderStatus.ACCEPTED)
        self.assertFalse(self.command_file.exists())

    def test_reject_matching_decision_sends_no_order(self) -> None:
        with JournalStore(self.journal_db) as journal:
            def sleep_and_reject(_seconds: float) -> None:
                loop.pending_decision and write_command(
                    self.command_file, "REJECT", loop.pending_decision.decision_id
                )

            loop = self._build(journal, sleep=sleep_and_reject)
            result = loop.run_cycle(equity=10_000, candle_count=22)

        self.assertEqual(result.outcome, "rejected")
        self.assertIsNone(result.order_result)

    def test_mismatched_decision_id_is_ignored_not_executed(self) -> None:
        with JournalStore(self.journal_db) as journal:
            def sleep_and_send_wrong_id(_seconds: float) -> None:
                loop.pending_decision and write_command(self.command_file, "APPROVE", "wrong-decision-id")

            loop = self._build(journal, sleep=sleep_and_send_wrong_id)
            result = loop.run_cycle(equity=10_000, candle_count=22)

        self.assertEqual(result.outcome, "timeout")
        self.assertIsNone(result.order_result)

    def test_kill_switch_freezes_future_cycles(self) -> None:
        with JournalStore(self.journal_db) as journal:
            def sleep_and_kill(_seconds: float) -> None:
                loop.pending_decision and write_command(
                    self.command_file, "KILL_SWITCH", loop.pending_decision.decision_id
                )

            loop = self._build(journal, sleep=sleep_and_kill)
            first = loop.run_cycle(equity=10_000, candle_count=22)
            second = loop.run_cycle(equity=10_000, candle_count=22)

        self.assertEqual(first.outcome, "kill_switch")
        self.assertTrue(loop.kill_switch)
        self.assertEqual(second.outcome, "kill_switch")
        self.assertEqual(second.scanned, 0)

    def test_resume_after_kill_scans_again(self) -> None:
        write_command(self.command_file, "KILL_SWITCH", "irrelevant")
        with JournalStore(self.journal_db) as journal:
            loop = self._build(journal)
            killed = loop.run_cycle(equity=10_000, candle_count=22)
            self.assertEqual(killed.outcome, "kill_switch")
            self.assertTrue(loop.kill_switch)

            write_command(self.command_file, "RESUME", "irrelevant")
            resumed = loop.run_cycle(equity=10_000, candle_count=22)

        self.assertFalse(loop.kill_switch)
        self.assertGreater(resumed.scanned, 0)

    def test_kill_switch_clicked_between_cycles_is_still_applied(self) -> None:
        write_command(self.command_file, "KILL_SWITCH", "irrelevant")
        with JournalStore(self.journal_db) as journal:
            loop = self._build(journal)
            result = loop.run_cycle(equity=10_000, candle_count=22)

        self.assertEqual(result.outcome, "kill_switch")
        self.assertEqual(result.scanned, 0)
        self.assertTrue(loop.kill_switch)

    def test_pause_clicked_between_cycles_stops_the_next_cycle(self) -> None:
        write_command(self.command_file, "PAUSE", "irrelevant")
        with JournalStore(self.journal_db) as journal:
            loop = self._build(journal)
            result = loop.run_cycle(equity=10_000, candle_count=22)

        self.assertEqual(result.outcome, "paused")
        self.assertEqual(result.scanned, 0)
        self.assertFalse(loop.kill_switch)

    def test_stale_command_file_before_cycle_is_dropped(self) -> None:
        write_command(self.command_file, "APPROVE", "leftover-from-last-run")
        with JournalStore(self.journal_db) as journal:
            loop = self._build(journal)
            loop.run_cycle(equity=10_000, candle_count=22)

        self.assertFalse(self.command_file.exists())


if __name__ == "__main__":
    unittest.main()
