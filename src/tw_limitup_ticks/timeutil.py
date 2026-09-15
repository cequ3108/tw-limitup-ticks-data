from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TAIPEI = ZoneInfo("Asia/Taipei")


def micros_to_taipei(time_us: int | float | None) -> str | None:
    """Convert Fubon/Fugle microsecond epoch timestamps to ISO-8601 Asia/Taipei."""
    if time_us is None:
        return None
    value = int(time_us)
    seconds, micros = divmod(value, 1_000_000)
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc).astimezone(TAIPEI)
    dt = dt.replace(microsecond=micros)
    return dt.isoformat()


def now_taipei_iso() -> str:
    return datetime.now(tz=TAIPEI).isoformat(timespec="seconds")
