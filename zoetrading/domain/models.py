"""Core domain models for signals, risk, orders and positions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from zoetrading.domain.enums import (
    MarketRegime,
    PositionStatus,
    RejectionReason,
    RiskVerdict,
    TradeAction,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _require_text(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} is required")


def _require_positive(value: float, field_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


@dataclass(frozen=True)
class MarketSnapshot:
    instrument: str
    timeframe: str
    timestamp: datetime
    bid: float
    ask: float
    spread: float
    is_fresh: bool
    ohlc: tuple[float, float, float, float] | None = None

    def __post_init__(self) -> None:
        _require_text(self.instrument, "instrument")
        _require_text(self.timeframe, "timeframe")
        _require_positive(self.bid, "bid")
        _require_positive(self.ask, "ask")
        if self.ask < self.bid:
            raise ValueError("ask must be greater than or equal to bid")
        if self.spread < 0:
            raise ValueError("spread must be zero or positive")
        if self.ohlc is not None and len(self.ohlc) != 4:
            raise ValueError("ohlc must contain open, high, low and close")


@dataclass(frozen=True)
class Signal:
    signal_id: str
    instrument: str
    action: TradeAction
    strategy: str
    setup_score: int
    regime: MarketRegime
    generated_at: datetime = field(default_factory=utc_now)
    entry: float | None = None
    invalidation: float | None = None
    proposed_sl: float | None = None
    proposed_tp: float | None = None
    expected_rr: float | None = None
    reasons: tuple[str, ...] = ()
    blockers: tuple[RejectionReason, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.signal_id, "signal_id")
        _require_text(self.instrument, "instrument")
        _require_text(self.strategy, "strategy")
        if not 0 <= self.setup_score <= 100:
            raise ValueError("setup_score must be between 0 and 100")
        if self.action is TradeAction.NO_TRADE:
            if not self.reasons and not self.blockers:
                raise ValueError("NO_TRADE signals require reasons or blockers")
            return
        for field_name in ("entry", "invalidation", "proposed_sl", "proposed_tp", "expected_rr"):
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} is required for trade signals")
        _require_positive(float(self.entry), "entry")
        _require_positive(float(self.proposed_sl), "proposed_sl")
        _require_positive(float(self.proposed_tp), "proposed_tp")
        _require_positive(float(self.expected_rr), "expected_rr")


@dataclass(frozen=True)
class RiskDecision:
    decision_id: str
    verdict: RiskVerdict
    reasons: tuple[RejectionReason, ...]
    risk_per_trade_pct: float
    position_size: float | None = None
    max_loss_amount: float | None = None

    def __post_init__(self) -> None:
        _require_text(self.decision_id, "decision_id")
        if self.verdict is RiskVerdict.REJECT and not self.reasons:
            raise ValueError("rejected risk decision requires at least one reason")
        if self.risk_per_trade_pct < 0:
            raise ValueError("risk_per_trade_pct must be zero or positive")
        if self.verdict is RiskVerdict.APPROVE:
            if RejectionReason.KILL_SWITCH in self.reasons:
                raise ValueError("KILL_SWITCH cannot approve risk")
            if self.position_size is None or self.max_loss_amount is None:
                raise ValueError("approved risk requires position_size and max_loss_amount")
            _require_positive(self.position_size, "position_size")
            _require_positive(self.max_loss_amount, "max_loss_amount")


@dataclass(frozen=True)
class Decision:
    decision_id: str
    signal: Signal
    risk: RiskDecision
    final_action: TradeAction
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_text(self.decision_id, "decision_id")
        if self.final_action is TradeAction.NO_TRADE and self.risk.verdict is RiskVerdict.APPROVE:
            raise ValueError("NO_TRADE cannot have an approved risk decision")
        if self.signal.action is not TradeAction.NO_TRADE and self.final_action is TradeAction.NO_TRADE:
            if self.risk.verdict is not RiskVerdict.REJECT:
                raise ValueError("blocked trade decisions require risk rejection")


@dataclass(frozen=True)
class OrderRequest:
    order_id: str
    decision_id: str
    instrument: str
    action: TradeAction
    volume: float
    entry: float
    stop_loss: float
    take_profit: float | None = None
    comment: str = "zoeTrading"

    def __post_init__(self) -> None:
        _require_text(self.order_id, "order_id")
        _require_text(self.decision_id, "decision_id")
        _require_text(self.instrument, "instrument")
        if self.action is TradeAction.NO_TRADE:
            raise ValueError("NO_TRADE cannot create an order request")
        _require_positive(self.volume, "volume")
        _require_positive(self.entry, "entry")
        _require_positive(self.stop_loss, "stop_loss")
        if self.take_profit is not None:
            _require_positive(self.take_profit, "take_profit")


@dataclass(frozen=True)
class PositionState:
    position_id: str
    instrument: str
    action: TradeAction
    volume: float
    entry: float
    opened_at: datetime
    status: PositionStatus
    current_sl: float
    current_tp: float | None = None
    unrealized_pnl: float = 0.0

    def __post_init__(self) -> None:
        _require_text(self.position_id, "position_id")
        _require_text(self.instrument, "instrument")
        if self.action is TradeAction.NO_TRADE:
            raise ValueError("NO_TRADE cannot be a position action")
        _require_positive(self.volume, "volume")
        _require_positive(self.entry, "entry")
        _require_positive(self.current_sl, "current_sl")
        if self.current_tp is not None:
            _require_positive(self.current_tp, "current_tp")
