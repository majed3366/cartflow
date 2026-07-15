# -*- coding: utf-8 -*-
"""Simulation event accounting structure — Phase 2 (counters before events)."""
from __future__ import annotations

import json
from typing import Any, Optional

from services.store_reality_simulator.contracts_v1 import (
    ACCOUNTING_BUCKETS,
    BUCKET_DUPLICATE,
    BUCKET_FAILED,
    BUCKET_PERSISTED,
    BUCKET_PLANNED,
    BUCKET_PROCESSED,
    BUCKET_REJECTED,
    BUCKET_REPLAYED,
    BUCKET_SUPPRESSED,
    BUCKET_UNSUPPORTED,
    empty_accounting,
)


def normalize_accounting(raw: Any) -> dict[str, int]:
    base = empty_accounting()
    if not isinstance(raw, dict):
        return base
    for key in ACCOUNTING_BUCKETS:
        try:
            base[key] = max(0, int(raw.get(key, 0) or 0))
        except (TypeError, ValueError):
            base[key] = 0
    return base


def accounting_from_json(raw: Optional[str]) -> dict[str, int]:
    if not raw:
        return empty_accounting()
    try:
        return normalize_accounting(json.loads(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return empty_accounting()


def accounting_to_json(counts: dict[str, int]) -> str:
    return json.dumps(normalize_accounting(counts), ensure_ascii=False, sort_keys=True)


def increment_bucket(counts: dict[str, int], bucket: str, amount: int = 1) -> dict[str, int]:
    out = normalize_accounting(counts)
    key = str(bucket or "").strip()
    if key not in out:
        raise KeyError(f"unknown_accounting_bucket:{key}")
    out[key] = out[key] + max(0, int(amount))
    return out


def reconcile_accounting(counts: dict[str, int]) -> dict[str, Any]:
    """
    Identity check (Phase 2 structure):
    planned ~= persisted + rejected + unsupported + failed (+ in-flight later)
    """
    c = normalize_accounting(counts)
    accounted = (
        c[BUCKET_PERSISTED]
        + c[BUCKET_REJECTED]
        + c[BUCKET_UNSUPPORTED]
        + c[BUCKET_FAILED]
    )
    planned = c[BUCKET_PLANNED]
    delta = planned - accounted
    return {
        "ok": delta == 0 or planned == 0,
        "planned": planned,
        "accounted_terminal": accounted,
        "delta": delta,
        "note": (
            "Phase 2: accounting structure only; "
            "full reconciliation after Phase 3 event generation"
        ),
        "side_buckets": {
            BUCKET_PROCESSED: c[BUCKET_PROCESSED],
            BUCKET_DUPLICATE: c[BUCKET_DUPLICATE],
            BUCKET_REPLAYED: c[BUCKET_REPLAYED],
            BUCKET_SUPPRESSED: c[BUCKET_SUPPRESSED],
        },
    }
