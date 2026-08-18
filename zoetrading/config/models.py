"""Validated configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from zoetrading.domain.enums import InstrumentFamily, RuntimeMode


def _require_non_empty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_pct(value: float, field_name: str, *, allow_zero: bool = False) -> None:
    if allow_zero and value == 0:
        return
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")
    if value > 100:
        raise ValueError(f"{field_name} cannot exceed 100")


@dataclass(frozen=True)
class MarketConfig:
    refresh_interval_seconds: int
    context_timeframes: tuple[str, ...]
    setup_timeframes: tuple[str, ...]
    timing_timeframes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.refresh_interval_seconds <= 0:
            raise ValueError("market.refresh_interval_seconds must be positive")
        for name, values in (
            ("market.timeframes.context", self.context_timeframes),
            ("market.timeframes.setup", self.setup_timeframes),
            ("market.timeframes.timing", self.timing_timeframes),
        ):
            if not values:
                raise ValueError(f"{name} must not be empty")
            for value in values:
                _require_non_empty(value, name)


@dataclass(frozen=True)
class DecisionConfig:
    minimum_setup_score: int
    allow_no_trade: bool

    def __post_init__(self) -> None:
        if not 0 <= self.minimum_setup_score <= 100:
            raise ValueError("decision.minimum_setup_score must be between 0 and 100")


@dataclass(frozen=True)
class ExecutionConfig:
    require_fresh_market_data: bool
    prevent_duplicate_orders: bool


@dataclass(frozen=True)
class SettingsConfig:
    environment: str
    mode: RuntimeMode
    log_dir: Path
    data_dir: Path
    market: MarketConfig
    decision: DecisionConfig
    execution: ExecutionConfig

    def __post_init__(self) -> None:
        _require_non_empty(self.environment, "environment")


@dataclass(frozen=True)
class RiskConfig:
    risk_per_trade_pct: float
    max_daily_loss_pct: float
    max_weekly_loss_pct: float
    max_open_positions: int
    max_consecutive_losses: int
    cooldown_minutes_after_losses: int
    stop_loss_required: bool
    martingale: bool
    minimum_rr_by_strategy: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_pct(self.risk_per_trade_pct, "risk.risk_per_trade_pct")
        _require_pct(self.max_daily_loss_pct, "risk.max_daily_loss_pct")
        _require_pct(self.max_weekly_loss_pct, "risk.max_weekly_loss_pct")
        if self.max_open_positions <= 0:
            raise ValueError("risk.max_open_positions must be positive")
        if self.max_consecutive_losses < 0:
            raise ValueError("risk.max_consecutive_losses must be zero or positive")
        if self.cooldown_minutes_after_losses < 0:
            raise ValueError("risk.cooldown_minutes_after_losses must be zero or positive")
        if not self.stop_loss_required:
            raise ValueError("risk.stop_loss_required must remain true")
        if self.martingale:
            raise ValueError("risk.martingale must remain false")
        for strategy, minimum_rr in self.minimum_rr_by_strategy.items():
            _require_non_empty(strategy, "risk.minimum_rr_by_strategy key")
            if minimum_rr <= 0:
                raise ValueError("risk.minimum_rr_by_strategy values must be positive")


@dataclass(frozen=True)
class InstrumentConfig:
    symbol: str
    family: InstrumentFamily
    enabled: bool
    timeframes: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_non_empty(self.symbol, "instrument.symbol")
        if not self.timeframes:
            raise ValueError(f"instrument '{self.symbol}' must define timeframes")
        for timeframe in self.timeframes:
            _require_non_empty(timeframe, f"instrument '{self.symbol}' timeframe")


@dataclass(frozen=True)
class InstrumentsConfig:
    instruments: tuple[InstrumentConfig, ...]

    def __post_init__(self) -> None:
        if not self.instruments:
            raise ValueError("instruments must not be empty")
        enabled_symbols = [item.symbol for item in self.instruments if item.enabled]
        if not enabled_symbols:
            raise ValueError("at least one instrument must be enabled")
        if len(set(enabled_symbols)) != len(enabled_symbols):
            raise ValueError("enabled instrument symbols must be unique")


@dataclass(frozen=True)
class AppConfig:
    settings: SettingsConfig
    risk: RiskConfig
    instruments: InstrumentsConfig

