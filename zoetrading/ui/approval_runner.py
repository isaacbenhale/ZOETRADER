"""Drives ManualApprovalLoop in a background thread for the web UI.

The web UI's own APPROVE/REJECT/PAUSE/KILL buttons never call the
execution engine directly -- they write to the same command file the MT5
EA writes to (see write_command_file), which this runner's loop reads
through the same, already-tested ManualApprovalLoop. Both surfaces are
symmetric: neither has priority over the other.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import threading

from zoetrading.domain import Decision
from zoetrading.runtime import ApprovalCycleResult, ManualApprovalLoop


@dataclass(frozen=True)
class ApprovalStatus:
    running: bool
    kill_switch: bool
    pending_decision: Decision | None
    last_outcome: str | None
    start_error: str | None


class ApprovalRunner:
    def __init__(self, build_loop: Callable[[], ManualApprovalLoop], *, refresh_interval_seconds: float) -> None:
        self._build_loop = build_loop
        self.refresh_interval_seconds = refresh_interval_seconds
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.loop: ManualApprovalLoop | None = None
        self.last_result: ApprovalCycleResult | None = None
        self.start_error: str | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, *, equity: float, candle_count: int = 200) -> bool:
        with self._lock:
            if self.running:
                return False
            self._stop.clear()
            self.start_error = None
            self.last_result = None
            self._thread = threading.Thread(target=self._run, args=(equity, candle_count), daemon=True)
            self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def status(self) -> ApprovalStatus:
        return ApprovalStatus(
            running=self.running,
            kill_switch=self.loop.kill_switch if self.loop else False,
            pending_decision=self.loop.pending_decision if self.loop else None,
            last_outcome=self.last_result.outcome if self.last_result else None,
            start_error=self.start_error,
        )

    def _run(self, equity: float, candle_count: int) -> None:
        try:
            self.loop = self._build_loop()
        except Exception as exc:  # surfaced via status(), never crashes the server
            self.start_error = str(exc)
            return
        try:
            while not self._stop.is_set():
                result = self.loop.run_cycle(equity=equity, candle_count=candle_count)
                self.last_result = result
                if result.outcome == "paused":
                    break
                if self._stop.wait(self.refresh_interval_seconds):
                    break
        finally:
            if self.loop.journal:
                self.loop.journal.close()
