"""Local-only web UI backend: launch operations and read the journal.

Constraints (see PRD.md "Interface web locale"): this API never approves or
sends an order, never touches AUTO, and never bypasses the Risk Engine. It
only triggers the same CLI operations (bootstrap/healthcheck/scan/backtest)
and reads what is already journaled. MT5 approval stays in the EA panel.
"""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from zoetrading.backtesting import run_library_backtest
from zoetrading.config import ConfigError, load_app_config
from zoetrading.domain import RuntimeMode
from zoetrading.journal import JournalStore
from zoetrading.main import build_state, render_state
from zoetrading.market import MT5Client, MT5ConnectionError, MarketDataEngine
from zoetrading.risk import AccountRiskState
from zoetrading.runtime import RuntimeEngine, connect_mt5_from_env

STATIC_DIR = Path(__file__).parent / "static"


class ScanRequest(BaseModel):
    mode: str = "MONITORING"
    equity: float
    candle_count: int = 200


class BacktestRequest(BaseModel):
    candle_count: int = 500
    lookahead_bars: int = 20


class BootstrapRequest(BaseModel):
    mode: str | None = None


def create_app(
    *,
    config_dir: str = "config",
    journal_db: str = "data/trading.db",
    status_file: str = "data/zoetrading_status.csv",
    report_file: str = "data/backtest_report.json",
    mt5_client_factory: Callable[[], MT5Client] = MT5Client,
) -> FastAPI:
    app = FastAPI(title="zoeTrading local UI", docs_url="/api/docs", redoc_url=None)
    app.state.config_dir = config_dir
    app.state.journal_db = journal_db
    app.state.mt5_client_factory = mt5_client_factory
    app.state.status_file = Path(status_file)
    app.state.report_file = Path(report_file)

    @app.get("/api/health")
    def api_health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/status")
    def api_status() -> dict[str, Any]:
        status: dict[str, str] = {}
        if app.state.status_file.exists():
            for line in app.state.status_file.read_text(encoding="ascii").splitlines():
                if "," in line:
                    key, value = line.split(",", 1)
                    status[key] = value
        with JournalStore(app.state.journal_db) as journal:
            summary = journal.analytics_summary()
        return {"status_file": status, "journal": summary}

    @app.get("/api/decisions")
    def api_decisions(limit: int = 50) -> dict[str, Any]:
        with JournalStore(app.state.journal_db) as journal:
            decisions = journal.list_recent_decisions(limit)
        return {"decisions": decisions}

    @app.get("/api/events")
    def api_events(limit: int = 50, event_type: str | None = None) -> dict[str, Any]:
        with JournalStore(app.state.journal_db) as journal:
            events = journal.list_recent_events(limit, event_type=event_type)
        return {"events": events}

    @app.get("/api/backtest-report")
    def api_backtest_report() -> dict[str, Any]:
        if not app.state.report_file.exists():
            raise HTTPException(status_code=404, detail="no backtest report yet")
        return {"report": _read_json(app.state.report_file)}

    @app.post("/api/actions/bootstrap")
    def action_bootstrap(request: BootstrapRequest) -> dict[str, Any]:
        try:
            state = build_state(request.mode, app.state.config_dir)
        except (ConfigError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"output": render_state(state)}

    @app.post("/api/actions/healthcheck")
    def action_healthcheck() -> dict[str, Any]:
        config = _load_config(app.state.config_dir)
        client = app.state.mt5_client_factory()
        try:
            connect_mt5_from_env(client)
        except MT5ConnectionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        with JournalStore(app.state.journal_db) as journal:
            engine = RuntimeEngine(config, mt5_client=client, journal=journal)
            ok, errors = engine.healthcheck()
        return {"ok": ok, "errors": list(errors)}

    @app.post("/api/actions/scan")
    def action_scan(request: ScanRequest) -> dict[str, Any]:
        try:
            mode = RuntimeMode(request.mode)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if mode is RuntimeMode.AUTO:
            raise HTTPException(status_code=400, detail="AUTO cannot be launched from the local UI")
        config = _load_config(app.state.config_dir)
        client = app.state.mt5_client_factory()
        try:
            connect_mt5_from_env(client)
        except MT5ConnectionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        with JournalStore(app.state.journal_db) as journal:
            engine = RuntimeEngine(
                config,
                mt5_client=client,
                journal=journal,
                status_file=app.state.status_file,
            )
            result = engine.scan_once(
                mode=mode,
                account_state=AccountRiskState(equity=request.equity),
                candle_count=request.candle_count,
            )
        return {
            "scanned": result.scanned,
            "errors": list(result.errors),
            "decisions": [
                {
                    "instrument": decision.signal.instrument,
                    "action": decision.final_action.value,
                    "strategy": decision.signal.strategy,
                    "score": decision.signal.setup_score,
                    "risk_verdict": decision.risk.verdict.value,
                }
                for decision in result.decisions
            ],
        }

    @app.post("/api/actions/backtest")
    def action_backtest(request: BacktestRequest) -> dict[str, Any]:
        config = _load_config(app.state.config_dir)
        client = app.state.mt5_client_factory()
        try:
            connect_mt5_from_env(client)
        except MT5ConnectionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        market = MarketDataEngine(client)
        report = run_library_backtest(
            config,
            market,
            candle_count=request.candle_count,
            lookahead_bars=request.lookahead_bars,
        )
        payload = _report_payload(report, request)
        app.state.report_file.parent.mkdir(parents=True, exist_ok=True)
        _write_json(app.state.report_file, payload)
        with JournalStore(app.state.journal_db) as journal:
            journal.log_event(
                "backtest",
                entity_id="strategy_library",
                payload={"combinations": len(payload["results"]), "skipped": len(payload["skipped"])},
            )
        return payload

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


def _load_config(config_dir: str):
    try:
        return load_app_config(config_dir)
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _report_payload(report, request: BacktestRequest) -> dict[str, Any]:
    ranked = report.ranked_by_expectancy
    return {
        "candle_count": request.candle_count,
        "lookahead_bars": request.lookahead_bars,
        "skipped": list(report.skipped),
        "results": [
            {
                "instrument": result.instrument,
                "strategy": result.strategy,
                "timeframe": result.timeframe,
                "trades": result.metrics.trades,
                "win_rate": result.metrics.win_rate,
                "expectancy": result.metrics.expectancy,
                "profit_factor": result.metrics.profit_factor,
                "max_drawdown": result.metrics.max_drawdown,
                "average_win": result.metrics.average_win,
                "average_loss": result.metrics.average_loss,
                "mfe": result.metrics.mfe,
                "mae": result.metrics.mae,
                "profitable": result.metrics.profitable,
            }
            for result in ranked
        ],
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
