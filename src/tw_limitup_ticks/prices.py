from __future__ import annotations

from typing import Any

PRICE_EPS = 1e-4


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def prices_equal(left: Any, right: Any, eps: float = PRICE_EPS) -> bool:
    a = as_float(left)
    b = as_float(right)
    if a is None or b is None:
        return False
    return abs(a - b) <= eps


def at_or_above(left: Any, right: Any, eps: float = PRICE_EPS) -> bool:
    a = as_float(left)
    b = as_float(right)
    if a is None or b is None:
        return False
    return a + eps >= b


def percent_change(price: Any, reference: Any) -> float | None:
    p = as_float(price)
    ref = as_float(reference)
    if p is None or ref is None or ref == 0:
        return None
    return (p - ref) / ref * 100.0
