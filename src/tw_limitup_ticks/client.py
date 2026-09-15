from __future__ import annotations

import os
import time
from typing import Any, Protocol

from tw_limitup_ticks.config import FubonCredentials
from tw_limitup_ticks.fixtures import movers_payload, ticker_payload, trades_payload
from tw_limitup_ticks.normalize import as_mapping

DEFAULT_TRADE_PAGE_SIZE = 500


class MarketDataError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class MarketClient(Protocol):
    dry_run: bool

    def snapshot_movers(
        self,
        *,
        market: str,
        direction: str,
        change: str,
        gte: float,
        type: str,
    ) -> dict[str, Any]: ...

    def intraday_ticker(self, *, symbol: str) -> dict[str, Any]: ...

    def intraday_trades(
        self,
        *,
        symbol: str,
        offset: int = 0,
        limit: int = DEFAULT_TRADE_PAGE_SIZE,
    ) -> dict[str, Any]: ...

    def close(self) -> None: ...


class MockMarketClient:
    """In-memory client used by --dry-run / CI. Never logs in."""

    dry_run = True

    def snapshot_movers(
        self,
        *,
        market: str,
        direction: str,
        change: str,
        gte: float,
        type: str,
    ) -> dict[str, Any]:
        if direction != "up" or change != "percent":
            raise MarketDataError("Mock client only implements direction=up change=percent")
        payload = movers_payload(market)
        payload["data"] = [
            row
            for row in payload.get("data") or []
            if float(row.get("changePercent") or 0) >= float(gte)
        ]
        payload["type"] = type
        return payload

    def intraday_ticker(self, *, symbol: str) -> dict[str, Any]:
        try:
            return ticker_payload(symbol)
        except KeyError as exc:
            raise MarketDataError(f"Unknown mock ticker: {symbol}") from exc

    def intraday_trades(
        self,
        *,
        symbol: str,
        offset: int = 0,
        limit: int = DEFAULT_TRADE_PAGE_SIZE,
    ) -> dict[str, Any]:
        try:
            return trades_payload(symbol, offset=offset, limit=limit)
        except KeyError as exc:
            raise MarketDataError(f"Unknown mock trades: {symbol}") from exc

    def close(self) -> None:
        return None


class FubonMarketClient:
    """Thin wrapper around the official fubon_neo wheel (not on PyPI)."""

    dry_run = False

    def __init__(
        self,
        credentials: FubonCredentials,
        *,
        sleep_s: float = 0.2,
        retries: int = 5,
    ) -> None:
        self._credentials = credentials
        self._sleep_s = sleep_s
        self._retries = retries
        self._sdk: Any = None
        self._stock: Any = None

    def connect(self) -> None:
        try:
            from fubon_neo.sdk import FubonSDK
        except ImportError as exc:
            raise MarketDataError(
                "fubon_neo is not installed. It is the official Fubon Neo SDK wheel, "
                "not a PyPI package. Download it from "
                "https://www.fbs.com.tw/TradeAPI/docs/sdk/sdk-download "
                "and `pip install` the matching .whl. Use --dry-run for CI."
            ) from exc

        sdk = FubonSDK()
        accounts = sdk.login(
            self._credentials.national_id,
            self._credentials.password,
            self._credentials.cert_path,
            self._credentials.cert_password,
        )
        if getattr(accounts, "is_success", True) is False:
            message = getattr(accounts, "message", None) or "Fubon login failed"
            raise MarketDataError(str(message))
        sdk.init_realtime()
        self._sdk = sdk
        self._stock = sdk.marketdata.rest_client.stock

    def snapshot_movers(
        self,
        *,
        market: str,
        direction: str,
        change: str,
        gte: float,
        type: str,
    ) -> dict[str, Any]:
        return self._invoke(
            self._stock.snapshot.movers,
            market=market,
            direction=direction,
            change=change,
            gte=gte,
            type=type,
        )

    def intraday_ticker(self, *, symbol: str) -> dict[str, Any]:
        return self._invoke(self._stock.intraday.ticker, symbol=symbol)

    def intraday_trades(
        self,
        *,
        symbol: str,
        offset: int = 0,
        limit: int = DEFAULT_TRADE_PAGE_SIZE,
    ) -> dict[str, Any]:
        return self._invoke(
            self._stock.intraday.trades,
            symbol=symbol,
            offset=offset,
            limit=limit,
        )

    def close(self) -> None:
        sdk = self._sdk
        self._sdk = None
        self._stock = None
        if sdk is None:
            return
        logout = getattr(sdk, "logout", None)
        if callable(logout):
            try:
                logout()
            except Exception:
                return

    def _invoke(self, fn: Any, **kwargs: Any) -> dict[str, Any]:
        if self._stock is None:
            raise MarketDataError("Fubon client is not connected; call connect() first.")
        last_error: Exception | None = None
        attempts = max(1, self._retries)
        for attempt in range(attempts):
            try:
                if self._sleep_s and attempt == 0:
                    time.sleep(self._sleep_s)
                return as_mapping(fn(**kwargs))
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                last_error = exc
                if status == 429 and attempt + 1 < attempts:
                    time.sleep(2**attempt)
                    continue
                raise MarketDataError(str(exc), status_code=status) from exc
        raise MarketDataError(str(last_error)) from last_error


def open_client(*, dry_run: bool, env_file: str | None = ".env", sleep_s: float = 0.2) -> MarketClient:
    env_flag = os.environ.get("TW_LIMITUP_DRY_RUN", "").strip().lower() in {"1", "true", "yes"}
    if dry_run or env_flag:
        return MockMarketClient()
    from tw_limitup_ticks.config import FubonCredentials

    client = FubonMarketClient(FubonCredentials.from_env(env_file), sleep_s=sleep_s)
    client.connect()
    return client
