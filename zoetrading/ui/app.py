"""Local-only web UI backend: launch operations and read the journal.

Constraints (see PRD.md "Interface web locale" and its MANUAL-approval
amendment): this API never bypasses the Risk Engine and can never activate
AUTO. It can trigger the same CLI operations (bootstrap/healthcheck/scan/
backtest), and -- at the user's explicit request -- can also drive MANUAL
approval (APPROVE/REJECT/PAUSE/KILL/RESUME). The approval buttons do not
add a new execution path: they write to the same command file the MT5 EA
writes to, read by the same ManualApprovalLoop, with the same decision_id
check. The MT5 panel keeps working in parallel; neither surface owns it.
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
from zoetrading.execution import ExecutionEngine
from zoetrading.journal import JournalStore
from zoetrading.journal.serialization import to_jsonable
from zoetrading.main import build_state, render_state
from zoetrading.market import MT5Client, MT5ConnectionError, MarketDataEngine
from zoetrading.operations import write_command_file
from zoetrading.risk import AccountRiskState
from zoetrading.runtime import ManualApprovalLoop, RuntimeEngine, connect_mt5_from_env
from zoetrading.ui.approval_runner import ApprovalRunner

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


class ApprovalStartRequest(BaseModel):
    equity: float
    candle_count: int = 200


def create_app(
    *,
    config_dir: str = "config",
    journal_db: str = "data/trading.db",
    status_file: str = "data/zoetrading_status.csv",
    command_file: str = "data/zoetrading_command.csv",
    report_file: str = "data/backtest_report.json",
    mt5_client_factory: Callable[[], MT5Client] = MT5Client,
    approval_timeout_seconds: float = 120.0,
    approval_poll_interval_seconds: float = 1.0,
) -> FastAPI:
    app = FastAPI(title="zoeTrading local UI", docs_url="/api/docs", redoc_url=None)
    app.state.config_dir = config_dir
    app.state.journal_db = journal_db
    app.state.mt5_client_factory = mt5_client_factory
    app.state.status_file = Path(status_file)
    app.state.command_file = str(command_file)
    app.state.report_file = Path(report_file)
    app.state.approval_timeout_seconds = approval_timeout_seconds
    app.state.approval_poll_interval_seconds = approval_poll_interval_seconds
    app.state.approval_runner: ApprovalRunner | None = None

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

    @app.post("/api/approval/start")
    def approval_start(request: ApprovalStartRequest) -> dict[str, Any]:
        config = _load_config(app.state.config_dir)

        # Fail fast with a clear HTTP error before spawning the background
        # thread, which cannot surface a request-shaped error itself.
        preflight_client = app.state.mt5_client_factory()
        try:
            connect_mt5_from_env(preflight_client)
        except MT5ConnectionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        finally:
            preflight_client.shutdown()

        if app.state.approval_runner is None:
            app.state.approval_runner = ApprovalRunner(
                _build_manual_loop(app),
                refresh_interval_seconds=config.settings.market.refresh_interval_seconds,
            )
        started = app.state.approval_runner.start(equity=request.equity, candle_count=request.candle_count)
        if not started:
            raise HTTPException(status_code=409, detail="approval loop is already running")
        return _approval_status_payload(app.state.approval_runner)

    @app.post("/api/approval/stop")
    def approval_stop() -> dict[str, Any]:
        if app.state.approval_runner:
            app.state.approval_runner.stop()
        return {"stopped": True}

    @app.get("/api/approval/status")
    def approval_status() -> dict[str, Any]:
        if app.state.approval_runner is None:
            return {
                "running": False,
                "kill_switch": False,
                "pending_decision": None,
                "last_outcome": None,
                "start_error": None,
            }
        return _approval_status_payload(app.state.approval_runner)

    @app.post("/api/approval/approve")
    def approval_approve() -> dict[str, Any]:
        return _send_approval_command(app, "APPROVE", require_pending=True)

    @app.post("/api/approval/reject")
    def approval_reject() -> dict[str, Any]:
        return _send_approval_command(app, "REJECT", require_pending=True)

    @app.post("/api/approval/pause")
    def approval_pause() -> dict[str, Any]:
        return _send_approval_command(app, "PAUSE", require_pending=False)

    @app.post("/api/approval/kill")
    def approval_kill() -> dict[str, Any]:
        return _send_approval_command(app, "KILL_SWITCH", require_pending=False)

    @app.post("/api/approval/resume")
    def approval_resume() -> dict[str, Any]:
        return _send_approval_command(app, "RESUME", require_pending=False)

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


def _build_manual_loop(app: FastAPI) -> Callable[[], ManualApprovalLoop]:
    def build() -> ManualApprovalLoop:
        config = load_app_config(app.state.config_dir)
        client = app.state.mt5_client_factory()
        connect_mt5_from_env(client)
        journal = JournalStore(app.state.journal_db)
        runtime_engine = RuntimeEngine(config, mt5_client=client, journal=journal, status_file=app.state.status_file)
        execution_engine = ExecutionEngine(client, config.settings.execution, journal=journal)
        return ManualApprovalLoop(
            runtime_engine,
            execution_engine,
            journal=journal,
            command_file=app.state.command_file,
            approval_timeout_seconds=app.state.approval_timeout_seconds,
            poll_interval_seconds=app.state.approval_poll_interval_seconds,
        )

    return build


def _approval_status_payload(runner: ApprovalRunner) -> dict[str, Any]:
    status = runner.status()
    return {
        "running": status.running,
        "kill_switch": status.kill_switch,
        "pending_decision": to_jsonable(status.pending_decision) if status.pending_decision else None,
        "last_outcome": status.last_outcome,
        "start_error": status.start_error,
    }


def _send_approval_command(app: FastAPI, command: str, *, require_pending: bool) -> dict[str, Any]:
    runner = app.state.approval_runner
    pending = runner.loop.pending_decision if runner and runner.loop else None
    if require_pending and pending is None:
        raise HTTPException(status_code=409, detail="no pending decision to respond to")
    write_command_file(app.state.command_file, command=command, decision_id=pending.decision_id if pending else None)
    return {"sent": command}


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
