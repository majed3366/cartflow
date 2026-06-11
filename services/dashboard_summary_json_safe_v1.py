# -*- coding: utf-8 -*-
"""
Dashboard summary JSON safety — read-only response shaping for GET /api/dashboard/summary.

Ensures UTF8JSONResponse (allow_nan=False) can encode the payload without altering
truth semantics: non-finite floats are invalid metric values and are coerced to 0.0.
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def finite_dashboard_float(value: Any, default: float = 0.0) -> float:
    """Return a JSON-safe finite float for dashboard metric fields."""
    try:
        out = float(value if value is not None else default)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def _json_safe_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else 0.0
    if isinstance(value, Decimal):
        try:
            f = float(value)
        except (TypeError, ValueError, ArithmeticError):
            return 0.0
        return f if math.isfinite(f) else 0.0
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def sanitize_dashboard_summary_payload(payload: Any) -> Any:
    """Recursively coerce dashboard summary payload to UTF-8 JSON-safe primitives."""
    value = _json_safe_scalar(payload)
    if value is not payload:
        return value
    if isinstance(payload, dict):
        return {
            str(k): sanitize_dashboard_summary_payload(v) for k, v in payload.items()
        }
    if isinstance(payload, (list, tuple)):
        return [sanitize_dashboard_summary_payload(v) for v in payload]
    if isinstance(payload, (bytes, bytearray)):
        return payload.decode("utf-8", errors="replace")
    return str(payload)


def preflight_utf8_json_payload(payload: Any) -> None:
    """Raise ValueError when payload cannot be encoded with allow_nan=False."""
    json.dumps(payload, ensure_ascii=False, allow_nan=False)


__all__ = [
    "finite_dashboard_float",
    "preflight_utf8_json_payload",
    "sanitize_dashboard_summary_payload",
]
