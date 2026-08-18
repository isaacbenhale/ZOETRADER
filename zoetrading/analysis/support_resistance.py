"""Support/resistance level detection."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from zoetrading.analysis.market_structure import SwingPoint


@dataclass(frozen=True)
class PriceLevel:
    kind: str
    price: float
    touches: int

    def __post_init__(self) -> None:
        if self.kind not in {"SUPPORT", "RESISTANCE"}:
            raise ValueError("level kind must be SUPPORT or RESISTANCE")
        if self.touches <= 0:
            raise ValueError("touches must be positive")


def find_price_levels(
    swings: Sequence[SwingPoint],
    *,
    tolerance: float,
    min_touches: int = 2,
) -> tuple[PriceLevel, ...]:
    if tolerance < 0:
        raise ValueError("tolerance must be zero or positive")
    if min_touches <= 0:
        raise ValueError("min_touches must be positive")

    levels: list[PriceLevel] = []
    for kind, level_kind in (("LOW", "SUPPORT"), ("HIGH", "RESISTANCE")):
        prices = [swing.price for swing in swings if swing.kind == kind]
        clusters = _cluster_prices(prices, tolerance)
        for cluster in clusters:
            if len(cluster) >= min_touches:
                levels.append(
                    PriceLevel(
                        kind=level_kind,
                        price=sum(cluster) / len(cluster),
                        touches=len(cluster),
                    )
                )
    return tuple(sorted(levels, key=lambda level: (level.kind, level.price)))


def _cluster_prices(prices: Sequence[float], tolerance: float) -> list[list[float]]:
    clusters: list[list[float]] = []
    for price in sorted(prices):
        for cluster in clusters:
            cluster_average = sum(cluster) / len(cluster)
            if abs(price - cluster_average) <= tolerance:
                cluster.append(price)
                break
        else:
            clusters.append([price])
    return clusters

