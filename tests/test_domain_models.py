from datetime import UTC, datetime
import unittest

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
    SystemStatus,
    TradeAction,
)


class DomainModelTests(unittest.TestCase):
    def test_no_trade_signal_is_complete_with_reason(self) -> None:
        signal = Signal(
            signal_id="sig-1",
            instrument="EURUSD",
            action=TradeAction.NO_TRADE,
            strategy="regime_filter",
            setup_score=0,
            regime=MarketRegime.CHAOTIC,
            blockers=(RejectionReason.NO_TRADE,),
        )

        self.assertEqual(signal.action, TradeAction.NO_TRADE)

    def test_trade_signal_requires_entry_and_protection(self) -> None:
        with self.assertRaisesRegex(ValueError, "entry is required"):
            Signal(
                signal_id="sig-2",
                instrument="EURUSD",
                action=TradeAction.BUY,
                strategy="trend_pullback",
                setup_score=82,
                regime=MarketRegime.TRENDING_UP,
            )

    def test_reject_and_kill_switch_are_normal_domain_states(self) -> None:
        risk = RiskDecision(
            decision_id="dec-1",
            verdict=RiskVerdict.REJECT,
            reasons=(RejectionReason.KILL_SWITCH,),
            risk_per_trade_pct=0,
        )

        self.assertEqual(risk.verdict, RiskVerdict.REJECT)
        self.assertEqual(SystemStatus.KILL_SWITCH.value, "KILL_SWITCH")

    def test_approved_risk_requires_position_size_and_loss_amount(self) -> None:
        risk = RiskDecision(
            decision_id="dec-approved",
            verdict=RiskVerdict.APPROVE,
            reasons=(),
            risk_per_trade_pct=0.5,
            position_size=0.01,
            max_loss_amount=10,
        )

        self.assertEqual(risk.verdict, RiskVerdict.APPROVE)

    def test_kill_switch_cannot_approve_risk(self) -> None:
        with self.assertRaisesRegex(ValueError, "KILL_SWITCH cannot approve"):
            RiskDecision(
                decision_id="dec-2",
                verdict=RiskVerdict.APPROVE,
                reasons=(RejectionReason.KILL_SWITCH,),
                risk_per_trade_pct=0.5,
                position_size=0.01,
                max_loss_amount=10,
            )

    def test_no_trade_cannot_create_order(self) -> None:
        with self.assertRaisesRegex(ValueError, "NO_TRADE cannot create"):
            OrderRequest(
                order_id="ord-1",
                decision_id="dec-1",
                instrument="EURUSD",
                action=TradeAction.NO_TRADE,
                volume=0.01,
                entry=1.1,
                stop_loss=1.0,
            )

    def test_decision_blocks_trade_when_risk_rejects(self) -> None:
        signal = Signal(
            signal_id="sig-3",
            instrument="EURUSD",
            action=TradeAction.BUY,
            strategy="trend_pullback",
            setup_score=82,
            regime=MarketRegime.TRENDING_UP,
            entry=1.1,
            invalidation=1.0,
            proposed_sl=1.0,
            proposed_tp=1.25,
            expected_rr=1.5,
            reasons=("trend aligned",),
        )
        risk = RiskDecision(
            decision_id="dec-3",
            verdict=RiskVerdict.REJECT,
            reasons=(RejectionReason.RR_TOO_LOW,),
            risk_per_trade_pct=0.5,
        )
        decision = Decision(
            decision_id="dec-3",
            signal=signal,
            risk=risk,
            final_action=TradeAction.NO_TRADE,
        )

        self.assertEqual(decision.final_action, TradeAction.NO_TRADE)

    def test_position_requires_trade_action(self) -> None:
        with self.assertRaisesRegex(ValueError, "NO_TRADE cannot be a position"):
            PositionState(
                position_id="pos-1",
                instrument="EURUSD",
                action=TradeAction.NO_TRADE,
                volume=0.01,
                entry=1.1,
                opened_at=datetime.now(UTC),
                status=PositionStatus.OPEN,
                current_sl=1.0,
            )


if __name__ == "__main__":
    unittest.main()
