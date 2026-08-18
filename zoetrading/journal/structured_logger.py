"""Append-only structured JSONL logger."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from zoetrading.journal.ids import new_event_id
from zoetrading.journal.serialization import dumps_json


class StructuredLogger:
    def __init__(self, log_path: str | Path) -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def event(
        self,
        event_type: str,
        *,
        entity_id: str | None = None,
        severity: str = "INFO",
        payload: dict[str, Any] | None = None,
    ) -> str:
        event_id = new_event_id()
        record = {
            "event_id": event_id,
            "event_type": event_type,
            "entity_id": entity_id,
            "severity": severity.upper(),
            "payload": payload or {},
            "created_at": datetime.now(UTC),
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(dumps_json(record) + "\n")
        return event_id

