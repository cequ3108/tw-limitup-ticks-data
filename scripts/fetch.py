#!/usr/bin/env python3
"""Download full-day intraday.trades for one symbol or a candidates JSON."""

from __future__ import annotations

import sys

import _bootstrap

_bootstrap.prepare()

from tw_limitup_ticks.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["fetch", *sys.argv[1:]]))
