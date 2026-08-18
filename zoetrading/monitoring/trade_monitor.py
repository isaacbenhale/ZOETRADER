"""Position monitoring and dynamic exit policies."""

from __future__ import annotations

from dataclasses import dataclass

from zoetrading.domain import PositionAction, PositionState, PositionUpdate, TradeAction
from zoetrading.journal import JournalStore


@dataclass(frozen=True)
class MonitoringPolicy:
    break_even_trigger_r: float = 1.0
    trailing_distance: float = 0.0
    allow_early_exit: bool = True


class PositionMonitor:
    def __init__(self, policy: MonitoringPolicy, journal: JournalStore | None = None) -> None:
        self.policy = policy
        self.journal = journal

    def evaluate_position(self, position: PositionState, current_price: float, *, invalidated: bool = False) -> PositionUpdate:
        if invalidated and self.policy.allow_early_exit:
            update = PositionUpdate(
                position_id=position.position_id,
                action=PositionAction.CLOSE,
                reason="scenario invalidated",
                close_volume=position.volume,
            )
            self._log(update)
            return update

        initial_risk = abs(position.entry - position.current_sl)
        if initial_risk <= 0:
            update = PositionUpdate(position_id=position.position_id, action=PositionAction.HOLD, reason="invalid risk distance")
            self._log(update)
            return update
        favorable = current_price - position.entry if position.action is TradeAction.BUY else position.entry - current_price
        if favorable >= initial_risk * self.policy.break_even_trigger_r:
            new_sl = position.entry
            if self.policy.trailing_distance > 0:
                if position.action is TradeAction.BUY:
                    new_sl = max(new_sl, current_price - self.policy.trailing_distance)
                else:
                    new_sl = min(new_sl, current_price + self.policy.trailing_distance)
            should_move = (
                position.action is TradeAction.BUY and new_sl > position.current_sl
            ) or (
                position.action is TradeAction.SELL and new_sl < position.current_sl
            )
            if should_move:
                update = PositionUpdate(
                    position_id=position.position_id,
                    action=PositionAction.MOVE_STOP,
                    reason="break-even/trailing policy",
                    new_stop_loss=new_sl,
                )
                self._log(update)
                return update

        update = PositionUpdate(position_id=position.position_id, action=PositionAction.HOLD, reason="scenario remains valid")
        self._log(update)
        return update

    def _log(self, update: PositionUpdate) -> None:
        if self.journal:
            self.journal.log_event(
                "position_update",
                entity_id=update.position_id,
                payload={
                    "action": update.action.value,
                    "reason": update.reason,
                    "new_stop_loss": update.new_stop_loss,
                    "close_volume": update.close_volume,
                },
            )

