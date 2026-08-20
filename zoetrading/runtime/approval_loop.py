"""Closes the MT5 EA click -> real execution gap for MANUAL mode.

The EA writes a command file when a human clicks APPROVE/REJECT/PAUSE/KILL.
Nothing consumed that file before this module: a click was journaled on the
MT5 side only and never sent an order. This loop is the single place that
turns an APPROVE click into a real `ExecutionEngine.execute()` call.

Safety properties this relies on:
- Any command left over from a previous cycle is read once at the start of
  the next cycle: KILL_SWITCH/PAUSE are applied immediately (they are not
  tied to a specific decision), APPROVE/REJECT found here are stale by
  definition (no proposal was being awaited) and are logged, not executed.
- The EA echoes back the decision_id it was showing when clicked; a click
  that does not match the decision currently being waited on is ignored
  rather than executed (see `_await_approval`).
- AUTO is out of scope here on purpose: it stays gated behind
  AutoValidationGate and is never reachable from this loop.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import time

from zoetrading.domain import Decision, OrderResult, RuntimeMode, TradeAction
from zoetrading.execution import ExecutionEngine
from zoetrading.journal import JournalStore
from zoetrading.operations import consume_command_file, read_command_file
from zoetrading.risk import AccountRiskState
from zoetrading.runtime.engine import RuntimeEngine


@dataclass(frozen=True)
class ApprovalCycleResult:
    scanned: int
    display_decision: Decision | None
    outcome: str
    order_result: OrderResult | None = None


class ManualApprovalLoop:
    def __init__(
        self,
        runtime_engine: RuntimeEngine,
        execution_engine: ExecutionEngine,
        *,
        journal: JournalStore | None,
        command_file: str,
        approval_timeout_seconds: float = 120.0,
        poll_interval_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.runtime_engine = runtime_engine
        self.execution_engine = execution_engine
        self.journal = journal
        self.command_file = command_file
        self.approval_timeout_seconds = approval_timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self._sleep = sleep
        self.kill_switch = False
        self.pending_decision: Decision | None = None

    def run_cycle(self, *, equity: float, candle_count: int = 200) -> ApprovalCycleResult:
        leftover = read_command_file(self.command_file)
        if leftover is not None:
            consume_command_file(self.command_file)
            if leftover.command == "KILL_SWITCH":
                self.kill_switch = True
                self._log_event("kill_switch_engaged", None)
            elif leftover.command == "PAUSE":
                self._log_event("manual_paused", None)
                return ApprovalCycleResult(scanned=0, display_decision=None, outcome="paused")
            else:
                self._log_event(
                    "stale_command_ignored",
                    None,
                    payload={"command": leftover.command, "received_decision_id": leftover.decision_id},
                )

        if self.kill_switch:
            return ApprovalCycleResult(scanned=0, display_decision=None, outcome="kill_switch")

        result = self.runtime_engine.scan_once(
            mode=RuntimeMode.MANUAL,
            account_state=AccountRiskState(equity=equity, kill_switch=self.kill_switch),
            candle_count=candle_count,
        )
        decision = result.display_decision
        if decision is None or decision.final_action is TradeAction.NO_TRADE:
            return ApprovalCycleResult(scanned=result.scanned, display_decision=decision, outcome="no_proposal")

        outcome, order_result = self._await_approval(decision)
        return ApprovalCycleResult(
            scanned=result.scanned,
            display_decision=decision,
            outcome=outcome,
            order_result=order_result,
        )

    def _await_approval(self, decision: Decision) -> tuple[str, OrderResult | None]:
        self.pending_decision = decision
        try:
            waited = 0.0
            while waited < self.approval_timeout_seconds:
                command = read_command_file(self.command_file)
                if command is not None:
                    consume_command_file(self.command_file)
                    if command.command in {"APPROVE", "REJECT"} and command.decision_id != decision.decision_id:
                        self._log_event(
                            "stale_command_ignored",
                            decision,
                            payload={"command": command.command, "received_decision_id": command.decision_id},
                        )
                    else:
                        return self._apply_command(command.command, decision)
                self._sleep(self.poll_interval_seconds)
                waited += self.poll_interval_seconds
            self._log_event("approval_timeout", decision)
            return "timeout", None
        finally:
            self.pending_decision = None

    def _apply_command(self, command: str, decision: Decision) -> tuple[str, OrderResult | None]:
        if command == "APPROVE":
            order_result = self.execution_engine.execute(decision, RuntimeMode.MANUAL)
            self._log_event("manual_approved", decision, payload={"order_status": order_result.status.value})
            return "approved", order_result
        if command == "REJECT":
            self._log_event("manual_rejected", decision)
            return "rejected", None
        if command == "KILL_SWITCH":
            self.kill_switch = True
            self._log_event("kill_switch_engaged", decision)
            return "kill_switch", None
        if command == "PAUSE":
            self._log_event("manual_paused", decision)
            return "paused", None
        self._log_event("unknown_command", decision, payload={"command": command})
        return "unknown_command", None

    def _log_event(self, event_type: str, decision: Decision | None, *, payload: dict | None = None) -> None:
        if not self.journal:
            return
        self.journal.log_event(
            event_type,
            entity_id=decision.decision_id if decision else None,
            payload=payload or {},
        )
