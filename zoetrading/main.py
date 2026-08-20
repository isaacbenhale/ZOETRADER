"""Operational CLI entry point for zoeTrading."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path

from zoetrading.backtesting import run_library_backtest
from zoetrading.config import ConfigError, load_app_config
from zoetrading.config.models import AppConfig
from zoetrading.domain import RuntimeMode
from zoetrading.journal import JournalStore
from zoetrading.market import MT5Client, MT5ConnectionError, MarketDataEngine
from zoetrading.risk import AccountRiskState
from zoetrading.runtime import RuntimeEngine, connect_mt5_from_env


@dataclass(frozen=True)
class BootstrapState:
    """Minimal startup state before trading modules are implemented."""

    mode: RuntimeMode
    orders_enabled: bool = False
    config_loaded: bool = True


def resolve_mode(raw_mode: str | None, config: AppConfig | None = None) -> RuntimeMode:
    """Resolve a requested mode while keeping AUTO unavailable in bootstrap."""

    configured_mode = config.settings.mode if config else RuntimeMode.MONITORING
    value = (raw_mode or os.getenv("ZOETRADING_MODE") or configured_mode).upper()
    try:
        mode = RuntimeMode(value)
    except ValueError as exc:
        allowed = ", ".join(mode.value for mode in RuntimeMode)
        raise ValueError(f"Invalid mode '{value}'. Allowed values: {allowed}") from exc

    if mode is RuntimeMode.AUTO:
        raise ValueError("AUTO mode is not available during bootstrap.")
    return mode


def build_state(raw_mode: str | None = None, config_dir: str = "config") -> BootstrapState:
    """Build the current neutral state without connecting to MT5."""

    config = load_app_config(config_dir)
    return BootstrapState(mode=resolve_mode(raw_mode, config), orders_enabled=False)


def render_state(state: BootstrapState) -> str:
    """Render a stable startup message for operators and smoke tests."""

    return "\n".join(
        [
            "zoeTrading bootstrap OK",
            f"mode={state.mode.value}",
            f"orders_enabled={str(state.orders_enabled).lower()}",
            f"config_loaded={str(state.config_loaded).lower()}",
        ]
    )


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="zoeTrading operational CLI.")
    subparsers = parser.add_subparsers(dest="command")

    bootstrap = subparsers.add_parser("bootstrap", help="Validate config and start in neutral mode.")
    bootstrap.add_argument(
        "--mode",
        choices=[RuntimeMode.OFF, RuntimeMode.MONITORING, RuntimeMode.MANUAL],
        help="Runtime mode for bootstrap. AUTO is intentionally unavailable.",
    )
    bootstrap.add_argument(
        "--config-dir",
        default=os.getenv("ZOETRADING_CONFIG_DIR", "config"),
        help="Directory containing settings.yaml, risk.yaml and instruments.yaml.",
    )

    healthcheck = subparsers.add_parser("healthcheck", help="Connect to MT5 and verify configured symbols.")
    healthcheck.add_argument("--config-dir", default=os.getenv("ZOETRADING_CONFIG_DIR", "config"))
    healthcheck.add_argument("--journal-db", default="data/trading.db")

    scan = subparsers.add_parser("scan-once", help="Run one MT5 monitoring scan and journal decisions.")
    scan.add_argument("--config-dir", default=os.getenv("ZOETRADING_CONFIG_DIR", "config"))
    scan.add_argument("--mode", choices=[RuntimeMode.MONITORING, RuntimeMode.MANUAL], default=None)
    scan.add_argument("--equity", type=float, required=True, help="Account equity used for risk sizing.")
    scan.add_argument("--journal-db", default="data/trading.db")
    scan.add_argument("--status-file", default="data/zoetrading_status.csv")
    scan.add_argument("--candle-count", type=int, default=200)

    backtest = subparsers.add_parser(
        "backtest",
        help="Measure win rate, expectancy and profit factor of the strategy library against MT5 history.",
    )
    backtest.add_argument("--config-dir", default=os.getenv("ZOETRADING_CONFIG_DIR", "config"))
    backtest.add_argument("--journal-db", default="data/trading.db")
    backtest.add_argument("--candle-count", type=int, default=500)
    backtest.add_argument("--lookahead-bars", type=int, default=20)
    backtest.add_argument("--report-file", default="data/backtest_report.json")

    args = parser.parse_args(argv)
    command = args.command or "bootstrap"

    try:
        if command == "bootstrap":
            state = build_state(
                getattr(args, "mode", None),
                getattr(args, "config_dir", os.getenv("ZOETRADING_CONFIG_DIR", "config")),
            )
            print(render_state(state))
            return 0
        if command == "healthcheck":
            return _healthcheck(args.config_dir, args.journal_db)
        if command == "scan-once":
            return _scan_once(args)
        if command == "backtest":
            return _backtest(args)
    except ConfigError as exc:
        parser.exit(status=2, message=f"Configuration error: {exc}\n")
    parser.exit(status=2, message=f"Unknown command: {command}\n")


def _healthcheck(config_dir: str, journal_db: str) -> int:
    config = load_app_config(config_dir)
    client = MT5Client()
    try:
        connect_mt5_from_env(client)
    except MT5ConnectionError as exc:
        print(f"MT5 healthcheck FAILED: {exc}")
        return 1
    with JournalStore(journal_db) as journal:
        engine = RuntimeEngine(config, mt5_client=client, journal=journal)
        ok, errors = engine.healthcheck()
    if ok:
        print("MT5 healthcheck OK")
        return 0
    print("MT5 healthcheck FAILED")
    for error in errors:
        print(f"- {error}")
    return 1


def _scan_once(args: argparse.Namespace) -> int:
    config = load_app_config(args.config_dir)
    mode = RuntimeMode(args.mode or config.settings.mode)
    client = MT5Client()
    connect_mt5_from_env(client)
    with JournalStore(args.journal_db) as journal:
        engine = RuntimeEngine(
            config,
            mt5_client=client,
            journal=journal,
            status_file=args.status_file,
        )
        result = engine.scan_once(
            mode=mode,
            account_state=AccountRiskState(equity=args.equity),
            candle_count=args.candle_count,
        )
    print(f"scan_complete=true scanned={result.scanned} errors={len(result.errors)}")
    print(f"status_file={result.status_file}")
    for decision in result.decisions:
        signal = decision.signal
        print(
            "decision "
            f"instrument={signal.instrument} action={decision.final_action.value} "
            f"strategy={signal.strategy} score={signal.setup_score} "
            f"risk={decision.risk.verdict.value}"
        )
    for error in result.errors:
        print(f"error {error}")
    return 0 if result.decisions else 1


def _backtest(args: argparse.Namespace) -> int:
    config = load_app_config(args.config_dir)
    client = MT5Client()
    connect_mt5_from_env(client)
    market = MarketDataEngine(client)
    report = run_library_backtest(
        config,
        market,
        candle_count=args.candle_count,
        lookahead_bars=args.lookahead_bars,
    )
    ranked = report.ranked_by_expectancy

    print(f"backtest_complete=true combinations={len(ranked)} skipped={len(report.skipped)}")
    print(
        f"{'instrument':<22}{'strategy':<22}{'timeframe':<6}"
        f"{'trades':>7}{'win_rate':>10}{'expectancy':>12}{'profit_factor':>15}{'max_dd':>9}"
    )
    for result in ranked:
        metrics = result.metrics
        print(
            f"{result.instrument:<22}{result.strategy:<22}{result.timeframe:<6}"
            f"{metrics.trades:>7}{metrics.win_rate:>10.2%}{metrics.expectancy:>12.3f}"
            f"{metrics.profit_factor:>15.2f}{metrics.max_drawdown:>9.2f}"
        )
    for skipped in report.skipped:
        print(f"skipped {skipped}")

    report_path = Path(args.report_file)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "candle_count": args.candle_count,
                "lookahead_bars": args.lookahead_bars,
                "skipped": list(report.skipped),
                "results": [
                    {
                        "instrument": result.instrument,
                        "strategy": result.strategy,
                        "timeframe": result.timeframe,
                        "trades": result.metrics.trades,
                        "win_rate": result.metrics.win_rate,
                        "expectancy": result.metrics.expectancy,
                        "profit_factor": result.metrics.profit_factor,
                        "max_drawdown": result.metrics.max_drawdown,
                        "average_win": result.metrics.average_win,
                        "average_loss": result.metrics.average_loss,
                        "mfe": result.metrics.mfe,
                        "mae": result.metrics.mae,
                        "profitable": result.metrics.profitable,
                    }
                    for result in ranked
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"report_file={report_path}")

    with JournalStore(args.journal_db) as journal:
        journal.log_event(
            "backtest",
            entity_id="strategy_library",
            payload={
                "combinations": len(ranked),
                "skipped": len(report.skipped),
                "report_file": str(report_path),
            },
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
