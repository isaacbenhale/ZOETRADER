from datetime import UTC, datetime
from types import SimpleNamespace
import unittest

from zoetrading.config import load_app_config
from zoetrading.domain import (
    MarketRegime,
    OrderStatus,
    PositionAction,
    PositionState,
    PositionStatus,
    RejectionReason,
    Signal,
    TradeAction,
    RuntimeMode,
)
from zoetrading.execution import ExecutionEngine, ExecutionError
from zoetrading.intelligence import DecisionEngine
from zoetrading.journal import JournalStore
from zoetrading.monitoring import MonitoringPolicy, PositionMonitor
from zoetrading.risk import AccountRiskState, RiskEngine
from zoetrading.market import MT5Client


class FakeMT5Execution:
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_SLTP = 6
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
            visible=True,
            trade_mode=1,
            digits=5,
            point=0.00001,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
        )

    def symbol_select(self, symbol: str, enabled: bool) -> bool:
        return True

    def symbol_info_tick(self, symbol: str):
        return SimpleNamespace(time=1_700_000_000, bid=1.1, ask=1.1002, last=1.1001, volume=1)

    def order_send(self, request: dict):
        self.orders.append(request)
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=456, comment="done")

    def last_error(self):
        return (0, "ok")


def signal(signal_id: str = "sig-decision", score: int = 85) -> Signal:
    return Signal(
        signal_id=signal_id,
        instrument="EURUSD",
        action=TradeAction.BUY,
        strategy="trend_pullback",
        setup_score=score,
        regime=MarketRegime.TRENDING_UP,
        entry=1.1,
        invalidation=1.09,
        proposed_sl=1.09,
        proposed_tp=1.12,
        expected_rr=2.0,
        reasons=("fixture",),
    )


class DecisionExecutionMonitoringTests(unittest.TestCase):
    def test_decision_engine_calls_risk_and_journals_no_trade(self) -> None:
        with JournalStore(":memory:") as journal:
            engine = DecisionEngine(RiskEngine(load_app_config("config").risk), journal)
            decision = engine.decide(
                (signal("sig-a"),),
                AccountRiskState(equity=10_000, kill_switch=True),
            )

            self.assertEqual(decision.final_action, TradeAction.NO_TRADE)
            self.assertIn(RejectionReason.KILL_SWITCH, decision.risk.reasons)
            self.assertEqual(journal.analytics_summary()["decisions"], 1)

    def test_decision_engine_selects_highest_trade_signal(self) -> None:
        engine = DecisionEngine(RiskEngine(load_app_config("config").risk))
        decision = engine.decide(
            (signal("sig-low", 70), signal("sig-high", 90)),
            AccountRiskState(equity=10_000),
        )

        self.assertEqual(decision.signal.signal_id, "sig-high")
        self.assertEqual(decision.final_action, TradeAction.BUY)

    def test_execution_blocks_monitoring_mode(self) -> None:
        client = MT5Client(FakeMT5Execution())
        client.connect()
        decision = DecisionEngine(RiskEngine(load_app_config("config").risk)).decide(
            (signal(),),
            AccountRiskState(equity=10_000),
        )
        executor = ExecutionEngine(client, load_app_config("config").settings.execution)

        with self.assertRaisesRegex(ExecutionError, "MONITORING"):
            executor.execute(decision, RuntimeMode.MONITORING)

    def test_execution_sends_once_per_decision(self) -> None:
        fake = FakeMT5Execution()
        client = MT5Client(fake)
        client.connect()
        decision = DecisionEngine(RiskEngine(load_app_config("config").risk)).decide(
            (signal(),),
            AccountRiskState(equity=10_000),
        )
        executor = ExecutionEngine(client, load_app_config("config").settings.execution)

        first = executor.execute(decision, RuntimeMode.AUTO)
        second = executor.execute(decision, RuntimeMode.AUTO)

        self.assertEqual(first.status, OrderStatus.ACCEPTED)
        self.assertEqual(second.order_id, first.order_id)
        self.assertEqual(len(fake.orders), 1)

    def test_position_monitor_moves_stop_and_closes_invalidated_position(self) -> None:
        position = PositionState(
            position_id="pos-1",
            instrument="EURUSD",
            action=TradeAction.BUY,
            volume=0.01,
            entry=1.10,
            opened_at=datetime.now(UTC),
            status=PositionStatus.OPEN,
            current_sl=1.09,
            current_tp=1.13,
        )
        monitor = PositionMonitor(MonitoringPolicy(break_even_trigger_r=1.0, trailing_distance=0.005))

        move = monitor.evaluate_position(position, 1.12)
        close = monitor.evaluate_position(position, 1.08, invalidated=True)

        self.assertEqual(move.action, PositionAction.MOVE_STOP)
        self.assertGreater(move.new_stop_loss or 0, position.current_sl)
        self.assertEqual(close.action, PositionAction.CLOSE)
        self.assertEqual(close.close_volume, position.volume)


if __name__ == "__main__":
    unittest.main()
