import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from zoetrading.backtesting import (
    BacktestEngine,
    BacktestInput,
    PerformanceMetrics,
    compute_metrics,
    make_walk_forward_splits,
    monte_carlo_drawdowns,
)
from zoetrading.domain import Candle, MarketRegime, Signal, TradeAction
from zoetrading.operations import backup_runtime_files, heartbeat_status
from zoetrading.validation import (
    AutoGateEvidence,
    AutoGateEvidenceError,
    AutoGateVerdict,
    AutoValidationGate,
    check_vps_readiness,
    load_auto_gate_evidence,
)


def make_candles(closes: list[float]) -> tuple[Candle, ...]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return tuple(
        Candle(
            instrument="EURUSD",
            timeframe="M1",
            timestamp=start + timedelta(minutes=index),
            open=close,
            high=close + 0.2,
            low=close - 0.2,
            close=close,
            tick_volume=100,
            spread=10,
            real_volume=0,
        )
        for index, close in enumerate(closes)
    )


def every_five_bars_signal(candles, index: int):
    if index % 5 != 0:
        return None
    entry = candles[-1].close
    return Signal(
        signal_id=f"sig-{index}",
        instrument="EURUSD",
        action=TradeAction.BUY,
        strategy="fixture",
        setup_score=80,
        regime=MarketRegime.TRENDING_UP,
        entry=entry,
        invalidation=entry - 0.1,
        proposed_sl=entry - 0.1,
        proposed_tp=entry + 0.2,
        expected_rr=2.0,
        reasons=("fixture",),
    )


