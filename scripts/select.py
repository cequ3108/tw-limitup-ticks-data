#!/usr/bin/env python3
"""Select near-limit-up names (movers + ticker confirmation)."""

from __future__ import annotations

import sys

import _bootstrap

_bootstrap.prepare()

from tw_limitup_ticks.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["select", *sys.argv[1:]]))
