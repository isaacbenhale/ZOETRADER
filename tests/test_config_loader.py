from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from zoetrading.config import ConfigError, load_app_config
from zoetrading.domain import InstrumentFamily, RuntimeMode


class ConfigLoaderTests(unittest.TestCase):
    def test_load_default_config(self) -> None:
        config = load_app_config("config")

        self.assertEqual(config.settings.mode, RuntimeMode.MONITORING)
        self.assertEqual(config.risk.risk_per_trade_pct, 0.5)
        self.assertFalse(config.risk.martingale)
        self.assertTrue(config.risk.stop_loss_required)
        self.assertGreaterEqual(len(config.instruments.instruments), 1)
        self.assertEqual(config.instruments.instruments[0].family, InstrumentFamily.SYNTHETIC)

    def test_invalid_config_fails_explicitly(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "settings.yaml").write_text(
                """
environment: local
mode: MONITORING
log_dir: logs
data_dir: data
market:
  refresh_interval_seconds: 5
  timeframes:
    context: [H4]
    setup: [M15]
    timing: [M1]
decision:
  minimum_setup_score: 80
  allow_no_trade: true
execution:
  require_fresh_market_data: true
  prevent_duplicate_orders: true
""",
                encoding="utf-8",
            )
            (root / "risk.yaml").write_text(
                """
risk_per_trade_pct: 0.5
max_daily_loss_pct: 2.0
max_weekly_loss_pct: 5.0
max_open_positions: 3
max_consecutive_losses: 3
cooldown_minutes_after_losses: 60
stop_loss_required: false
martingale: false
minimum_rr_by_strategy: {}
""",
                encoding="utf-8",
            )
            (root / "instruments.yaml").write_text(
                """
instruments:
  - symbol: EURUSD
    family: forex
    enabled: true
    timeframes: [M1, M5]
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ConfigError, "stop_loss_required"):
                load_app_config(root)


if __name__ == "__main__":
    unittest.main()

