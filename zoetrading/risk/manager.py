"""Non-bypassable risk checks."""

from __future__ import annotations

from dataclasses import dataclass

from zoetrading.config.models import RiskConfig
from zoetrading.domain import RejectionReason, RiskDecision, RiskVerdict, Signal, TradeAction
from zoetrading.journal import new_decision_id
from zoetrading.risk.position_size import calculate_position_size


@dataclass(frozen=True)
class AccountRiskState:
    equity: float
    daily_loss_pct: float = 0.0
    weekly_loss_pct: float = 0.0
    open_positions: int = 0
    consecutive_losses: int = 0
    kill_switch: bool = False
    value_per_price_unit: float = 1.0


class RiskEngine:
    def __init__(self, config: RiskConfig) -> None:
        self.config = config

    def evaluate(self, signal: Signal, state: AccountRiskState) -> RiskDecision:
        decision_id = new_decision_id()
        reasons: list[RejectionReason] = []

        if state.kill_switch:
            reasons.append(RejectionReason.KILL_SWITCH)
        if signal.action is TradeAction.NO_TRADE:
            reasons.append(RejectionReason.NO_TRADE)
        if self.config.martingale:
            reasons.append(RejectionReason.INVALID_CONFIGURATION)
        if self.config.stop_loss_required and signal.proposed_sl is None:
            reasons.append(RejectionReason.MISSING_STOP_LOSS)
        if state.daily_loss_pct >= self.config.max_daily_loss_pct:
            reasons.append(RejectionReason.DAILY_LOSS_LIMIT)
        if state.weekly_loss_pct >= self.config.max_weekly_loss_pct:
            reasons.append(RejectionReason.WEEKLY_LOSS_LIMIT)
        if state.open_positions >= self.config.max_open_positions:
            reasons.append(RejectionReason.MAX_OPEN_POSITIONS)
        if state.consecutive_losses >= self.config.max_consecutive_losses:
            reasons.append(RejectionReason.CONSECUTIVE_LOSS_COOLDOWN)

        minimum_rr = self.config.minimum_rr_by_strategy.get(signal.strategy)
        if minimum_rr is not None and (signal.expected_rr is None or signal.expected_rr < minimum_rr):
            reasons.append(RejectionReason.RR_TOO_LOW)

        if reasons:
            return RiskDecision(
                decision_id=decision_id,
                verdict=RiskVerdict.REJECT,
                reasons=tuple(dict.fromkeys(reasons)),
                risk_per_trade_pct=self.config.risk_per_trade_pct,
            )

        assert signal.entry is not None
        assert signal.proposed_sl is not None
        position_size, max_loss_amount = calculate_position_size(
            equity=state.equity,
            risk_per_trade_pct=self.config.risk_per_trade_pct,
            entry=signal.entry,
            stop_loss=signal.proposed_sl,
            value_per_price_unit=state.value_per_price_unit,
        )
        return RiskDecision(
            decision_id=decision_id,
            verdict=RiskVerdict.APPROVE,
            reasons=(),
            risk_per_trade_pct=self.config.risk_per_trade_pct,
            position_size=position_size,
            max_loss_amount=max_loss_amount,
        )

