from __future__ import annotations

from typing import Any, Mapping


def as_mapping(resp: Any) -> dict[str, Any]:
    """Normalize SDK / REST responses into a plain dict."""
    if resp is None:
        return {}
    if isinstance(resp, Mapping):
        return dict(resp)
    to_dict = getattr(resp, "to_dict", None)
    if callable(to_dict):
        mapped = to_dict()
        if isinstance(mapped, Mapping):
            return dict(mapped)
    model_dump = getattr(resp, "model_dump", None)
    if callable(model_dump):
        mapped = model_dump()
        if isinstance(mapped, Mapping):
            return dict(mapped)
    if hasattr(resp, "__dict__"):
        mapped = {key: value for key, value in vars(resp).items() if not key.startswith("_")}
        if mapped:
            return mapped
    raise TypeError(f"Unsupported market-data response type: {type(resp)!r}")


def response_rows(resp: Mapping[str, Any]) -> list[dict[str, Any]]:
    data = resp.get("data") or []
    rows: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, Mapping):
            rows.append(dict(item))
        else:
            rows.append(as_mapping(item))
    return rows
