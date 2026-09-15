"""Make `python scripts/*.py` safe to run from the repo root."""

from __future__ import annotations

import sys
from pathlib import Path


def prepare() -> None:
    """Keep `src/` importable without putting `scripts/` on sys.path.

    `python scripts/select.py` would otherwise shadow the stdlib `select`
    module, which pandas/subprocess import during CLI startup.
    """
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parent
    script_dir_str = str(script_dir)
    while script_dir_str in sys.path:
        sys.path.remove(script_dir_str)
    src = str(root / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
