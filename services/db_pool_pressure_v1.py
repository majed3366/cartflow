# -*- coding: utf-8 -*-
"""
DB pool pressure evaluation and scanner circuit breaker (Production Reliability v2).

Read-only pressure signals; scanner skips ticks when pool is near exhaustion so
background work does not compete with API/dashboard traffic.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional, Tuple

log = logging.getLogger("cartflow")

LEVEL_OK = "ok"
LEVEL_ELEVATED = "elevated"
LEVEL_HIGH = "high"
LEVEL_CRITICAL = "critical"

# Utilization thresholds (checked_out / max_connections).
_DEFAULT_ELEVATED_UTIL = 0.60
_DEFAULT_HIGH_UTIL = 0.75
_DEFAULT_CRITICAL_UTIL = 0.85

# Absolute minimum available slots before escalating (when metrics known).
_DEFAULT_ELEVATED_MIN_SLOTS = 8
_DEFAULT_HIGH_MIN_SLOTS = 5
_DEFAULT_CRITICAL_MIN_SLOTS = 2


def _env_float(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def pool_pressure_thresholds() -> dict[str, Any]:
    return {
        "elevated_utilization": _env_float(
            "CARTFLOW_DB_POOL_ELEVATED_UTIL", _DEFAULT_ELEVATED_UTIL
        ),
        "high_utilization": _env_float(
            "CARTFLOW_DB_POOL_HIGH_UTIL", _DEFAULT_HIGH_UTIL
        ),
        "critical_utilization": _env_float(
            "CARTFLOW_DB_POOL_CRITICAL_UTIL", _DEFAULT_CRITICAL_UTIL
        ),
        "elevated_min_available_slots": _env_int(
            "CARTFLOW_DB_POOL_ELEVATED_MIN_SLOTS", _DEFAULT_ELEVATED_MIN_SLOTS
        ),
        "high_min_available_slots": _env_int(
            "CARTFLOW_DB_POOL_HIGH_MIN_SLOTS", _DEFAULT_HIGH_MIN_SLOTS
        ),
        "critical_min_available_slots": _env_int(
            "CARTFLOW_DB_POOL_CRITICAL_MIN_SLOTS", _DEFAULT_CRITICAL_MIN_SLOTS
        ),
    }


def _utilization_pct(checked_out: Optional[int], max_connections: Optional[int]) -> Optional[float]:
    if checked_out is None or max_connections is None or int(max_connections) <= 0:
        return None
    try:
        return round(100.0 * int(checked_out) / int(max_connections), 1)
    except (TypeError, ValueError):
        return None


def evaluate_db_pool_pressure() -> dict[str, Any]:
    """
    Canonical pool pressure snapshot with level and circuit-breaker flag.

    Fields: pool_size, max_overflow, max_connections, checked_out, overflow,
    available_slots, utilization_pct, timeout_count, exhausted, pressure_level,
    circuit_breaker_open, warning_ar.
    """
    from services.db_pool_diagnostics import build_db_pool_health_snapshot

    snap = build_db_pool_health_snapshot()
    thresholds = pool_pressure_thresholds()

    pool_size = snap.get("size")
    max_overflow = snap.get("overflow")
    checked_out = snap.get("checked_out")
    max_connections = snap.get("max_connections")
    available_slots = snap.get("available_slots")
    timeout_count = int(snap.get("timeout_count") or 0)
    exhausted = bool(snap.get("exhausted"))
    util_pct = _utilization_pct(
        int(checked_out) if checked_out is not None else None,
        int(max_connections) if max_connections is not None else None,
    )

    level = LEVEL_OK
    warning_ar: Optional[str] = None
    circuit_open = False

    if not snap.get("available"):
        level = LEVEL_OK
    elif exhausted or timeout_count > 0:
        level = LEVEL_CRITICAL
        circuit_open = True
        warning_ar = "مسبح القاعدة منهك — إيقاف الماسح الضوئي مؤقتاً"
    elif available_slots is not None and int(available_slots) <= int(
        thresholds["critical_min_available_slots"]
    ):
        level = LEVEL_CRITICAL
        circuit_open = True
        warning_ar = f"اتصالات قليلة متبقية ({available_slots}) — ضغط حرج على المسبح"
    elif util_pct is not None and util_pct >= thresholds["critical_utilization"] * 100:
        level = LEVEL_CRITICAL
        circuit_open = True
        warning_ar = f"استخدام المسبح {util_pct}% — ضغط حرج"
    elif available_slots is not None and int(available_slots) <= int(
        thresholds["high_min_available_slots"]
    ):
        level = LEVEL_HIGH
        circuit_open = True
        warning_ar = f"اتصالات متبقية {available_slots} — تخطي الماسح الضوئي"
    elif util_pct is not None and util_pct >= thresholds["high_utilization"] * 100:
        level = LEVEL_HIGH
        circuit_open = True
        warning_ar = f"استخدام المسبح {util_pct}% — تخطي الماسح الضوئي"
    elif available_slots is not None and int(available_slots) <= int(
        thresholds["elevated_min_available_slots"]
    ):
        level = LEVEL_ELEVATED
        warning_ar = f"اتصالات متبقية {available_slots} — مراقبة ضغط المسبح"
    elif util_pct is not None and util_pct >= thresholds["elevated_utilization"] * 100:
        level = LEVEL_ELEVATED
        warning_ar = f"استخدام المسبح {util_pct}% — مراقبة ضغط المسبح"

    out: dict[str, Any] = {
        "available": bool(snap.get("available")),
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "max_connections": max_connections,
        "checked_out": checked_out,
        "overflow": max_overflow,
        "available_slots": available_slots,
        "utilization_pct": util_pct,
        "timeout_count": timeout_count,
        "exhausted": exhausted,
        "pressure_level": level,
        "circuit_breaker_open": circuit_open,
        "warning_ar": warning_ar,
        "pool_class": snap.get("pool_class"),
    }

    if level in (LEVEL_ELEVATED, LEVEL_HIGH, LEVEL_CRITICAL):
        try:
            log.warning(
                "[DB POOL PRESSURE] level=%s checked_out=%s max=%s available=%s util_pct=%s",
                level,
                checked_out,
                max_connections,
                available_slots,
                util_pct,
            )
        except Exception:  # noqa: BLE001
            pass

    return out


def scanner_should_skip_due_to_pool_pressure() -> Tuple[bool, str, dict[str, Any]]:
    """
    Returns (should_skip, reason_code, pressure_snapshot).

    Scanner circuit breaker opens at HIGH or CRITICAL pressure.
    """
    pressure = evaluate_db_pool_pressure()
    if not pressure.get("available"):
        return False, "", pressure
    if pressure.get("circuit_breaker_open"):
        level = str(pressure.get("pressure_level") or LEVEL_HIGH)
        return True, f"pool_pressure_{level}", pressure
    return False, "", pressure


def merge_pool_pressure_into_health_snapshot(snap: dict[str, Any]) -> dict[str, Any]:
    """Augment an existing health dict with pressure fields (non-destructive)."""
    pressure = evaluate_db_pool_pressure()
    merged = dict(snap)
    db_pool = dict(merged.get("db_pool") or {})
    db_pool.update(pressure)
    merged["db_pool"] = db_pool
    merged["db_pool_pressure"] = {
        "pressure_level": pressure.get("pressure_level"),
        "circuit_breaker_open": pressure.get("circuit_breaker_open"),
        "warning_ar": pressure.get("warning_ar"),
    }
    return merged


__all__ = [
    "LEVEL_CRITICAL",
    "LEVEL_ELEVATED",
    "LEVEL_HIGH",
    "LEVEL_OK",
    "evaluate_db_pool_pressure",
    "merge_pool_pressure_into_health_snapshot",
    "pool_pressure_thresholds",
    "scanner_should_skip_due_to_pool_pressure",
]
