"""Status file writer and command file reader for the MQL5 companion EA."""

from __future__ import annotations

from dataclasses import dataclass
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
        "decision_id": "-",
    }
    if decision is not None:
        signal = decision.signal
        rows.update(
            {
                "signal": f"{decision.final_action.value} {signal.instrument}",
                "decision_id": decision.decision_id,
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


@dataclass(frozen=True)
class MT5Command:
    command: str
    decision_id: str | None = None


def read_command_file(path: str | Path) -> MT5Command | None:
    """Read a command written by the EA (APPROVE/REJECT/PAUSE/KILL_SWITCH), if present."""

    file_path = Path(path)
    if not file_path.exists():
        return None
    values: dict[str, str] = {}
    for line in file_path.read_text(encoding="ascii").splitlines():
        if "," in line:
            key, value = line.split(",", 1)
            values[key] = value
    command = values.get("command")
    if not command:
        return None
    decision_id = values.get("decision_id")
    return MT5Command(command=command, decision_id=decision_id if decision_id and decision_id != "-" else None)


def consume_command_file(path: str | Path) -> None:
    """Delete a processed (or stale) command file so it is never re-applied."""

    file_path = Path(path)
    if file_path.exists():
        file_path.unlink()

