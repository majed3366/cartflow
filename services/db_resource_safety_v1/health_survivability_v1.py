# -*- coding: utf-8 -*-
"""
Health/auth survivability under pool pressure.

/health?db=1 must not wait on a saturated QueuePool (that produced the 503
timeout). If the pool is already critical, report that honestly without a
new checkout. Do not return ok=true without a probe when a probe was asked.
"""
from __future__ import annotations

from typing import Any, Optional


def pool_pressure_blocks_db_probe() -> tuple[bool, dict[str, Any]]:
    """
    True when a new checkout is likely to wait/timeout.
    Caller should return 503 with database=pool_pressure (honest).
    """
    try:
        from services.db_pool_pressure_v1 import (
            LEVEL_CRITICAL,
            LEVEL_HIGH,
            evaluate_db_pool_pressure,
        )

        snap = evaluate_db_pool_pressure()
    except Exception:  # noqa: BLE001
        return False, {}
    if not snap.get("available"):
        return False, snap
    level = str(snap.get("pressure_level") or "")
    if snap.get("exhausted") or level in (LEVEL_CRITICAL, LEVEL_HIGH):
        return True, snap
    return False, snap


def health_db_probe_denied_payload(pressure: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    p = pressure or {}
    return {
        "ok": False,
        "service": "cartflow",
        "database": "pool_pressure",
        "pressure_level": p.get("pressure_level"),
        "checked_out": p.get("checked_out"),
        "available_slots": p.get("available_slots"),
        "timeout_count": p.get("timeout_count"),
    }


__all__ = [
    "health_db_probe_denied_payload",
    "pool_pressure_blocks_db_probe",
]
