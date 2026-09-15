#!/usr/bin/env python3
"""Daily pipeline: select + fetch + write Parquet/manifest."""

from __future__ import annotations

import sys

import _bootstrap

_bootstrap.prepare()

from tw_limitup_ticks.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["archive", *sys.argv[1:]]))
