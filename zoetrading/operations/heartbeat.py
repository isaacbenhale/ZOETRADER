"""Heartbeat helpers for local laptop operation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class Heartbeat:
    python_running: bool
    mt5_connected: bool
    checked_at: datetime

    @property
    def healthy(self) -> bool:
        return self.python_running and self.mt5_connected


def heartbeat_status(*, mt5_connected: bool) -> Heartbeat:
    return Heartbeat(python_running=True, mt5_connected=mt5_connected, checked_at=datetime.now(UTC))

