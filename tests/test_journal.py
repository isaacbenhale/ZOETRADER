from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from zoetrading.config import load_app_config
from zoetrading.domain import (
    Decision,
    MarketRegime,
    OrderRequest,
    PositionState,
    PositionStatus,
    RejectionReason,
    RiskDecision,
    RiskVerdict,
    Signal,
    TradeAction,
)
from zoetrading.journal import (
    JournalStore,
    StructuredLogger,
    new_decision_id,
    new_event_id,
    new_order_id,
    new_position_id,
    new_signal_id,
)


class JournalTests(unittest.TestCase):
    def test_id_helpers_generate_prefixed_unique_ids(self) -> None:
        ids = {
            new_signal_id(),
            new_decision_id(),
            new_order_id(),
            new_position_id(),
            new_event_id(),
        }

        self.assertEqual(len(ids), 5)
        self.assertTrue(any(item.startswith("sig_") for item in ids))
        self.assertTrue(any(item.startswith("dec_") for item in ids))

    def test_rejected_signal_is_journaled_with_reason(self) -> None:
        signal = Signal(
            signal_id="sig-rejected",
            instrument="EURUSD",
            action=TradeAction.NO_TRADE,
            strategy="regime_filter",
            setup_score=0,
            regime=MarketRegime.CHAOTIC,
            blockers=(RejectionReason.NO_TRADE,),
        )

        with JournalStore(":memory:") as journal:
            journal.log_signal(signal)

            self.assertEqual(
                journal.analytics_summary(),
                {
                    "signals": 1,
                    "decisions": 0,
                    "rejections": 1,
                    "orders": 0,
                    "positions": 0,
                    "events": 0,
                    "metrics": 0,
                },
            )

    def test_decision_trace_links_signal_risk_rejection_and_config(self) -> None:
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
            verdict=RiskVerdict.REJECT,
            reasons=(RejectionReason.RR_TOO_LOW,),
            risk_per_trade_pct=0.5,
        )
        decision = Decision(
            decision_id="dec-1",
            signal=signal,
            risk=risk,
            final_action=TradeAction.NO_TRADE,
        )
        config = load_app_config("config")

        with JournalStore(":memory:") as journal:
            config_hash = journal.save_config_snapshot(config)
            journal.log_decision(decision, config_hash=config_hash)
            trace = journal.get_decision_trace("dec-1")

            self.assertEqual(trace.decision["decision_id"], "dec-1")
            self.assertEqual(trace.signal["signal_id"], "sig-1")
            self.assertEqual(trace.risk["verdict"], "REJECT")
            self.assertIn("RR_TOO_LOW", trace.rejections)
            self.assertIsNotNone(trace.config)
            self.assertEqual(trace.config["settings"]["mode"], "MONITORING")

    def test_relogging_decision_does_not_duplicate_rejections(self) -> None:
        signal = Signal(
            signal_id="sig-repeat",
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
        decision = Decision(
            decision_id="dec-repeat",
            signal=signal,
            risk=RiskDecision(
                decision_id="dec-repeat",
                verdict=RiskVerdict.REJECT,
                reasons=(RejectionReason.RR_TOO_LOW,),
                risk_per_trade_pct=0.5,
            ),
            final_action=TradeAction.NO_TRADE,
        )

        with JournalStore(":memory:") as journal:
            journal.log_decision(decision)
            journal.log_decision(decision)

            trace = journal.get_decision_trace("dec-repeat")
            self.assertEqual(trace.rejections.count("RR_TOO_LOW"), 1)

    def test_orders_positions_events_and_metrics_are_counted(self) -> None:
        signal = Signal(
            signal_id="sig-approved",
            instrument="EURUSD",
            action=TradeAction.BUY,
            strategy="trend_pullback",
            setup_score=88,
            regime=MarketRegime.TRENDING_UP,
            entry=1.1,
            invalidation=1.09,
            proposed_sl=1.09,
            proposed_tp=1.12,
            expected_rr=2.0,
            reasons=("setup valid",),
        )
        risk = RiskDecision(
            decision_id="dec-approved",
            verdict=RiskVerdict.APPROVE,
            reasons=(),
            risk_per_trade_pct=0.5,
            position_size=0.01,
            max_loss_amount=10,
        )
        decision = Decision(
            decision_id="dec-approved",
            signal=signal,
            risk=risk,
            final_action=TradeAction.BUY,
        )
        order = OrderRequest(
            order_id="ord-approved",
            decision_id="dec-approved",
            instrument="EURUSD",
            action=TradeAction.BUY,
            volume=0.01,
            entry=1.1,
            stop_loss=1.09,
            take_profit=1.12,
        )
        position = PositionState(
            position_id="pos-approved",
            instrument="EURUSD",
            action=TradeAction.BUY,
            volume=0.01,
            entry=1.1,
            opened_at=datetime.now(UTC),
            status=PositionStatus.OPEN,
            current_sl=1.09,
            current_tp=1.12,
        )

        with JournalStore(":memory:") as journal:
            journal.log_decision(decision)
            journal.log_order_request(order)
            journal.log_position(position)
            journal.log_event("heartbeat", entity_id="system", payload={"status": "RUNNING"})
            journal.record_metric("expectancy", 0.12, instrument="EURUSD", strategy="trend_pullback")

            self.assertEqual(journal.analytics_summary()["orders"], 1)
            self.assertEqual(journal.analytics_summary()["positions"], 1)
            self.assertEqual(journal.analytics_summary()["events"], 1)
            self.assertEqual(journal.analytics_summary()["metrics"], 1)

    def test_structured_logger_writes_json_lines(self) -> None:
        with TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "zoetrading.jsonl"
            logger = StructuredLogger(log_path)
            event_id = logger.event("decision_rejected", entity_id="dec-1", payload={"reason": "RR_TOO_LOW"})

            line = log_path.read_text(encoding="utf-8").strip()
            payload = json.loads(line)

            self.assertEqual(payload["event_id"], event_id)
            self.assertEqual(payload["event_type"], "decision_rejected")
            self.assertEqual(payload["entity_id"], "dec-1")
            self.assertEqual(payload["payload"]["reason"], "RR_TOO_LOW")


if __name__ == "__main__":
    unittest.main()
