"""Position sizing helpers."""

from __future__ import annotations


def calculate_position_size(
    *,
    equity: float,
    risk_per_trade_pct: float,
    entry: float,
    stop_loss: float,
    value_per_price_unit: float = 1.0,
) -> tuple[float, float]:
    if equity <= 0:
        raise ValueError("equity must be positive")
    if risk_per_trade_pct <= 0:
        raise ValueError("risk_per_trade_pct must be positive")
    if value_per_price_unit <= 0:
        raise ValueError("value_per_price_unit must be positive")
    distance = abs(entry - stop_loss)
    if distance <= 0:
        raise ValueError("entry and stop_loss must differ")
    max_loss = equity * (risk_per_trade_pct / 100)
    size = max_loss / (distance * value_per_price_unit)
    return size, max_loss

