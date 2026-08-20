"""Operational scan runtime for Windows + MT5."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from zoetrading.analysis import assess_multi_timeframe, classify_market_regime
from zoetrading.config.models import AppConfig, InstrumentConfig
from zoetrading.domain import Decision, RuntimeMode, SystemStatus, TradeAction
from zoetrading.intelligence import DecisionEngine
from zoetrading.journal import JournalStore
from zoetrading.market import MT5Client, MarketDataEngine, MarketDataError
from zoetrading.operations import heartbeat_status
from zoetrading.operations.mt5_status import write_status_file
from zoetrading.risk import AccountRiskState, RiskEngine
from zoetrading.strategies import StrategyContext, StrategyEngine, default_strategies


@dataclass(frozen=True)
class RuntimeResult:
    scanned: int
    decisions: tuple[Decision, ...]
    errors: tuple[str, ...]
    status_file: Path

    @property
    def ok(self) -> bool:
        return self.scanned > 0 and not self.errors

    @property
    def display_decision(self) -> Decision | None:
        return select_display_decision(self.decisions)


def connect_mt5_from_env(client: MT5Client) -> None:
    login = os.getenv("MT5_LOGIN")
    client.connect(
        path=os.getenv("MT5_PATH") or None,
        login=int(login) if login else None,
        password=os.getenv("MT5_PASSWORD") or None,
        server=os.getenv("MT5_SERVER") or None,
    )


class RuntimeEngine:
    def __init__(
        self,
        config: AppConfig,
        *,
        mt5_client: MT5Client | None = None,
        journal: JournalStore | None = None,
        status_file: str | Path = "data/zoetrading_status.csv",
    ) -> None:
        self.config = config
        self.mt5_client = mt5_client or MT5Client()
        self.market = MarketDataEngine(self.mt5_client)
        self.journal = journal
        self.status_file = Path(status_file)
        self.strategy_engine = StrategyEngine(default_strategies())
        self.decision_engine = DecisionEngine(RiskEngine(config.risk), journal)

    def healthcheck(self) -> tuple[bool, tuple[str, ...]]:
        errors: list[str] = []
        try:
            self.mt5_client.ensure_connected()
            for instrument in self.config.instruments.instruments:
                if instrument.enabled:
                    self.mt5_client.get_symbol_info(instrument.symbol)
        except MarketDataError as exc:
            errors.append(str(exc))
        heartbeat = heartbeat_status(mt5_connected=not errors)
        if self.journal:
            self.journal.log_event(
                "healthcheck",
                entity_id="runtime",
                payload={
                    "healthy": heartbeat.healthy,
                    "mt5_connected": heartbeat.mt5_connected,
                    "errors": errors,
                },
            )
        return not errors, tuple(errors)

    def scan_once(
        self,
        *,
        mode: RuntimeMode,
        account_state: AccountRiskState,
        candle_count: int = 200,
    ) -> RuntimeResult:
        if mode is RuntimeMode.AUTO:
            raise ValueError("AUTO runtime requires the validation gate and is not enabled by scan-once")

        decisions: list[Decision] = []
        errors: list[str] = []
        config_hash = self.journal.save_config_snapshot(self.config) if self.journal else None
        for instrument in self.config.instruments.instruments:
            if not instrument.enabled:
                continue
            try:
                decision = self._scan_instrument(
                    instrument,
                    account_state=account_state,
                    candle_count=candle_count,
                )
            except Exception as exc:  # scanner must isolate symbol failures
                message = f"{instrument.symbol}: {exc}"
                errors.append(message)
                if self.journal:
                    self.journal.log_event("scan_error", entity_id=instrument.symbol, severity="ERROR", payload={"error": message})
                continue
            decisions.append(decision)
            if self.journal:
                self.journal.log_decision(decision, config_hash=config_hash)

        selected = select_display_decision(tuple(decisions))
        write_status_file(
            self.status_file,
            status=SystemStatus.RUNNING if decisions else SystemStatus.ERROR,
            mode=mode.value,
            decision=selected,
        )
        return RuntimeResult(
            scanned=len(decisions),
            decisions=tuple(decisions),
            errors=tuple(errors),
            status_file=self.status_file,
        )

    def _scan_instrument(
        self,
        instrument: InstrumentConfig,
        *,
        account_state: AccountRiskState,
        candle_count: int,
    ) -> Decision:
        result = self.market.collect_instrument(
            instrument.symbol,
            instrument.timeframes,
            candle_count=candle_count,
        )
        if result.errors:
            raise MarketDataError("; ".join(result.errors))
        candles_by_timeframe = result.candles_by_timeframe
        mtf = assess_multi_timeframe(
            instrument.symbol,
            candles_by_timeframe,
            context_timeframes=self.config.settings.market.context_timeframes,
            setup_timeframes=self.config.settings.market.setup_timeframes,
            timing_timeframes=self.config.settings.market.timing_timeframes,
        )
        setup_timeframe = _first_available(
            self.config.settings.market.setup_timeframes,
            candles_by_timeframe,
        )
        setup_candles = candles_by_timeframe[setup_timeframe]
        regime = classify_market_regime(setup_candles)
        strategy_context = StrategyContext(
            instrument=instrument.symbol,
            family=instrument.family,
            timeframe=setup_timeframe,
            candles=tuple(setup_candles),
            regime=regime,
            mtf=mtf,
        )
        strategy_result = self.strategy_engine.evaluate(strategy_context)
        return self.decision_engine.decide(strategy_result.signals, account_state)


def _first_available(
    preferred: tuple[str, ...],
    candles_by_timeframe: dict[str, object],
) -> str:
    for timeframe in preferred:
        if timeframe in candles_by_timeframe:
            return timeframe
    if candles_by_timeframe:
        return next(iter(candles_by_timeframe))
    raise ValueError("no candles available")


def select_display_decision(decisions: tuple[Decision, ...]) -> Decision | None:
    trade_decisions = [decision for decision in decisions if decision.final_action is not TradeAction.NO_TRADE]
    if trade_decisions:
        return max(trade_decisions, key=lambda decision: decision.signal.setup_score)
    if decisions:
        return max(decisions, key=lambda decision: decision.signal.setup_score)
    return None

