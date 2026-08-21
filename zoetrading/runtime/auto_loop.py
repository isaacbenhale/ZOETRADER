"""Real AUTO execution loop.

`AutoTradingLoop` is the only place in the codebase allowed to send an order
under `RuntimeMode.AUTO`. It exists to remove the human click that
`ManualApprovalLoop` waits for, while keeping every other safety property
identical:

- It can only be constructed with an `AutoGateDecision` whose verdict is
  `ALLOW` (see `zoetrading.validation.AutoValidationGate`). There is no way
  to build one from ad hoc numbers -- the caller must load the decision from
  `AutoValidationGate.evaluate(load_auto_gate_evidence(path))`, which forces
  documented evidence (backtest, out-of-sample, demo/shadow/manual trades)
  to exist on disk. Construction raises `AutoModeBlockedError` otherwise.
- Every proposal still goes through `RiskEngine` via `RuntimeEngine.scan_once`
  (called with `RuntimeMode.MANUAL`, the same scanning path MANUAL uses --
  `scan_once` itself still refuses `RuntimeMode.AUTO` as a defense-in-depth
  guard against accidental AUTO scans elsewhere). SL, TP, position size and
  the risk verdict are exactly what the Risk Engine computed; this loop never
  overrides them.
- KILL_SWITCH/PAUSE/RESUME/REJECT written by the MT5 EA or the web UI's
  manual-approval panel are still honored: at the start of every cycle, and
  again right before an order is actually sent (closing the window where a
  human clicks REJECT/KILL while a scan is in flight). REJECT acts as a
  per-decision veto: it skips only that one proposal, it does not disable
  AUTO. Only PAUSE stops the loop; KILL_SWITCH freezes it until RESUME.
- The web UI can never activate AUTO: it can only write KILL_SWITCH, PAUSE,
  RESUME, APPROVE or REJECT to the shared command file, all of which either
  do nothing here or make the system more conservative.
"""

from __future__ import annotations

from dataclasses import dataclass

from zoetrading.domain import Decision, OrderResult, RiskVerdict, RuntimeMode, TradeAction
from zoetrading.execution import ExecutionEngine
from zoetrading.journal import JournalStore
from zoetrading.operations import consume_command_file, read_command_file
from zoetrading.risk import AccountRiskState
from zoetrading.runtime.engine import RuntimeEngine
from zoetrading.validation import AutoGateDecision, AutoGateVerdict


class AutoModeBlockedError(RuntimeError):
    pass


@dataclass(frozen=True)
class AutoCycleResult:
    scanned: int
    display_decision: Decision | None
    outcome: str
    order_result: OrderResult | None = None


class AutoTradingLoop:
    def __init__(
        self,
        runtime_engine: RuntimeEngine,
        execution_engine: ExecutionEngine,
        *,
        journal: JournalStore | None,
        command_file: str,
        gate_decision: AutoGateDecision,
    ) -> None:
        if gate_decision.verdict is not AutoGateVerdict.ALLOW:
            raise AutoModeBlockedError(
                "AUTO mode is blocked: " + "; ".join(gate_decision.reasons)
            )
        self.runtime_engine = runtime_engine
        self.execution_engine = execution_engine
        self.journal = journal
        self.command_file = command_file
        self.gate_decision = gate_decision
        self.kill_switch = False

    def run_cycle(self, *, equity: float, candle_count: int = 200) -> AutoCycleResult:
        leftover_outcome = self._apply_leftover_commands(decision=None)
        if leftover_outcome is not None:
            return AutoCycleResult(scanned=0, display_decision=None, outcome=leftover_outcome)

        if self.kill_switch:
            return AutoCycleResult(scanned=0, display_decision=None, outcome="kill_switch")

        result = self.runtime_engine.scan_once(
            mode=RuntimeMode.MANUAL,
            account_state=AccountRiskState(equity=equity, kill_switch=self.kill_switch),
            candle_count=candle_count,
        )
        decision = result.display_decision
        if decision is None or decision.final_action is TradeAction.NO_TRADE:
            return AutoCycleResult(scanned=result.scanned, display_decision=decision, outcome="no_trade")
        if decision.risk.verdict is not RiskVerdict.APPROVE:
            return AutoCycleResult(scanned=result.scanned, display_decision=decision, outcome="risk_rejected")

        pre_execution_outcome = self._apply_leftover_commands(decision=decision)
        if pre_execution_outcome is not None:
            return AutoCycleResult(
                scanned=result.scanned,
                display_decision=decision,
                outcome=pre_execution_outcome,
            )
        if self.kill_switch:
            return AutoCycleResult(scanned=result.scanned, display_decision=decision, outcome="kill_switch")

        order_result = self.execution_engine.execute(decision, RuntimeMode.AUTO)
        self._log_event("auto_executed", decision, payload={"order_status": order_result.status.value})
        return AutoCycleResult(
            scanned=result.scanned,
            display_decision=decision,
            outcome="auto_executed",
            order_result=order_result,
        )

    def _apply_leftover_commands(self, *, decision: Decision | None) -> str | None:
        """Consume one pending command and return a terminal outcome, or None to continue."""

        command = read_command_file(self.command_file)
        if command is None:
            return None
        consume_command_file(self.command_file)

        if command.command == "KILL_SWITCH":
            self.kill_switch = True
            self._log_event("kill_switch_engaged", decision)
            return "kill_switch"
        if command.command == "RESUME":
            self.kill_switch = False
            self._log_event("kill_switch_resumed", decision)
            return None
        if command.command == "PAUSE":
            self._log_event("auto_paused", decision)
            return "paused"
        if command.command == "REJECT" and decision is not None and command.decision_id == decision.decision_id:
            self._log_event("auto_rejected_by_operator", decision)
            return "rejected"
        if command.command in {"APPROVE", "REJECT"}:
            self._log_event(
                "stale_command_ignored",
                decision,
                payload={"command": command.command, "received_decision_id": command.decision_id},
            )
            return None
        self._log_event("unknown_command", decision, payload={"command": command.command})
        return None

    def _log_event(self, event_type: str, decision: Decision | None, *, payload: dict | None = None) -> None:
        if not self.journal:
            return
        self.journal.log_event(
            event_type,
            entity_id=decision.decision_id if decision else None,
            payload=payload or {},
        )
