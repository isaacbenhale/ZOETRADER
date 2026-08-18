"""Order execution with validation and idempotence."""

from __future__ import annotations

from zoetrading.config.models import ExecutionConfig
from zoetrading.domain import Decision, OrderRequest, OrderResult, OrderStatus, RiskVerdict, RuntimeMode, TradeAction
from zoetrading.journal import JournalStore, new_order_id
from zoetrading.market import MT5Client, MarketDataError


class ExecutionError(RuntimeError):
    pass


class ExecutionEngine:
    def __init__(
        self,
        client: MT5Client,
        config: ExecutionConfig,
        *,
        journal: JournalStore | None = None,
    ) -> None:
        self.client = client
        self.config = config
        self.journal = journal
        self._executed_decisions: dict[str, OrderResult] = {}

    def execute(self, decision: Decision, mode: RuntimeMode) -> OrderResult:
        if mode is RuntimeMode.MONITORING:
            raise ExecutionError("MONITORING mode cannot send orders")
        if mode is RuntimeMode.OFF:
            raise ExecutionError("OFF mode cannot send orders")
        if decision.final_action is TradeAction.NO_TRADE or decision.risk.verdict is not RiskVerdict.APPROVE:
            raise ExecutionError("decision is not approved for execution")
        if self.config.prevent_duplicate_orders and decision.decision_id in self._executed_decisions:
            return self._executed_decisions[decision.decision_id]

        order = self.build_order_request(decision)
        try:
            symbol = self.client.get_symbol_info(order.instrument)
            tick = self.client.get_tick(order.instrument)
        except MarketDataError as exc:
            result = OrderResult(order_id=order.order_id, status=OrderStatus.FAILED, message=str(exc))
            self._executed_decisions[decision.decision_id] = result
            return result

        if not symbol.trade_allowed:
            result = OrderResult(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                message="symbol trade is not allowed",
            )
            self._executed_decisions[decision.decision_id] = result
            return result
        if tick.spread < 0:
            result = OrderResult(order_id=order.order_id, status=OrderStatus.REJECTED, message="invalid spread")
            self._executed_decisions[decision.decision_id] = result
            return result

        result = self.client.send_order(order)
        self._executed_decisions[decision.decision_id] = result
        if self.journal:
            self.journal.log_order_request(order)
            self.journal.log_event(
                "order_result",
                entity_id=order.order_id,
                payload={"status": result.status.value, "message": result.message},
            )
        return result

    @staticmethod
    def build_order_request(decision: Decision) -> OrderRequest:
        signal = decision.signal
        assert signal.entry is not None
        assert signal.proposed_sl is not None
        return OrderRequest(
            order_id=new_order_id(),
            decision_id=decision.decision_id,
            instrument=signal.instrument,
            action=signal.action,
            volume=decision.risk.position_size or 0,
            entry=signal.entry,
            stop_loss=signal.proposed_sl,
            take_profit=signal.proposed_tp,
        )

