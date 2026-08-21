import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from zoetrading.domain import (
    Decision,
    MarketRegime,
    RiskDecision,
    RiskVerdict,
    Signal,
    SystemStatus,
    TradeAction,
)
from zoetrading.operations.mt5_status import (
    consume_command_file,
    read_command_file,
    write_command_file,
    write_status_file,
)


def make_decision() -> Decision:
    signal = Signal(
        signal_id="sig-1",
        instrument="EURUSD",
        action=TradeAction.BUY,
        strategy="trend_pullback",
        setup_score=82,
        regime=MarketRegime.TRENDING_UP,
        entry=1.1,
        invalidation=1.09,
        proposed_sl=1.09,
        proposed_tp=1.12,
        expected_rr=2.0,
        reasons=("H1 trend aligned",),
    )
    risk = RiskDecision(
        decision_id="dec-1",
        verdict=RiskVerdict.APPROVE,
        reasons=(),
        risk_per_trade_pct=0.5,
        position_size=0.1,
        max_loss_amount=10.0,
    )
    return Decision(decision_id="dec-1", signal=signal, risk=risk, final_action=TradeAction.BUY)


def parse_status_lines(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "," in line:
            key, value = line.split(",", 1)
            values[key] = value
    return values


class Mt5StatusTests(unittest.TestCase):
    def test_write_status_file_without_decision_uses_placeholders(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "status.csv"
            write_status_file(path, status=SystemStatus.RUNNING, mode="MANUAL")

            values = parse_status_lines(path.read_text(encoding="ascii"))

        self.assertEqual(values["status"], "RUNNING")
        self.assertEqual(values["mode"], "MANUAL")
        self.assertEqual(values["signal"], "NO SIGNAL")
        self.assertEqual(values["decision_id"], "-")

    def test_write_status_file_with_decision_includes_signal_fields(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "status.csv"
            write_status_file(path, status=SystemStatus.RUNNING, mode="MANUAL", decision=make_decision())

            values = parse_status_lines(path.read_text(encoding="ascii"))

        self.assertEqual(values["signal"], "BUY EURUSD")
        self.assertEqual(values["decision_id"], "dec-1")
        self.assertEqual(values["strategy"], "trend_pullback")
        self.assertEqual(values["entry"], "1.10000")
        self.assertEqual(values["sl"], "1.09000")
        self.assertEqual(values["tp"], "1.12000")

    def test_write_status_file_leaves_no_temp_file_behind(self) -> None:
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = directory / "status.csv"
            write_status_file(path, status=SystemStatus.RUNNING, mode="MANUAL")

            self.assertEqual(list(directory.iterdir()), [path])

    def test_write_status_file_never_leaves_a_partially_written_file_under_concurrent_reads(self) -> None:
        # Regression guard for the EA reading zoetrading_status.csv on a 1s
        # timer while Python rewrites it every scan cycle: a non-atomic
        # write() could be observed mid-write, desyncing the EA's key/value
        # parsing. Hammer writes and reads concurrently and require every
        # observed file to be a complete, well-formed snapshot.
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "status.csv"
            write_status_file(path, status=SystemStatus.RUNNING, mode="MANUAL")
            errors: list[str] = []
            stop = threading.Event()

            def writer() -> None:
                for i in range(200):
                    decision = make_decision() if i % 2 == 0 else None
                    write_status_file(path, status=SystemStatus.RUNNING, mode="MANUAL", decision=decision)
                stop.set()

            def reader() -> None:
                while not stop.is_set():
                    try:
                        text = path.read_text(encoding="ascii")
                    except FileNotFoundError:
                        continue
                    values = parse_status_lines(text)
                    if len(values) not in (0, 11):
                        errors.append(f"malformed snapshot: {values!r}")

            writer_thread = threading.Thread(target=writer)
            reader_threads = [threading.Thread(target=reader) for _ in range(4)]
            writer_thread.start()
            for thread in reader_threads:
                thread.start()
            writer_thread.join()
            for thread in reader_threads:
                thread.join()

        self.assertEqual(errors, [])

    def test_write_command_file_round_trips_through_read_command_file(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "command.csv"
            write_command_file(path, command="APPROVE", decision_id="dec-1")

            command = read_command_file(path)

        self.assertIsNotNone(command)
        self.assertEqual(command.command, "APPROVE")
        self.assertEqual(command.decision_id, "dec-1")

    def test_write_command_file_without_decision_id_reads_back_none(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "command.csv"
            write_command_file(path, command="KILL_SWITCH", decision_id=None)

            command = read_command_file(path)

        self.assertEqual(command.command, "KILL_SWITCH")
        self.assertIsNone(command.decision_id)

    def test_read_command_file_missing_returns_none(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "command.csv"

            self.assertIsNone(read_command_file(path))

    def test_consume_command_file_removes_it(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "command.csv"
            write_command_file(path, command="PAUSE", decision_id=None)

            consume_command_file(path)

            self.assertFalse(path.exists())

if __name__ == "__main__":
    unittest.main()
