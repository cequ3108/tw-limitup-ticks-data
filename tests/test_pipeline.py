from __future__ import annotations

import json
from pathlib import Path

from tw_limitup_ticks.archive import PARQUET_COLUMNS, archive_day, write_archive
from tw_limitup_ticks.client import MockMarketClient
from tw_limitup_ticks.fetch import fetch_trades
from tw_limitup_ticks.prices import prices_equal
from tw_limitup_ticks.select import MOVERS_LIMITATION, select_near_limit
from tw_limitup_ticks.timeutil import micros_to_taipei


def test_select_tse_and_otc_common_stocks_with_confirmation():
    result = select_near_limit(MockMarketClient(), gte=8)
    symbols = [item["symbol"] for item in result["symbols"]]
    assert result["date"] == "2024-04-30"
    assert symbols == ["6488", "2345", "2303"]
    by_symbol = {item["symbol"]: item for item in result["symbols"]}
    assert by_symbol["2345"]["touched_limit_up"] is True
    assert by_symbol["2345"]["status"] == "touched"
    assert by_symbol["2303"]["touched_limit_up"] is False
    assert by_symbol["2303"]["approached_limit_up"] is True
    assert by_symbol["2303"]["status"] == "approached"
    assert by_symbol["2303"]["limit_up_price"] == 55.0
    assert by_symbol["2303"]["high_price"] == 54.2
    assert result["selection"]["type"] == "COMMONSTOCK"
    assert result["selection"]["markets"] == ["TSE", "OTC"]
    assert "last/close" in result["selection"]["movers_limitation"]
    assert "last/close" in MOVERS_LIMITATION


def test_touched_only_filters_approached_names():
    result = select_near_limit(MockMarketClient(), gte=8, touched_only=True)
    assert [item["symbol"] for item in result["symbols"]] == ["6488", "2345"]


def test_gte_can_be_widened_but_close_pullback_still_missing():
    """movers limitation: high-touch 1101 closed +5% so gte=8 and gte=5 both miss it."""
    tight = {item["symbol"] for item in select_near_limit(MockMarketClient(), gte=8)["symbols"]}
    wide = {item["symbol"] for item in select_near_limit(MockMarketClient(), gte=5)["symbols"]}
    assert "1101" not in tight
    assert "1101" not in wide


def test_fetch_paginates_and_sorts_ascending():
    payload = fetch_trades(MockMarketClient(), "2345", page_size=2)
    assert payload["count"] == 3
    serials = [row["serial"] for row in payload["data"]]
    assert serials == [1001, 2002, 3003]
    times = [row["time"] for row in payload["data"]]
    assert times == sorted(times)


def test_archive_writes_parquet_schema_and_manifest(tmp_path: Path):
    manifest = archive_day(MockMarketClient(), out_root=tmp_path, gte=8)
    day = tmp_path / "2024-04-30"
    assert (day / "manifest.json").is_file()
    assert manifest["dry_run"] is True
    assert manifest["source"] == "mock"
    assert manifest["symbol_count"] == 3

    import pandas as pd

    frame = pd.read_parquet(day / "2345.parquet")
    assert list(frame.columns) == list(PARQUET_COLUMNS)
    assert (frame["symbol"] == "2345").all()
    assert frame["time_local"].tolist() == [micros_to_taipei(t) for t in frame["time_us"]]
    assert bool(frame["is_limit_up_price"].iloc[-1])
    assert prices_equal(frame["price"].iloc[-1], frame["limit_up_price"].iloc[-1])
    assert "+08:00" in frame["time_local"].iloc[0]

    saved = json.loads((day / "manifest.json").read_text(encoding="utf-8"))
    entry = next(item for item in saved["symbols"] if item["symbol"] == "2345")
    assert entry["rows"] == 3
    assert entry["limit_up_ticks"] >= 1
    assert len(entry["sha256"]) == 64


def test_write_from_cached_trades(tmp_path: Path):
    client = MockMarketClient()
    selection = select_near_limit(client, gte=8, touched_only=True)
    trades = {item["symbol"]: fetch_trades(client, item["symbol"]) for item in selection["symbols"]}
    manifest = write_archive(client, selection, out_root=tmp_path, trades_by_symbol=trades)
    assert (tmp_path / "2024-04-30" / "6488.parquet").is_file()
    assert manifest["symbol_count"] == 2
