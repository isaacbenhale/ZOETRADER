"""Small, testable wrapper around the MetaTrader5 Python package."""

from __future__ import annotations

from datetime import UTC, datetime
from types import ModuleType
from typing import Any

from zoetrading.domain import (
    Candle,
    OrderRequest,
    OrderResult,
    OrderStatus,
    PositionState,
    PositionStatus,
    SymbolInfo,
    Tick,
    TradeAction,
)
from zoetrading.market.errors import MT5ConnectionError, SymbolUnavailableError
from zoetrading.market.timeframes import mt5_timeframe_constant


class MT5Client:
    """Encapsulates all direct calls to the MetaTrader5 package."""

    def __init__(self, mt5_module: ModuleType | Any | None = None) -> None:
        self._mt5 = mt5_module if mt5_module is not None else self._import_mt5()
        self._connected = False

    @staticmethod
    def _import_mt5() -> ModuleType:
        try:
            import MetaTrader5 as mt5  # type: ignore[import-not-found]
        except ImportError as exc:
            raise MT5ConnectionError(
                "MetaTrader5 Python package is not installed. "
                "Install it on the Windows MT5 machine before enabling market data."
            ) from exc
        return mt5

    def connect(
        self,
        *,
        path: str | None = None,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {}
        if path:
            kwargs["path"] = path
        if login is not None:
            kwargs["login"] = login
        if password:
            kwargs["password"] = password
        if server:
            kwargs["server"] = server

        if not self._mt5.initialize(**kwargs):
            raise MT5ConnectionError(f"Unable to initialize MT5: {self.last_error()}")
        self._connected = True

    def shutdown(self) -> None:
        if self._connected:
            self._mt5.shutdown()
        self._connected = False

    def last_error(self) -> object:
        last_error = getattr(self._mt5, "last_error", None)
        return last_error() if callable(last_error) else None

    def ensure_connected(self) -> None:
        terminal_info = self._mt5.terminal_info()
        if not self._connected or terminal_info is None:
            raise MT5ConnectionError("MT5 is not connected or terminal_info is unavailable.")

    def ensure_symbol(self, instrument: str) -> SymbolInfo:
        self.ensure_connected()
        raw = self._mt5.symbol_info(instrument)
        if raw is None:
            raise SymbolUnavailableError(f"Symbol unavailable in MT5: {instrument}")
        if not bool(getattr(raw, "visible", False)):
            selected = self._mt5.symbol_select(instrument, True)
            if not selected:
                raise SymbolUnavailableError(f"Symbol cannot be selected in MT5: {instrument}")
            raw = self._mt5.symbol_info(instrument)
            if raw is None:
                raise SymbolUnavailableError(f"Symbol unavailable after selection: {instrument}")
        return self._to_symbol_info(instrument, raw)

    def get_symbol_info(self, instrument: str) -> SymbolInfo:
        return self.ensure_symbol(instrument)

    def get_tick(self, instrument: str) -> Tick:
        self.ensure_symbol(instrument)
        raw = self._mt5.symbol_info_tick(instrument)
        if raw is None:
            raise SymbolUnavailableError(f"No tick available for symbol: {instrument}")
        bid = float(getattr(raw, "bid"))
        ask = float(getattr(raw, "ask"))
        return Tick(
            instrument=instrument,
            timestamp=_timestamp_to_datetime(getattr(raw, "time")),
            bid=bid,
            ask=ask,
            last=_optional_float(getattr(raw, "last", None)),
            volume=_optional_float(getattr(raw, "volume", None)),
            spread=max(0.0, ask - bid),
        )

    def get_candles(self, instrument: str, timeframe: str, count: int) -> tuple[Candle, ...]:
        if count <= 0:
            raise ValueError("count must be positive")
        self.ensure_symbol(instrument)
        mt5_timeframe = mt5_timeframe_constant(self._mt5, timeframe)
        rates = self._mt5.copy_rates_from_pos(instrument, mt5_timeframe, 0, count)
        if rates is None:
            raise SymbolUnavailableError(
                f"No OHLC data available for {instrument} {timeframe}: {self.last_error()}"
            )
        return tuple(self._to_candle(instrument, timeframe, row) for row in rates)

    def get_open_positions(self, instrument: str | None = None) -> tuple[PositionState, ...]:
        self.ensure_connected()
        kwargs = {"symbol": instrument} if instrument else {}
        raw_positions = self._mt5.positions_get(**kwargs)
        if raw_positions is None:
            return ()
        return tuple(self._to_position(row) for row in raw_positions)

    def send_order(self, order: OrderRequest) -> OrderResult:
        self.ensure_symbol(order.instrument)
        order_type = (
            getattr(self._mt5, "ORDER_TYPE_BUY", 0)
            if order.action is TradeAction.BUY
            else getattr(self._mt5, "ORDER_TYPE_SELL", 1)
        )
        request = {
            "action": getattr(self._mt5, "TRADE_ACTION_DEAL", 1),
            "symbol": order.instrument,
            "volume": order.volume,
            "type": order_type,
            "price": order.entry,
            "sl": order.stop_loss,
            "tp": order.take_profit or 0.0,
            "deviation": 20,
            "magic": 260817,
            "comment": order.comment,
            "type_time": getattr(self._mt5, "ORDER_TIME_GTC", 0),
            "type_filling": getattr(self._mt5, "ORDER_FILLING_IOC", 1),
        }
        raw = self._mt5.order_send(request)
        if raw is None:
            return OrderResult(order_id=order.order_id, status=OrderStatus.FAILED, message=str(self.last_error()))
        retcode = getattr(raw, "retcode", None)
        success_code = getattr(self._mt5, "TRADE_RETCODE_DONE", 10009)
        status = OrderStatus.ACCEPTED if retcode == success_code else OrderStatus.REJECTED
        return OrderResult(
            order_id=order.order_id,
            status=status,
            broker_order_id=str(getattr(raw, "order", "")) or None,
            message=str(getattr(raw, "comment", "")),
        )

    def modify_position_stop(self, position_id: str, symbol: str, stop_loss: float, take_profit: float | None) -> bool:
        self.ensure_connected()
        request = {
            "action": getattr(self._mt5, "TRADE_ACTION_SLTP", 6),
            "position": int(position_id),
            "symbol": symbol,
            "sl": stop_loss,
            "tp": take_profit or 0.0,
        }
        raw = self._mt5.order_send(request)
        if raw is None:
            return False
        return getattr(raw, "retcode", None) == getattr(self._mt5, "TRADE_RETCODE_DONE", 10009)

    @staticmethod
    def _to_symbol_info(instrument: str, raw: object) -> SymbolInfo:
        return SymbolInfo(
            instrument=instrument,
            visible=bool(getattr(raw, "visible")),
            trade_allowed=bool(getattr(raw, "trade_mode", 0) != 0),
            digits=int(getattr(raw, "digits")),
            point=float(getattr(raw, "point")),
            volume_min=float(getattr(raw, "volume_min")),
            volume_max=float(getattr(raw, "volume_max")),
            volume_step=float(getattr(raw, "volume_step")),
        )

    @staticmethod
    def _to_candle(instrument: str, timeframe: str, row: Any) -> Candle:
        getter = _row_getter(row)
        return Candle(
            instrument=instrument,
            timeframe=timeframe.upper(),
            timestamp=_timestamp_to_datetime(getter("time")),
            open=float(getter("open")),
            high=float(getter("high")),
            low=float(getter("low")),
            close=float(getter("close")),
            tick_volume=int(getter("tick_volume")),
            spread=int(getter("spread")),
            real_volume=int(getter("real_volume")),
        )

    def _to_position(self, row: object) -> PositionState:
        buy_type = getattr(self._mt5, "POSITION_TYPE_BUY", 0)
        action = TradeAction.BUY if getattr(row, "type") == buy_type else TradeAction.SELL
        return PositionState(
            position_id=str(getattr(row, "ticket")),
            instrument=str(getattr(row, "symbol")),
            action=action,
            volume=float(getattr(row, "volume")),
            entry=float(getattr(row, "price_open")),
            opened_at=_timestamp_to_datetime(getattr(row, "time")),
            status=PositionStatus.OPEN,
            current_sl=float(getattr(row, "sl")),
            current_tp=_optional_float(getattr(row, "tp", None)),
            unrealized_pnl=float(getattr(row, "profit", 0.0)),
        )


def _timestamp_to_datetime(value: int | float) -> datetime:
    return datetime.fromtimestamp(float(value), tz=UTC)


def _optional_float(value: object | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _row_getter(row: Any):
    if isinstance(row, dict):
        return row.__getitem__

    def get_from_object(key: str) -> object:
        try:
            return row[key]
        except (TypeError, KeyError, IndexError, ValueError):
            return getattr(row, key)

    return get_from_object
