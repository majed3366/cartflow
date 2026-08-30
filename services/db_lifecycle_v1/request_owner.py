# -*- coding: utf-8 -*-
"""Request owner context for DB checkout attribution (INV-DB-11)."""
from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from typing import Any, Optional

_owner: ContextVar[Optional[dict[str, Any]]] = ContextVar(
    "db_lifecycle_request_owner", default=None
)

LONG_HOLD_WARN_MS = 1000.0


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def request_owner_begin(request: Any) -> dict[str, Any]:
    path = getattr(getattr(request, "url", None), "path", "") or ""
    method = getattr(request, "method", "") or ""
    hdrs = getattr(request, "headers", None)
    incoming = ""
    if hdrs is not None:
        try:
            incoming = str(hdrs.get("x-request-id") or hdrs.get("x-cartflow-request-id") or "")
        except Exception:  # noqa: BLE001
            incoming = ""
    rid = (incoming.strip() or new_request_id())[:32]
    rec: dict[str, Any] = {
        "request_id": rid,
        "route": path[:256],
        "method": method[:16],
        "merchant": "",
        "admission": "n/a",
        "t0": time.perf_counter(),
        "checkout_count": 0,
        "checkin_count": 0,
        "last_checkout_ts": None,
        "last_checkin_ts": None,
        "last_hold_ms": 0.0,
        "outcome": "",
    }
    _owner.set(rec)
    return rec


def bind_merchant_safe(store_slug: str) -> None:
    rec = _owner.get()
    if rec is None:
        return
    slug = (store_slug or "").strip()
    rec["merchant"] = slug[:64]


def bind_admission(decision: str) -> None:
    rec = _owner.get()
    if rec is None:
        return
    rec["admission"] = (decision or "")[:32]


def current_owner() -> Optional[dict[str, Any]]:
    return _owner.get()


def request_owner_end(*, outcome: str = "") -> Optional[dict[str, Any]]:
    rec = _owner.get()
    if rec is None:
        return None
    rec["outcome"] = (outcome or "")[:32]
    rec["request_ms"] = round((time.perf_counter() - float(rec["t0"])) * 1000.0, 1)
    _owner.set(None)
    return rec


def reset_for_tests() -> None:
    _owner.set(None)
