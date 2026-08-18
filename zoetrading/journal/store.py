"""SQLite-backed audit journal for zoeTrading."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Any

from zoetrading.config.models import AppConfig
from zoetrading.domain import Decision, OrderRequest, PositionState, RiskVerdict, Signal
from zoetrading.journal.ids import new_event_id
from zoetrading.journal.serialization import dumps_json, loads_json, stable_hash, to_jsonable


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS config_snapshots (
    config_hash TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    instrument TEXT NOT NULL,
    action TEXT NOT NULL,
    strategy TEXT NOT NULL,
    setup_score INTEGER NOT NULL,
    regime TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    config_hash TEXT,
    FOREIGN KEY(config_hash) REFERENCES config_snapshots(config_hash)
);

CREATE TABLE IF NOT EXISTS risk_decisions (
    decision_id TEXT PRIMARY KEY,
    verdict TEXT NOT NULL,
    risk_per_trade_pct REAL NOT NULL,
    position_size REAL,
    max_loss_amount REAL,
    reasons_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    signal_id TEXT NOT NULL,
    final_action TEXT NOT NULL,
    risk_verdict TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    config_hash TEXT,
    FOREIGN KEY(signal_id) REFERENCES signals(signal_id),
    FOREIGN KEY(decision_id) REFERENCES risk_decisions(decision_id),
    FOREIGN KEY(config_hash) REFERENCES config_snapshots(config_hash)
);

CREATE TABLE IF NOT EXISTS rejections (
    rejection_id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT,
    signal_id TEXT,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(decision_id) REFERENCES decisions(decision_id),
    FOREIGN KEY(signal_id) REFERENCES signals(signal_id)
);

CREATE TABLE IF NOT EXISTS order_requests (
    order_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    instrument TEXT NOT NULL,
    action TEXT NOT NULL,
    volume REAL NOT NULL,
    entry REAL NOT NULL,
    stop_loss REAL NOT NULL,
    take_profit REAL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(decision_id) REFERENCES decisions(decision_id)
);

CREATE TABLE IF NOT EXISTS positions (
    position_id TEXT PRIMARY KEY,
    instrument TEXT NOT NULL,
    action TEXT NOT NULL,
    volume REAL NOT NULL,
    entry REAL NOT NULL,
    opened_at TEXT NOT NULL,
    status TEXT NOT NULL,
    current_sl REAL NOT NULL,
    current_tp REAL,
    unrealized_pnl REAL NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    entity_id TEXT,
    severity TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    instrument TEXT,
    strategy TEXT,
    timeframe TEXT,
    regime TEXT,
    value REAL NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class DecisionTrace:
    decision: dict[str, Any]
    signal: dict[str, Any]
    risk: dict[str, Any]
    rejections: tuple[str, ...]
    config: dict[str, Any] | None


class JournalStore:
    """Persist audit records in SQLite and expose basic read paths."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        if self.db_path != Path(":memory:"):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.db_path))
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(SCHEMA)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "JournalStore":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def save_config_snapshot(self, config: AppConfig | dict[str, Any]) -> str:
        payload = to_jsonable(config)
        config_hash = stable_hash(payload)
        self._connection.execute(
            """
            INSERT OR IGNORE INTO config_snapshots (config_hash, payload_json, created_at)
            VALUES (?, ?, ?)
            """,
            (config_hash, dumps_json(payload), _now_iso()),
        )
        self._connection.commit()
        return config_hash

    def log_signal(self, signal: Signal, *, config_hash: str | None = None) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO signals (
                signal_id, instrument, action, strategy, setup_score, regime,
                generated_at, payload_json, config_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                signal.signal_id,
                signal.instrument,
                signal.action.value,
                signal.strategy,
                signal.setup_score,
                signal.regime.value,
                signal.generated_at.isoformat(),
                dumps_json(signal),
                config_hash,
            ),
        )
        self._connection.execute(
            "DELETE FROM rejections WHERE signal_id = ? AND decision_id IS NULL",
            (signal.signal_id,),
        )
        for reason in signal.blockers:
            self._insert_rejection(signal_id=signal.signal_id, decision_id=None, reason=reason.value)
        self._connection.commit()

    def log_decision(self, decision: Decision, *, config_hash: str | None = None) -> None:
        self.log_signal(decision.signal, config_hash=config_hash)
        risk = decision.risk
        self._connection.execute(
            """
            INSERT OR REPLACE INTO risk_decisions (
                decision_id, verdict, risk_per_trade_pct, position_size, max_loss_amount,
                reasons_json, payload_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                risk.decision_id,
                risk.verdict.value,
                risk.risk_per_trade_pct,
                risk.position_size,
                risk.max_loss_amount,
                dumps_json(risk.reasons),
                dumps_json(risk),
                _now_iso(),
            ),
        )
        self._connection.execute(
            """
            INSERT OR REPLACE INTO decisions (
                decision_id, signal_id, final_action, risk_verdict,
                created_at, payload_json, config_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision.decision_id,
                decision.signal.signal_id,
                decision.final_action.value,
                risk.verdict.value,
                decision.created_at.isoformat(),
                dumps_json(decision),
                config_hash,
            ),
        )
        self._connection.execute(
            "DELETE FROM rejections WHERE decision_id = ?",
            (decision.decision_id,),
        )
        if risk.verdict is RiskVerdict.REJECT:
            for reason in risk.reasons:
                self._insert_rejection(
                    signal_id=decision.signal.signal_id,
                    decision_id=decision.decision_id,
                    reason=reason.value,
                )
        self._connection.commit()

    def log_order_request(self, order: OrderRequest) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO order_requests (
                order_id, decision_id, instrument, action, volume, entry,
                stop_loss, take_profit, payload_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order.order_id,
                order.decision_id,
                order.instrument,
                order.action.value,
                order.volume,
                order.entry,
                order.stop_loss,
                order.take_profit,
                dumps_json(order),
                _now_iso(),
            ),
        )
        self._connection.commit()

    def log_position(self, position: PositionState) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO positions (
                position_id, instrument, action, volume, entry, opened_at, status,
                current_sl, current_tp, unrealized_pnl, payload_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                position.position_id,
                position.instrument,
                position.action.value,
                position.volume,
                position.entry,
                position.opened_at.isoformat(),
                position.status.value,
                position.current_sl,
                position.current_tp,
                position.unrealized_pnl,
                dumps_json(position),
                _now_iso(),
            ),
        )
        self._connection.commit()

    def log_event(
        self,
        event_type: str,
        *,
        entity_id: str | None = None,
        severity: str = "INFO",
        payload: dict[str, Any] | None = None,
    ) -> str:
        event_id = new_event_id()
        self._connection.execute(
            """
            INSERT INTO events (event_id, event_type, entity_id, severity, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_id, event_type, entity_id, severity.upper(), dumps_json(payload or {}), _now_iso()),
        )
        self._connection.commit()
        return event_id

    def record_metric(
        self,
        metric_name: str,
        value: float,
        *,
        instrument: str | None = None,
        strategy: str | None = None,
        timeframe: str | None = None,
        regime: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO metrics (
                metric_name, instrument, strategy, timeframe, regime,
                value, payload_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metric_name,
                instrument,
                strategy,
                timeframe,
                regime,
                value,
                dumps_json(payload or {}),
                _now_iso(),
            ),
        )
        self._connection.commit()

    def get_decision_trace(self, decision_id: str) -> DecisionTrace:
        decision_row = self._fetch_one("SELECT * FROM decisions WHERE decision_id = ?", decision_id)
        signal_row = self._fetch_one("SELECT * FROM signals WHERE signal_id = ?", decision_row["signal_id"])
        risk_row = self._fetch_one("SELECT * FROM risk_decisions WHERE decision_id = ?", decision_id)
        rejection_rows = self._connection.execute(
            "SELECT reason FROM rejections WHERE decision_id = ? OR signal_id = ? ORDER BY rejection_id",
            (decision_id, signal_row["signal_id"]),
        ).fetchall()

        config = None
        if decision_row["config_hash"]:
            config_row = self._fetch_one(
                "SELECT payload_json FROM config_snapshots WHERE config_hash = ?",
                decision_row["config_hash"],
            )
            config = loads_json(config_row["payload_json"])

        return DecisionTrace(
            decision=loads_json(decision_row["payload_json"]),
            signal=loads_json(signal_row["payload_json"]),
            risk=loads_json(risk_row["payload_json"]),
            rejections=tuple(row["reason"] for row in rejection_rows),
            config=config,
        )

    def analytics_summary(self) -> dict[str, int]:
        return {
            "signals": self._count("signals"),
            "decisions": self._count("decisions"),
            "rejections": self._count("rejections"),
            "orders": self._count("order_requests"),
            "positions": self._count("positions"),
            "events": self._count("events"),
            "metrics": self._count("metrics"),
        }

    def _insert_rejection(self, *, signal_id: str | None, decision_id: str | None, reason: str) -> None:
        self._connection.execute(
            """
            INSERT INTO rejections (decision_id, signal_id, reason, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (decision_id, signal_id, reason, _now_iso()),
        )

    def _fetch_one(self, query: str, *params: object) -> sqlite3.Row:
        row = self._connection.execute(query, params).fetchone()
        if row is None:
            raise KeyError(f"Journal record not found for query: {query}")
        return row

    def _count(self, table: str) -> int:
        row = self._connection.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
        return int(row["total"])


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
