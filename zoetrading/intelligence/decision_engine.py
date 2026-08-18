"""Decision engine that selects strategy output and calls risk last."""

from __future__ import annotations

from dataclasses import dataclass

from zoetrading.domain import Decision, RejectionReason, RiskDecision, RiskVerdict, Signal, TradeAction
from zoetrading.journal import JournalStore
from zoetrading.risk import AccountRiskState, RiskEngine


@dataclass(frozen=True)
class DecisionEvidence:
    selected_signal_id: str
    evaluated_signal_ids: tuple[str, ...]
    reasons: tuple[str, ...]
    blockers: tuple[RejectionReason, ...]


class DecisionEngine:
    def __init__(self, risk_engine: RiskEngine, journal: JournalStore | None = None) -> None:
        self.risk_engine = risk_engine
        self.journal = journal

    def decide(self, signals: tuple[Signal, ...], account_state: AccountRiskState) -> Decision:
        if not signals:
            raise ValueError("at least one signal is required")
        selected = self._select_best_signal(signals)
        risk = self.risk_engine.evaluate(selected, account_state)
        final_action = selected.action if risk.verdict is RiskVerdict.APPROVE else TradeAction.NO_TRADE
        decision = Decision(
            decision_id=risk.decision_id,
            signal=selected,
            risk=risk,
            final_action=final_action,
        )
        if self.journal:
            self.journal.log_decision(decision)
        return decision

    @staticmethod
    def _select_best_signal(signals: tuple[Signal, ...]) -> Signal:
        trade_signals = [signal for signal in signals if signal.action is not TradeAction.NO_TRADE]
        if not trade_signals:
            return max(signals, key=lambda signal: signal.setup_score)
        best_by_strategy: dict[str, Signal] = {}
        for signal in trade_signals:
            current = best_by_strategy.get(signal.strategy)
            if current is None or signal.setup_score > current.setup_score:
                best_by_strategy[signal.strategy] = signal
        return max(best_by_strategy.values(), key=lambda signal: signal.setup_score)

    @staticmethod
    def evidence(decision: Decision, evaluated_signals: tuple[Signal, ...]) -> DecisionEvidence:
        return DecisionEvidence(
            selected_signal_id=decision.signal.signal_id,
            evaluated_signal_ids=tuple(signal.signal_id for signal in evaluated_signals),
            reasons=decision.signal.reasons,
            blockers=decision.signal.blockers + decision.risk.reasons,
        )

