"""Status file writer consumed by the MQL5 companion EA."""

from __future__ import annotations

from pathlib import Path

from zoetrading.domain import Decision, SystemStatus


def write_status_file(
    path: str | Path,
    *,
    status: SystemStatus,
    mode: str,
    decision: Decision | None = None,
    risk: str = "-",
) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = {
        "status": status.value,
        "mode": mode,
        "signal": "NO SIGNAL",
        "strategy": "-",
        "regime": "-",
        "score": "-",
        "entry": "-",
        "sl": "-",
        "tp": "-",
        "risk": risk,
    }
    if decision is not None:
        signal = decision.signal
        rows.update(
            {
                "signal": f"{decision.final_action.value} {signal.instrument}",
                "strategy": signal.strategy,
                "regime": signal.regime.value,
                "score": str(signal.setup_score),
                "entry": _fmt(signal.entry),
                "sl": _fmt(signal.proposed_sl),
                "tp": _fmt(signal.proposed_tp),
                "risk": f"{decision.risk.risk_per_trade_pct:.2f}%",
            }
        )
    with output.open("w", encoding="ascii", newline="") as handle:
        for key, value in rows.items():
            handle.write(f"{key},{value}\n")


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.5f}"

