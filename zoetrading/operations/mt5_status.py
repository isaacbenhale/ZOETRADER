"""Status file writer and command file reader for the MQL5 companion EA."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from zoetrading.domain import Decision, SystemStatus


def _write_atomic(path: Path, content: str) -> None:
    """Write content so a concurrent reader never sees a partial file.

    The MT5 EA polls this file on a 1s timer while Python rewrites it every
    scan cycle; a plain write() can be observed mid-write (e.g. a "mode,"
    line with no value yet), which desyncs the EA's key/value parsing and
    scrambles the whole panel. Writing to a temp file in the same directory
    then os.replace()-ing it is atomic on both POSIX and Windows.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="ascii", newline="") as handle:
            handle.write(content)
        os.replace(tmp_path, path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def write_status_file(
    path: str | Path,
    *,
    status: SystemStatus,
    mode: str,
    decision: Decision | None = None,
    risk: str = "-",
) -> None:
    output = Path(path)
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
    content = "".join(f"{key},{value}\n" for key, value in rows.items())
    _write_atomic(output, content)


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


def write_command_file(path: str | Path, *, command: str, decision_id: str | None) -> None:
    """Write a command in the same format the MT5 EA uses.

    Lets any other approval surface (the local web UI) feed the exact same
    command file the EA writes to, so both are read by the same
    ManualApprovalLoop with the same decision_id check -- no separate
    execution path is introduced.
    """

    _write_atomic(Path(path), f"command,{command}\ndecision_id,{decision_id or '-'}\n")

