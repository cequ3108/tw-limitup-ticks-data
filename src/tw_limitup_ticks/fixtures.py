"""Canned Fubon-shaped payloads for --dry-run and CI (no live login)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

FIXTURE_DATE = "2024-04-30"

# TSE 2345: high touches official limit-up.
# TSE 2303: close/high near limit (gte=8) but high < limitUpPrice.
# OTC 6488: high touches limit-up.
# TSE 1101 is intentionally absent from movers so tests can document the
# last/close % limitation (a high-touch name that closed below gte).

MOVERS: dict[str, dict[str, Any]] = {
    "TSE": {
        "date": FIXTURE_DATE,
        "time": "133500",
        "market": "TSE",
        "change": "percent",
        "data": [
            {
                "type": "EQUITY",
                "symbol": "2345",
                "name": "智邦",
                "openPrice": 357.5,
                "highPrice": 393.0,
                "lowPrice": 346.5,
                "closePrice": 393.0,
                "change": 35.5,
                "changePercent": 9.93,
                "tradeVolume": 9350,
                "tradeValue": 3331334500,
                "lastUpdated": 1714455000000000,
            },
            {
                "type": "EQUITY",
                "symbol": "2303",
                "name": "聯電",
                "openPrice": 50.0,
                "highPrice": 54.2,
                "lowPrice": 49.8,
                "closePrice": 54.0,
                "change": 4.0,
                "changePercent": 8.0,
                "tradeVolume": 12000,
                "tradeValue": 640000000,
                "lastUpdated": 1714455000000000,
            },
        ],
    },
    "OTC": {
        "date": FIXTURE_DATE,
        "time": "133500",
        "market": "OTC",
        "change": "percent",
        "data": [
            {
                "type": "EQUITY",
                "symbol": "6488",
                "name": "環球晶",
                "openPrice": 1800.0,
                "highPrice": 1980.0,
                "lowPrice": 1795.0,
                "closePrice": 1975.0,
                "change": 175.0,
                "changePercent": 9.72,
                "tradeVolume": 2100,
                "tradeValue": 4000000000,
                "lastUpdated": 1714455000000000,
            }
        ],
    },
}

TICKERS: dict[str, dict[str, Any]] = {
    "2345": {
        "date": FIXTURE_DATE,
        "type": "EQUITY",
        "exchange": "TWSE",
        "market": "TSE",
        "symbol": "2345",
        "name": "智邦",
        "referencePrice": 357.5,
        "limitUpPrice": 393.0,
        "limitDownPrice": 322.0,
        "previousClose": 357.5,
        "securityType": "01",
    },
    "2303": {
        "date": FIXTURE_DATE,
        "type": "EQUITY",
        "exchange": "TWSE",
        "market": "TSE",
        "symbol": "2303",
        "name": "聯電",
        "referencePrice": 50.0,
        "limitUpPrice": 55.0,
        "limitDownPrice": 45.0,
        "previousClose": 50.0,
        "securityType": "01",
    },
    "6488": {
        "date": FIXTURE_DATE,
        "type": "EQUITY",
        "exchange": "TPEx",
        "market": "OTC",
        "symbol": "6488",
        "name": "環球晶",
        "referencePrice": 1800.0,
        "limitUpPrice": 1980.0,
        "limitDownPrice": 1620.0,
        "previousClose": 1800.0,
        "securityType": "01",
    },
    # High touched limit-up, but last/close % is only +5 — movers(gte=8) misses it.
    "1101": {
        "date": FIXTURE_DATE,
        "type": "EQUITY",
        "exchange": "TWSE",
        "market": "TSE",
        "symbol": "1101",
        "name": "台泥",
        "referencePrice": 40.0,
        "limitUpPrice": 44.0,
        "limitDownPrice": 36.0,
        "previousClose": 40.0,
        "securityType": "01",
    },
}

# Newest-first, matching the official REST default sort.
TRADES: dict[str, dict[str, Any]] = {
    "2345": {
        "date": FIXTURE_DATE,
        "type": "EQUITY",
        "exchange": "TWSE",
        "market": "TSE",
        "symbol": "2345",
        "data": [
            {
                "bid": 392.5,
                "ask": 393.0,
                "price": 393.0,
                "size": 20,
                "volume": 9350,
                "time": 1714455000000000,
                "serial": 3003,
            },
            {
                "bid": 390.0,
                "ask": 390.5,
                "price": 390.5,
                "size": 15,
                "volume": 8000,
                "time": 1714446000000000,
                "serial": 2002,
            },
            {
                "bid": 357.0,
                "ask": 357.5,
                "price": 357.5,
                "size": 50,
                "volume": 50,
                "time": 1714438800000000,
                "serial": 1001,
            },
        ],
    },
    "2303": {
        "date": FIXTURE_DATE,
        "type": "EQUITY",
        "exchange": "TWSE",
        "market": "TSE",
        "symbol": "2303",
        "data": [
            {
                "bid": 53.9,
                "ask": 54.0,
                "price": 54.0,
                "size": 100,
                "volume": 12000,
                "time": 1714455000000000,
                "serial": 22,
            },
            {
                "bid": 54.1,
                "ask": 54.2,
                "price": 54.2,
                "size": 80,
                "volume": 4000,
                "time": 1714446000000000,
                "serial": 11,
            },
        ],
    },
    "6488": {
        "date": FIXTURE_DATE,
        "type": "EQUITY",
        "exchange": "TPEx",
        "market": "OTC",
        "symbol": "6488",
        "data": [
            {
                "bid": 1970.0,
                "ask": 1975.0,
                "price": 1975.0,
                "size": 5,
                "volume": 2100,
                "time": 1714455000000000,
                "serial": 9,
            },
            {
                "bid": 1980.0,
                "ask": 1980.0,
                "price": 1980.0,
                "size": 3,
                "volume": 300,
                "time": 1714446000000000,
                "serial": 2,
            },
        ],
    },
}


def movers_payload(market: str) -> dict[str, Any]:
    if market not in MOVERS:
        return {"date": FIXTURE_DATE, "time": "133500", "market": market, "change": "percent", "data": []}
    return deepcopy(MOVERS[market])


def ticker_payload(symbol: str) -> dict[str, Any]:
    if symbol not in TICKERS:
        raise KeyError(symbol)
    return deepcopy(TICKERS[symbol])


def trades_payload(symbol: str, *, offset: int = 0, limit: int = 500) -> dict[str, Any]:
    if symbol not in TRADES:
        raise KeyError(symbol)
    payload = deepcopy(TRADES[symbol])
    rows = payload.get("data") or []
    payload["data"] = rows[offset : offset + limit]
    return payload
