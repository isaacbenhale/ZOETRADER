"""Formal gate for enabling real AUTO mode."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

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


class AutoGateEvidenceError(ValueError):
    pass


_METRICS_FIELDS = (
    "trades",
    "win_rate",
    "expectancy",
    "profit_factor",
    "max_drawdown",
    "average_win",
    "average_loss",
    "mfe",
    "mae",
)
_EVIDENCE_FIELDS = (
    "backtest",
    "out_of_sample",
    "demo_trades",
    "shadow_trades",
    "manual_trades",
    "max_allowed_drawdown",
    "documented",
)


def _metrics_from_dict(raw: dict, *, field_name: str) -> PerformanceMetrics:
    missing = [name for name in _METRICS_FIELDS if name not in raw]
    if missing:
        raise AutoGateEvidenceError(f"{field_name} is missing fields: {', '.join(missing)}")
    return PerformanceMetrics(**{name: raw[name] for name in _METRICS_FIELDS})


def load_auto_gate_evidence(path: str | Path) -> AutoGateEvidence:
    """Load documented AUTO-gate evidence from a JSON file.

    This is the only supported way to build `AutoGateEvidence` for a real run:
    it forces the evidence (backtest, out-of-sample, demo/shadow/manual trade
    counts) to exist as a file on disk that the operator wrote deliberately,
    rather than as ad hoc numbers passed on the command line.
    """

    evidence_path = Path(path)
    try:
        raw = json.loads(evidence_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AutoGateEvidenceError(f"AUTO gate evidence file not found: {evidence_path}") from exc
    except json.JSONDecodeError as exc:
        raise AutoGateEvidenceError(f"AUTO gate evidence file is not valid JSON: {evidence_path}") from exc

    missing = [name for name in _EVIDENCE_FIELDS if name not in raw]
    if missing:
        raise AutoGateEvidenceError(f"AUTO gate evidence file is missing fields: {', '.join(missing)}")

    return AutoGateEvidence(
        backtest=_metrics_from_dict(raw["backtest"], field_name="backtest"),
        out_of_sample=_metrics_from_dict(raw["out_of_sample"], field_name="out_of_sample"),
        demo_trades=int(raw["demo_trades"]),
        shadow_trades=int(raw["shadow_trades"]),
        manual_trades=int(raw["manual_trades"]),
        max_allowed_drawdown=float(raw["max_allowed_drawdown"]),
        documented=bool(raw["documented"]),
    )

