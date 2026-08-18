"""Operational CLI entry point for zoeTrading."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from zoetrading.config import ConfigError, load_app_config
from zoetrading.config.models import AppConfig
from zoetrading.domain import RuntimeMode
from zoetrading.journal import JournalStore
from zoetrading.market import MT5Client, MT5ConnectionError
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


if __name__ == "__main__":
    raise SystemExit(cli())
