import unittest
from types import SimpleNamespace

from zoetrading.config import load_app_config
from zoetrading.domain import MarketRegime, RejectionReason, RiskVerdict, Signal, TradeAction
from zoetrading.risk import AccountRiskState, RiskEngine, calculate_position_size


def trade_signal(expected_rr: float = 2.0, *, stop_loss: float | None = 1.09) -> Signal:
    return Signal(
        signal_id="sig-risk",
        instrument="EURUSD",
        action=TradeAction.BUY,
        strategy="trend_pullback",
        setup_score=85,
        regime=MarketRegime.TRENDING_UP,
        entry=1.1,
        invalidation=1.09,
        proposed_sl=stop_loss,
        proposed_tp=1.12,
        expected_rr=expected_rr,
        reasons=("fixture",),
    )


class RiskEngineTests(unittest.TestCase):
    def test_position_size_uses_equity_risk_and_stop_distance(self) -> None:
        size, max_loss = calculate_position_size(
            equity=10_000,
            risk_per_trade_pct=0.5,
            entry=1.10,
            stop_loss=1.09,
        )

        self.assertAlmostEqual(max_loss, 50)
        self.assertAlmostEqual(size, 5000)

    def test_risk_engine_approves_valid_signal(self) -> None:
        risk = RiskEngine(load_app_config("config").risk).evaluate(
            trade_signal(),
            AccountRiskState(equity=10_000),
        )

        self.assertEqual(risk.verdict, RiskVerdict.APPROVE)
        self.assertGreater(risk.position_size or 0, 0)
        self.assertEqual(risk.reasons, ())

    def test_risk_engine_rejects_kill_switch_and_limits(self) -> None:
        risk = RiskEngine(load_app_config("config").risk).evaluate(
            trade_signal(),
            AccountRiskState(equity=10_000, kill_switch=True, open_positions=3),
        )

        self.assertEqual(risk.verdict, RiskVerdict.REJECT)
        self.assertIn(RejectionReason.KILL_SWITCH, risk.reasons)
        self.assertIn(RejectionReason.MAX_OPEN_POSITIONS, risk.reasons)

    def test_risk_engine_rejects_missing_sl_and_low_rr(self) -> None:
        raw_invalid_signal = SimpleNamespace(
            action=TradeAction.BUY,
            strategy="trend_pullback",
            entry=1.1,
            proposed_sl=None,
            expected_rr=1.0,
        )
        risk = RiskEngine(load_app_config("config").risk).evaluate(
            raw_invalid_signal,
            AccountRiskState(equity=10_000),
        )

        self.assertEqual(risk.verdict, RiskVerdict.REJECT)
        self.assertIn(RejectionReason.MISSING_STOP_LOSS, risk.reasons)
        self.assertIn(RejectionReason.RR_TOO_LOW, risk.reasons)


if __name__ == "__main__":
    unittest.main()
