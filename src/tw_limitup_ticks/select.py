from __future__ import annotations

from typing import Any, Iterable, Sequence

from tw_limitup_ticks.client import MarketClient
from tw_limitup_ticks.normalize import response_rows
from tw_limitup_ticks.prices import as_float, at_or_above, percent_change

DEFAULT_GTE = 8.0
DEFAULT_MARKETS: tuple[str, ...] = ("TSE", "OTC")
DEFAULT_TYPE = "COMMONSTOCK"

MOVERS_LIMITATION = (
    "snapshot.movers ranks by last/close change percent, not the session high. "
    "A name that touched limit-up then pulled back below --gte will not appear. "
    "Optional workaround: widen --gte (for example 6 or 5) to catch more pullbacks; "
    "this still cannot list names whose close change percent is negative or unlisted."
)


def select_near_limit(
    client: MarketClient,
    *,
    gte: float = DEFAULT_GTE,
    markets: Sequence[str] = DEFAULT_MARKETS,
    security_type: str = DEFAULT_TYPE,
    touched_only: bool = False,
) -> dict[str, Any]:
    """Select TSE+OTC common stocks that approached or touched limit-up."""
    movers: list[dict[str, Any]] = []
    session_date: str | None = None
    for market in markets:
        payload = client.snapshot_movers(
            market=market,
            direction="up",
            change="percent",
            gte=gte,
            type=security_type,
        )
        session_date = payload.get("date") or session_date
        for row in response_rows(payload):
            item = dict(row)
            item["market"] = item.get("market") or market
            movers.append(item)

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in movers:
        symbol = str(row.get("symbol") or "").strip()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        ticker = client.intraday_ticker(symbol=symbol)
        candidate = confirm_candidate(row, ticker, gte=gte, date=session_date)
        if touched_only and not candidate["touched_limit_up"]:
            continue
        selected.append(candidate)

    selected.sort(key=lambda item: (-float(item.get("high_change_percent") or 0), item["symbol"]))
    return {
        "date": session_date,
        "selection": {
            "markets": list(markets),
            "direction": "up",
            "change": "percent",
            "gte": gte,
            "type": security_type,
            "touched_only": touched_only,
            "movers_limitation": MOVERS_LIMITATION,
        },
        "symbols": selected,
    }


def confirm_candidate(
    mover: dict[str, Any],
    ticker: dict[str, Any],
    *,
    gte: float,
    date: str | None,
) -> dict[str, Any]:
    """Confirm movers highPrice against official limitUpPrice / referencePrice."""
    high = as_float(mover.get("highPrice"))
    close = as_float(mover.get("closePrice"))
    reference = as_float(ticker.get("referencePrice"))
    limit_up = as_float(ticker.get("limitUpPrice"))
    limit_down = as_float(ticker.get("limitDownPrice"))
    close_change = as_float(mover.get("changePercent"))
    high_change = percent_change(high, reference)
    touched = at_or_above(high, limit_up)
    approached = bool(high_change is not None and high_change >= gte)
    if touched:
        status = "touched"
    elif approached:
        status = "approached"
    else:
        status = "unconfirmed"

    return {
        "symbol": str(mover.get("symbol") or ticker.get("symbol")),
        "name": mover.get("name") or ticker.get("name"),
        "date": ticker.get("date") or date or mover.get("date"),
        "market": mover.get("market") or ticker.get("market"),
        "exchange": ticker.get("exchange"),
        "open_price": as_float(mover.get("openPrice")),
        "high_price": high,
        "low_price": as_float(mover.get("lowPrice")),
        "close_price": close,
        "change": as_float(mover.get("change")),
        "change_percent": close_change,
        "trade_volume": as_float(mover.get("tradeVolume")),
        "trade_value": as_float(mover.get("tradeValue")),
        "reference_price": reference,
        "limit_up_price": limit_up,
        "limit_down_price": limit_down,
        "high_change_percent": None if high_change is None else round(high_change, 4),
        "touched_limit_up": touched,
        "approached_limit_up": approached or touched,
        "status": status,
        "security_type": ticker.get("securityType"),
    }


def parse_markets(value: str | Iterable[str]) -> tuple[str, ...]:
    if isinstance(value, str):
        parts = [item.strip().upper() for item in value.split(",")]
        return tuple(item for item in parts if item)
    return tuple(str(item).strip().upper() for item in value if str(item).strip())
