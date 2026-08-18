"""Market data orchestration and candle freshness checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from zoetrading.domain import Candle, MarketSnapshot, PositionState, SymbolInfo, Tick
from zoetrading.market.errors import MarketDataError, StaleMarketDataError
from zoetrading.market.mt5_client import MT5Client
from zoetrading.market.timeframes import TIMEFRAME_SECONDS, normalize_timeframe


@dataclass
class CandleCache:
    candles: dict[tuple[str, str], tuple[Candle, ...]] = field(default_factory=dict)

    def get(self, instrument: str, timeframe: str) -> tuple[Candle, ...] | None:
        return self.candles.get((instrument, normalize_timeframe(timeframe)))

    def put(self, instrument: str, timeframe: str, candles: tuple[Candle, ...]) -> None:
        self.candles[(instrument, normalize_timeframe(timeframe))] = candles

    def latest(self, instrument: str, timeframe: str) -> Candle | None:
        candles = self.get(instrument, timeframe)
        if not candles:
            return None
        return candles[-1]


@dataclass(frozen=True)
class InstrumentScanResult:
    instrument: str
    tick: Tick | None
    symbol_info: SymbolInfo | None
    candles_by_timeframe: dict[str, tuple[Candle, ...]]
    positions: tuple[PositionState, ...]
    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors


class MarketDataEngine:
    """Collects market data without letting one symbol failure stop the scanner."""

    def __init__(self, client: MT5Client, cache: CandleCache | None = None) -> None:
        self.client = client
        self.cache = cache or CandleCache()

    def collect_instrument(
        self,
        instrument: str,
        timeframes: tuple[str, ...],
        *,
        candle_count: int = 200,
    ) -> InstrumentScanResult:
        errors: list[str] = []
        tick: Tick | None = None
        symbol_info: SymbolInfo | None = None
        candles_by_timeframe: dict[str, tuple[Candle, ...]] = {}
        positions: tuple[PositionState, ...] = ()

        try:
            symbol_info = self.client.get_symbol_info(instrument)
            tick = self.client.get_tick(instrument)
            positions = self.client.get_open_positions(instrument)
        except MarketDataError as exc:
            errors.append(str(exc))
            return InstrumentScanResult(
                instrument=instrument,
                tick=tick,
                symbol_info=symbol_info,
                candles_by_timeframe=candles_by_timeframe,
                positions=positions,
                errors=tuple(errors),
            )

        for timeframe in timeframes:
            normalized = normalize_timeframe(timeframe)
            try:
                candles = self.client.get_candles(instrument, normalized, candle_count)
            except MarketDataError as exc:
                cached = self.cache.get(instrument, normalized)
                if cached:
                    candles_by_timeframe[normalized] = cached
                errors.append(f"{instrument} {normalized}: {exc}")
                continue
            self.cache.put(instrument, normalized, candles)
            candles_by_timeframe[normalized] = candles

        return InstrumentScanResult(
            instrument=instrument,
            tick=tick,
            symbol_info=symbol_info,
            candles_by_timeframe=candles_by_timeframe,
            positions=positions,
            errors=tuple(errors),
        )

    def build_snapshot(
        self,
        instrument: str,
        timeframe: str,
        *,
        max_age_seconds: int | None = None,
        now: datetime | None = None,
    ) -> MarketSnapshot:
        normalized = normalize_timeframe(timeframe)
        tick = self.client.get_tick(instrument)
        latest = self.cache.latest(instrument, normalized)
        if latest is None:
            candles = self.client.get_candles(instrument, normalized, 1)
            self.cache.put(instrument, normalized, candles)
            latest = candles[-1]

        timestamp = latest.timestamp
        freshness_limit = max_age_seconds or TIMEFRAME_SECONDS[normalized] * 2
        is_fresh = is_fresh_timestamp(timestamp, freshness_limit, now=now)
        snapshot = MarketSnapshot(
            instrument=instrument,
            timeframe=normalized,
            timestamp=timestamp,
            bid=tick.bid,
            ask=tick.ask,
            spread=tick.spread,
            is_fresh=is_fresh,
            ohlc=(latest.open, latest.high, latest.low, latest.close),
        )
        validate_fresh_snapshot(snapshot)
        return snapshot


def is_fresh_timestamp(
    timestamp: datetime,
    max_age_seconds: int,
    *,
    now: datetime | None = None,
) -> bool:
    reference = now or datetime.now(UTC)
    return (reference - timestamp).total_seconds() <= max_age_seconds


def validate_fresh_snapshot(snapshot: MarketSnapshot) -> None:
    if not snapshot.is_fresh:
        raise StaleMarketDataError(
            f"Stale market data for {snapshot.instrument} {snapshot.timeframe} at "
            f"{snapshot.timestamp.isoformat()}"
        )

