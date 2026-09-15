from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from tw_limitup_ticks.client import MarketClient
from tw_limitup_ticks.fetch import fetch_trades
from tw_limitup_ticks.prices import as_float, prices_equal
from tw_limitup_ticks.select import select_near_limit
from tw_limitup_ticks.timeutil import micros_to_taipei, now_taipei_iso

PARQUET_COLUMNS: tuple[str, ...] = (
    "symbol",
    "name",
    "date",
    "time_us",
    "time_local",
    "price",
    "size",
    "volume",
    "bid",
    "ask",
    "serial",
    "limit_up_price",
    "is_limit_up_price",
    "market",
    "reference_price",
    "limit_down_price",
    "high_price",
    "close_price",
    "change_percent",
    "high_change_percent",
    "touched_limit_up",
    "approached_limit_up",
    "status",
)


def archive_day(
    client: MarketClient,
    *,
    out_root: str | Path = "ticks",
    gte: float = 8.0,
    markets: Sequence[str] = ("TSE", "OTC"),
    touched_only: bool = False,
    page_size: int = 500,
    max_symbols: int | None = None,
) -> dict[str, Any]:
    selection = select_near_limit(
        client,
        gte=gte,
        markets=markets,
        touched_only=touched_only,
    )
    symbols = list(selection["symbols"])
    if max_symbols is not None:
        symbols = symbols[: max(0, max_symbols)]
        selection["symbols"] = symbols
    return write_archive(
        client,
        selection,
        out_root=out_root,
        page_size=page_size,
    )


def write_archive(
    client: MarketClient | None,
    selection: dict[str, Any],
    *,
    out_root: str | Path = "ticks",
    page_size: int = 500,
    trades_by_symbol: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    date = selection.get("date")
    if not date:
        raise ValueError("Selection is missing session date")
    day_dir = Path(out_root) / str(date)
    day_dir.mkdir(parents=True, exist_ok=True)

    manifest_symbols: list[dict[str, Any]] = []
    for candidate in selection.get("symbols") or []:
        symbol = candidate["symbol"]
        if trades_by_symbol is not None and symbol in trades_by_symbol:
            trades = trades_by_symbol[symbol]
        else:
            if client is None:
                raise ValueError(f"No cached trades for {symbol} and no market client")
            trades = fetch_trades(client, symbol, page_size=page_size)
        frame = trades_to_frame(trades, candidate)
        parquet_name = f"{symbol}.parquet"
        parquet_path = day_dir / parquet_name
        frame.to_parquet(parquet_path, engine="pyarrow", index=False)
        digest, size = _sha256_and_size(parquet_path)
        limit_up_ticks = int(frame["is_limit_up_price"].fillna(False).sum()) if not frame.empty else 0
        manifest_symbols.append(
            {
                **{k: candidate.get(k) for k in (
                    "symbol",
                    "name",
                    "market",
                    "limit_up_price",
                    "reference_price",
                    "high_price",
                    "close_price",
                    "change_percent",
                    "high_change_percent",
                    "touched_limit_up",
                    "approached_limit_up",
                    "status",
                )},
                "parquet": parquet_name,
                "rows": int(len(frame)),
                "sha256": digest,
                "bytes": size,
                "limit_up_ticks": limit_up_ticks,
                "first_time_local": None if frame.empty else frame["time_local"].iloc[0],
                "last_time_local": None if frame.empty else frame["time_local"].iloc[-1],
            }
        )

    dry_run = bool(getattr(client, "dry_run", False))
    manifest = {
        "date": date,
        "generated_at": now_taipei_iso(),
        "source": "mock" if dry_run else "fubon_neo",
        "dry_run": dry_run,
        "selection": selection.get("selection"),
        "symbol_count": len(manifest_symbols),
        "symbols": manifest_symbols,
    }
    manifest_path = day_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def trades_to_frame(trades: dict[str, Any], candidate: dict[str, Any]) -> pd.DataFrame:
    limit_up = as_float(candidate.get("limit_up_price"))
    records: list[dict[str, Any]] = []
    for row in trades.get("data") or []:
        price = as_float(row.get("price"))
        time_us = row.get("time")
        records.append(
            {
                "symbol": candidate.get("symbol") or trades.get("symbol"),
                "name": candidate.get("name"),
                "date": trades.get("date") or candidate.get("date"),
                "time_us": None if time_us is None else int(time_us),
                "time_local": micros_to_taipei(time_us),
                "price": price,
                "size": row.get("size"),
                "volume": row.get("volume"),
                "bid": as_float(row.get("bid")),
                "ask": as_float(row.get("ask")),
                "serial": row.get("serial"),
                "limit_up_price": limit_up,
                "is_limit_up_price": prices_equal(price, limit_up),
                "market": candidate.get("market") or trades.get("market"),
                "reference_price": candidate.get("reference_price"),
                "limit_down_price": candidate.get("limit_down_price"),
                "high_price": candidate.get("high_price"),
                "close_price": candidate.get("close_price"),
                "change_percent": candidate.get("change_percent"),
                "high_change_percent": candidate.get("high_change_percent"),
                "touched_limit_up": candidate.get("touched_limit_up"),
                "approached_limit_up": candidate.get("approached_limit_up"),
                "status": candidate.get("status"),
            }
        )
    frame = pd.DataFrame.from_records(records, columns=list(PARQUET_COLUMNS))
    return frame


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_trades_dir(path: str | Path) -> dict[str, dict[str, Any]]:
    root = Path(path)
    loaded: dict[str, dict[str, Any]] = {}
    if not root.exists():
        return loaded
    for file in sorted(root.glob("*.json")):
        payload = load_json(file)
        symbol = str(payload.get("symbol") or file.stem)
        loaded[symbol] = payload
    return loaded


def iter_candidate_symbols(selection: dict[str, Any]) -> Iterable[str]:
    for item in selection.get("symbols") or []:
        yield str(item["symbol"])


def _sha256_and_size(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest(), path.stat().st_size
