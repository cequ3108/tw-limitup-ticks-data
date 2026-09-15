from __future__ import annotations

from typing import Any

from tw_limitup_ticks.client import DEFAULT_TRADE_PAGE_SIZE, MarketClient
from tw_limitup_ticks.normalize import response_rows

MAX_TRADE_OFFSET = 1_000_000


def fetch_trades(
    client: MarketClient,
    symbol: str,
    *,
    page_size: int = DEFAULT_TRADE_PAGE_SIZE,
) -> dict[str, Any]:
    """Download full-day `intraday.trades` by paging offset/limit."""
    rows: list[dict[str, Any]] = []
    offset = 0
    meta: dict[str, Any] = {"symbol": symbol}
    while offset <= MAX_TRADE_OFFSET:
        payload = client.intraday_trades(symbol=symbol, offset=offset, limit=page_size)
        for key in ("date", "type", "exchange", "market", "symbol"):
            if payload.get(key) is not None:
                meta[key] = payload[key]
        batch = response_rows(payload)
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    unique = _dedupe_trades(rows)
    unique.sort(key=lambda item: (int(item.get("time") or 0), int(item.get("serial") or 0)))
    meta["data"] = unique
    meta["count"] = len(unique)
    return meta


def _dedupe_trades(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    unique: list[dict[str, Any]] = []
    for row in rows:
        serial = row.get("serial")
        key = (
            serial
            if serial is not None
            else (row.get("time"), row.get("price"), row.get("size"), row.get("volume"))
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique
