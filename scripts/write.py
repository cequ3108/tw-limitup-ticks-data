#!/usr/bin/env python3
"""Write ticks/YYYY-MM-DD/{symbol}.parquet and manifest.json."""

from __future__ import annotations

import sys

import _bootstrap

_bootstrap.prepare()

from tw_limitup_ticks.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["write", *sys.argv[1:]]))
