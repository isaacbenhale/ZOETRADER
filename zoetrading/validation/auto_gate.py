"""Formal gate for enabling real AUTO mode."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from zoetrading.backtesting.metrics import PerformanceMetrics


class AutoGateVerdict(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class AutoGateEvidence:
    backtest: PerformanceMetrics
    out_of_sample: PerformanceMetrics
    demo_trades: int
    shadow_trades: int
    manual_trades: int
    max_allowed_drawdown: float
    documented: bool


@dataclass(frozen=True)
class AutoGateDecision:
    verdict: AutoGateVerdict
    reasons: tuple[str, ...]


class AutoValidationGate:
    def evaluate(self, evidence: AutoGateEvidence) -> AutoGateDecision:
        reasons: list[str] = []
        if not evidence.documented:
            reasons.append("validation evidence is not documented")
        if not evidence.backtest.profitable:
            reasons.append("backtest expectancy/profit factor failed")
        if not evidence.out_of_sample.profitable:
            reasons.append("out-of-sample expectancy/profit factor failed")
        if evidence.out_of_sample.max_drawdown > evidence.max_allowed_drawdown:
            reasons.append("out-of-sample drawdown exceeds limit")
        if evidence.demo_trades <= 0:
            reasons.append("demo phase has no trades")
        if evidence.shadow_trades <= 0:
            reasons.append("shadow phase has no trades")
        if evidence.manual_trades <= 0:
            reasons.append("manual phase has no trades")
        if reasons:
            return AutoGateDecision(verdict=AutoGateVerdict.BLOCK, reasons=tuple(reasons))
        return AutoGateDecision(verdict=AutoGateVerdict.ALLOW, reasons=("all AUTO gates passed",))