class BacktestingValidationOperationsTests(unittest.TestCase):
    def test_metrics_include_required_validation_numbers(self) -> None:
        metrics = compute_metrics((2.0, -1.0, 1.0, -0.5), mfe=(2, 0.2, 1.4, 0.1), mae=(-0.1, -1, -0.3, -0.5))

        self.assertEqual(metrics.trades, 4)
        self.assertEqual(metrics.win_rate, 0.5)
        self.assertAlmostEqual(metrics.expectancy, 0.375)
        self.assertGreater(metrics.profit_factor, 1)
        self.assertGreaterEqual(metrics.max_drawdown, 0)
        self.assertNotEqual(metrics.mfe, 0)
        self.assertNotEqual(metrics.mae, 0)

    def test_backtest_applies_cost_assumptions(self) -> None:
        candles = make_candles([1 + index * 0.05 for index in range(40)])
        result = BacktestEngine().run(
            BacktestInput(
                instrument="EURUSD",
                strategy="fixture",
                timeframe="M1",
                candles=candles,
                spread_cost_r=0.1,
                slippage_cost_r=0.1,
            ),
            every_five_bars_signal,
            lookahead_bars=4,
        )

        self.assertGreater(result.metrics.trades, 0)
        self.assertEqual(result.assumptions["spread_cost_r"], 0.1)
        self.assertEqual(result.assumptions["slippage_cost_r"], 0.1)
        self.assertTrue(all(value <= 1.8 for value in result.r_multiples))

    def test_walk_forward_and_monte_carlo_are_deterministic(self) -> None:
        splits = make_walk_forward_splits(100, train_size=40, validation_size=20, step=20)
        monte_carlo = monte_carlo_drawdowns((2.0, -1.0, 1.0, -0.5), runs=10, seed=7)

        self.assertEqual(len(splits), 3)
        self.assertEqual(splits[0].train_start, 0)
        self.assertEqual(splits[0].validation_start, 40)
        self.assertEqual(monte_carlo.runs, 10)
        self.assertGreaterEqual(monte_carlo.worst_drawdown, monte_carlo.median_drawdown)

    def test_auto_gate_blocks_without_documented_positive_oos(self) -> None:
        decision = AutoValidationGate().evaluate(
            AutoGateEvidence(
                backtest=PerformanceMetrics(10, 0.6, 0.2, 1.5, 2.0, 1.0, -0.5, 1.2, -0.8),
                out_of_sample=PerformanceMetrics(10, 0.4, -0.1, 0.8, 4.0, 1.0, -1.0, 1.0, -1.0),
                demo_trades=0,
                shadow_trades=5,
                manual_trades=5,
                max_allowed_drawdown=3.0,
                documented=False,
            )
        )

        self.assertEqual(decision.verdict, AutoGateVerdict.BLOCK)
        self.assertIn("validation evidence is not documented", decision.reasons)
        self.assertIn("out-of-sample expectancy/profit factor failed", decision.reasons)

    def test_auto_gate_allows_only_when_all_gates_pass(self) -> None:
        good = PerformanceMetrics(30, 0.55, 0.2, 1.4, 2.0, 1.0, -0.7, 1.3, -0.6)
        decision = AutoValidationGate().evaluate(
            AutoGateEvidence(
                backtest=good,
                out_of_sample=good,
                demo_trades=10,
                shadow_trades=10,
                manual_trades=10,
                max_allowed_drawdown=3.0,
                documented=True,
            )
        )

        self.assertEqual(decision.verdict, AutoGateVerdict.ALLOW)

    def test_load_auto_gate_evidence_reads_a_documented_json_file(self) -> None:
        metrics = {
            "trades": 30,
            "win_rate": 0.55,
            "expectancy": 0.2,
            "profit_factor": 1.4,
            "max_drawdown": 2.0,
            "average_win": 1.0,
            "average_loss": -0.7,
            "mfe": 1.3,
            "mae": -0.6,
        }
        with TemporaryDirectory() as tmp:
            evidence_path = Path(tmp) / "auto_gate_evidence.json"
            evidence_path.write_text(
                json.dumps(
                    {
                        "backtest": metrics,
                        "out_of_sample": metrics,
                        "demo_trades": 10,
                        "shadow_trades": 10,
                        "manual_trades": 10,
                        "max_allowed_drawdown": 3.0,
                        "documented": True,
                    }
                ),
                encoding="utf-8",
            )

            evidence = load_auto_gate_evidence(evidence_path)
            decision = AutoValidationGate().evaluate(evidence)

        self.assertEqual(decision.verdict, AutoGateVerdict.ALLOW)

    def test_load_auto_gate_evidence_rejects_missing_file(self) -> None:
        with self.assertRaises(AutoGateEvidenceError):
            load_auto_gate_evidence("/nonexistent/auto_gate_evidence.json")

    def test_load_auto_gate_evidence_rejects_missing_fields(self) -> None:
        with TemporaryDirectory() as tmp:
            evidence_path = Path(tmp) / "auto_gate_evidence.json"
            evidence_path.write_text(json.dumps({"documented": True}), encoding="utf-8")

            with self.assertRaises(AutoGateEvidenceError):
                load_auto_gate_evidence(evidence_path)

    def test_vps_readiness_blocks_business_logic_changes(self) -> None:
        report = check_vps_readiness(
            mt5_installed=True,
            python_installed=True,
            secrets_externalized=True,
            supervisor_configured=True,
            business_logic_changed=True,
        )

        self.assertFalse(report.ready)
        self.assertIn("VPS migration must not change trading business logic", report.blockers)

    def test_local_heartbeat_and_backup(self) -> None:
        heartbeat = heartbeat_status(mt5_connected=True)
        self.assertTrue(heartbeat.healthy)

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "trading.db"
            config_dir = root / "config"
            destination = root / "backup"
            db.write_text("sqlite fixture", encoding="utf-8")
            config_dir.mkdir()
            (config_dir / "settings.yaml").write_text("mode: MONITORING", encoding="utf-8")

            manifest = backup_runtime_files(db_path=db, config_dir=config_dir, destination=destination)

            self.assertEqual(len(manifest.files), 2)
            self.assertTrue((destination / "trading.db").exists())
            self.assertTrue((destination / "config" / "settings.yaml").exists())


if __name__ == "__main__":
    unittest.main()

