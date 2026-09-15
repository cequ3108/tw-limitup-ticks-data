from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from tw_limitup_ticks import __version__
from tw_limitup_ticks.archive import (
    archive_day,
    dump_json,
    load_json,
    load_trades_dir,
    write_archive,
)
from tw_limitup_ticks.client import MarketDataError, open_client
from tw_limitup_ticks.config import ConfigError
from tw_limitup_ticks.fetch import fetch_trades
from tw_limitup_ticks.select import DEFAULT_GTE, DEFAULT_MARKETS, parse_markets, select_near_limit


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    raw = list(argv) if argv is not None else sys.argv[1:]
    args = parser.parse_args(_normalize_argv(raw))
    try:
        if args.command == "select":
            return cmd_select(args)
        if args.command == "fetch":
            return cmd_fetch(args)
        if args.command == "write":
            return cmd_write(args)
        if args.command == "archive":
            return cmd_archive(args)
    except (ConfigError, MarketDataError) as exc:
        print(exc, file=sys.stderr)
        return 1
    parser.error("unknown command")
    return 2


def _normalize_argv(argv: Sequence[str]) -> list[str]:
    """Allow global flags before or after the subcommand (`--dry-run archive` / `archive --dry-run`)."""
    flags_bool = {"--dry-run"}
    flags_value = {"--env-file", "--sleep"}
    extracted: list[str] = []
    rest: list[str] = []
    command: str | None = None
    i = 0
    items = list(argv)
    while i < len(items):
        arg = items[i]
        if arg in flags_bool:
            extracted.append(arg)
            i += 1
            continue
        if arg in flags_value:
            extracted.append(arg)
            if i + 1 < len(items):
                extracted.append(items[i + 1])
                i += 2
            else:
                i += 1
            continue
        if arg.startswith("--env-file=") or arg.startswith("--sleep="):
            extracted.append(arg)
            i += 1
            continue
        if command is None and not arg.startswith("-"):
            command = arg
            i += 1
            continue
        rest.append(arg)
        i += 1
    normalized: list[str] = []
    if command:
        normalized.append(command)
    normalized.extend(extracted)
    normalized.extend(rest)
    return normalized


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--dry-run",
        action="store_true",
        help="Use the in-memory mock client (no live login). For CI and local smoke tests.",
    )
    common.add_argument("--env-file", default=".env", help="Path to .env with FUBON_* credentials")
    common.add_argument(
        "--sleep",
        type=float,
        default=0.2,
        help="Delay in seconds before each live REST call (rate-limit padding)",
    )

    parser = argparse.ArgumentParser(
        prog="tw-limitup-ticks",
        description=(
            "Select Taiwan stocks that approached/touched limit-up via Fubon Neo, "
            "download full-day intraday.trades, and write Parquet + manifest."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    select_p = sub.add_parser(
        "select",
        parents=[common],
        help="snapshot.movers + intraday.ticker confirmation",
    )
    _add_selection_flags(select_p)
    select_p.add_argument("--output", "-o", help="Write candidates JSON (default: stdout)")

    fetch_p = sub.add_parser("fetch", parents=[common], help="Download full-day intraday.trades")
    fetch_p.add_argument("--symbol", help="Single symbol")
    fetch_p.add_argument("--candidates", help="Candidates JSON from the select command")
    fetch_p.add_argument("--output-dir", "-o", help="Directory for {symbol}.json trade dumps")
    fetch_p.add_argument("--page-size", type=int, default=500)

    write_p = sub.add_parser("write", parents=[common], help="Write Parquet files + manifest.json")
    write_p.add_argument("--candidates", required=True, help="Candidates JSON from select")
    write_p.add_argument("--trades-dir", required=True, help="Directory of {symbol}.json from fetch")
    write_p.add_argument("--out", default="ticks", help="Archive root (ticks/YYYY-MM-DD/)")

    archive_p = sub.add_parser("archive", parents=[common], help="select + fetch + write in one step")
    _add_selection_flags(archive_p)
    archive_p.add_argument("--out", default="ticks", help="Archive root (ticks/YYYY-MM-DD/)")
    archive_p.add_argument("--page-size", type=int, default=500)
    archive_p.add_argument("--max-symbols", type=int, help="Cap symbols (debug)")
    return parser


def _add_selection_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--gte", type=float, default=DEFAULT_GTE, help="movers changePercent >= this (default 8)")
    parser.add_argument(
        "--markets",
        default=",".join(DEFAULT_MARKETS),
        help="Comma-separated markets (default TSE,OTC)",
    )
    parser.add_argument(
        "--touched-only",
        action="store_true",
        help="Keep only names whose movers highPrice reached ticker.limitUpPrice",
    )


def cmd_select(args: argparse.Namespace) -> int:
    client = open_client(dry_run=args.dry_run, env_file=args.env_file, sleep_s=args.sleep)
    try:
        payload = select_near_limit(
            client,
            gte=args.gte,
            markets=parse_markets(args.markets),
            touched_only=args.touched_only,
        )
    finally:
        client.close()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        dump_json(args.output, payload)
    else:
        print(text)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    symbols = _symbols_from_args(args)
    if not symbols:
        raise SystemExit("Provide --symbol or --candidates")
    client = open_client(dry_run=args.dry_run, env_file=args.env_file, sleep_s=args.sleep)
    try:
        dumps = [fetch_trades(client, symbol, page_size=args.page_size) for symbol in symbols]
    finally:
        client.close()
    if args.output_dir:
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        for payload in dumps:
            dump_json(out / f"{payload['symbol']}.json", payload)
    else:
        print(json.dumps(dumps if len(dumps) > 1 else dumps[0], ensure_ascii=False, indent=2))
    return 0


def cmd_write(args: argparse.Namespace) -> int:
    selection = load_json(args.candidates)
    trades = load_trades_dir(args.trades_dir)
    missing = [item["symbol"] for item in selection.get("symbols") or [] if item["symbol"] not in trades]
    if missing:
        raise SystemExit("Missing trade dumps for: " + ", ".join(missing))
    client = None
    if args.dry_run:
        client = open_client(dry_run=True)
    try:
        manifest = write_archive(client, selection, out_root=args.out, trades_by_symbol=trades)
    finally:
        if client is not None:
            client.close()
    print(json.dumps({"date": manifest["date"], "symbol_count": manifest["symbol_count"], "out": args.out}, ensure_ascii=False))
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    client = open_client(dry_run=args.dry_run, env_file=args.env_file, sleep_s=args.sleep)
    try:
        manifest = archive_day(
            client,
            out_root=args.out,
            gte=args.gte,
            markets=parse_markets(args.markets),
            touched_only=args.touched_only,
            page_size=args.page_size,
            max_symbols=args.max_symbols,
        )
    finally:
        client.close()
    print(
        json.dumps(
            {
                "date": manifest["date"],
                "symbol_count": manifest["symbol_count"],
                "out": str(Path(args.out) / str(manifest["date"])),
                "dry_run": manifest["dry_run"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _symbols_from_args(args: argparse.Namespace) -> list[str]:
    symbols: list[str] = []
    if args.symbol:
        symbols.append(str(args.symbol).strip())
    if args.candidates:
        selection = load_json(args.candidates)
        symbols.extend(str(item["symbol"]) for item in selection.get("symbols") or [])
    # preserve order, drop dupes
    seen: set[str] = set()
    unique: list[str] = []
    for symbol in symbols:
        if symbol and symbol not in seen:
            seen.add(symbol)
            unique.append(symbol)
    return unique


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
