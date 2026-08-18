"""YAML configuration loader with explicit validation errors."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from zoetrading.config.models import (
    AppConfig,
    DecisionConfig,
    ExecutionConfig,
    InstrumentConfig,
    InstrumentsConfig,
    MarketConfig,
    RiskConfig,
    SettingsConfig,
)
from zoetrading.domain.enums import InstrumentFamily, RuntimeMode


class ConfigError(ValueError):
    """Raised when a configuration file is missing or invalid."""


def load_app_config(config_dir: str | Path = "config") -> AppConfig:
    root = Path(config_dir)
    try:
        return AppConfig(
            settings=_load_settings(root / "settings.yaml"),
            risk=_load_risk(root / "risk.yaml"),
            instruments=_load_instruments(root / "instruments.yaml"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, ConfigError):
            raise
        raise ConfigError(f"Invalid configuration in {root}: {exc}") from exc


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Missing configuration file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ConfigError(f"Configuration file must contain a mapping: {path}")
    return data


def _as_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{field_name} must be a boolean")
    return value


def _as_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{field_name} must be an integer")
    return value


def _as_float(value: Any, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigError(f"{field_name} must be a number")
    return float(value)


def _as_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ConfigError(f"{field_name} must be a string")
    return value


def _as_str_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ConfigError(f"{field_name} must be a list")
    result = []
    for item in value:
        result.append(_as_str(item, field_name))
    return tuple(result)


def _load_settings(path: Path) -> SettingsConfig:
    data = _read_yaml(path)
    market = data["market"]
    timeframes = market["timeframes"]
    decision = data["decision"]
    execution = data["execution"]
    return SettingsConfig(
        environment=_as_str(data["environment"], "settings.environment"),
        mode=RuntimeMode(_as_str(data["mode"], "settings.mode").upper()),
        log_dir=Path(_as_str(data["log_dir"], "settings.log_dir")),
        data_dir=Path(_as_str(data["data_dir"], "settings.data_dir")),
        market=MarketConfig(
            refresh_interval_seconds=_as_int(
                market["refresh_interval_seconds"],
                "settings.market.refresh_interval_seconds",
            ),
            context_timeframes=_as_str_tuple(
                timeframes["context"],
                "settings.market.timeframes.context",
            ),
            setup_timeframes=_as_str_tuple(
                timeframes["setup"],
                "settings.market.timeframes.setup",
            ),
            timing_timeframes=_as_str_tuple(
                timeframes["timing"],
                "settings.market.timeframes.timing",
            ),
        ),
        decision=DecisionConfig(
            minimum_setup_score=_as_int(
                decision["minimum_setup_score"],
                "settings.decision.minimum_setup_score",
            ),
            allow_no_trade=_as_bool(decision["allow_no_trade"], "settings.decision.allow_no_trade"),
        ),
        execution=ExecutionConfig(
            require_fresh_market_data=_as_bool(
                execution["require_fresh_market_data"],
                "settings.execution.require_fresh_market_data",
            ),
            prevent_duplicate_orders=_as_bool(
                execution["prevent_duplicate_orders"],
                "settings.execution.prevent_duplicate_orders",
            ),
        ),
    )


def _load_risk(path: Path) -> RiskConfig:
    data = _read_yaml(path)
    minimum_rr_raw = data.get("minimum_rr_by_strategy", {})
    if not isinstance(minimum_rr_raw, dict):
        raise ConfigError("risk.minimum_rr_by_strategy must be a mapping")
    return RiskConfig(
        risk_per_trade_pct=_as_float(data["risk_per_trade_pct"], "risk.risk_per_trade_pct"),
        max_daily_loss_pct=_as_float(data["max_daily_loss_pct"], "risk.max_daily_loss_pct"),
        max_weekly_loss_pct=_as_float(data["max_weekly_loss_pct"], "risk.max_weekly_loss_pct"),
        max_open_positions=_as_int(data["max_open_positions"], "risk.max_open_positions"),
        max_consecutive_losses=_as_int(
            data["max_consecutive_losses"],
            "risk.max_consecutive_losses",
        ),
        cooldown_minutes_after_losses=_as_int(
            data["cooldown_minutes_after_losses"],
            "risk.cooldown_minutes_after_losses",
        ),
        stop_loss_required=_as_bool(data["stop_loss_required"], "risk.stop_loss_required"),
        martingale=_as_bool(data["martingale"], "risk.martingale"),
        minimum_rr_by_strategy={
            _as_str(strategy, "risk.minimum_rr_by_strategy key"): _as_float(
                minimum_rr,
                f"risk.minimum_rr_by_strategy.{strategy}",
            )
            for strategy, minimum_rr in minimum_rr_raw.items()
        },
    )


def _load_instruments(path: Path) -> InstrumentsConfig:
    data = _read_yaml(path)
    raw_instruments = data["instruments"]
    if not isinstance(raw_instruments, list):
        raise ConfigError("instruments.instruments must be a list")
    instruments = []
    for raw in raw_instruments:
        if not isinstance(raw, dict):
            raise ConfigError("each instrument must be a mapping")
        instruments.append(
            InstrumentConfig(
                symbol=_as_str(raw["symbol"], "instrument.symbol"),
                family=InstrumentFamily(_as_str(raw["family"], "instrument.family").lower()),
                enabled=_as_bool(raw["enabled"], "instrument.enabled"),
                timeframes=_as_str_tuple(raw["timeframes"], "instrument.timeframes"),
            )
        )
    return InstrumentsConfig(instruments=tuple(instruments))

