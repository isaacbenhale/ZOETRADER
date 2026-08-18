"""Strategy parameters separated by instrument family."""

from __future__ import annotations

from dataclasses import dataclass

from zoetrading.domain import InstrumentFamily


@dataclass(frozen=True)
class StrategyParameters:
    minimum_score: int
    stop_buffer_atr: float
    target_rr: float
    retest_tolerance_atr: float
    range_edge_tolerance_atr: float


FOREX_PARAMETERS = StrategyParameters(
    minimum_score=70,
    stop_buffer_atr=0.25,
    target_rr=1.8,
    retest_tolerance_atr=0.35,
    range_edge_tolerance_atr=0.40,
)

SYNTHETIC_PARAMETERS = StrategyParameters(
    minimum_score=75,
    stop_buffer_atr=0.35,
    target_rr=2.0,
    retest_tolerance_atr=0.50,
    range_edge_tolerance_atr=0.55,
)


def parameters_for_family(family: InstrumentFamily) -> StrategyParameters:
    if family is InstrumentFamily.FOREX:
        return FOREX_PARAMETERS
    if family is InstrumentFamily.SYNTHETIC:
        return SYNTHETIC_PARAMETERS
    raise ValueError(f"Unsupported instrument family: {family}")

