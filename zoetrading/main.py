"""Neutral bootstrap entry point for zoeTrading."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from zoetrading.config import ConfigError, load_app_config
from zoetrading.config.models import AppConfig
from zoetrading.domain import RuntimeMode


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
    parser = argparse.ArgumentParser(description="Start zoeTrading in neutral bootstrap mode.")
    parser.add_argument(
        "--mode",
        choices=[RuntimeMode.OFF, RuntimeMode.MONITORING, RuntimeMode.MANUAL],
        help="Runtime mode for bootstrap. AUTO is intentionally unavailable.",
    )
    parser.add_argument(
        "--config-dir",
        default=os.getenv("ZOETRADING_CONFIG_DIR", "config"),
        help="Directory containing settings.yaml, risk.yaml and instruments.yaml.",
    )
    args = parser.parse_args(argv)

    try:
        state = build_state(args.mode, args.config_dir)
    except ConfigError as exc:
        parser.exit(status=2, message=f"Configuration error: {exc}\n")
    print(render_state(state))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
