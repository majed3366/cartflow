# -*- coding: utf-8 -*-
"""
Restart survival verification for Startup DB Warm (Operational Hardening V1 — Step 4B.4+).

Read-only observability: whether the first dashboard request after restart was
protected from cold-start DB warm — not merely whether warm finished first.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger("cartflow")

_PREFIX = "[RESTART SURVIVAL]"
_PASS_MAX_MS = 1000.0

TIMING_WARM_BEFORE_REQUEST = "warm_completed_before_request"
TIMING_DURING_WARM = "request_arrived_during_warm"
TIMING_BEFORE_WARM_SAFE = "request_arrived_before_warm_and_used_safe_path"
TIMING_WARM_FAILED = "warm_failed"
TIMING_UNKNOWN = "unknown"

_lock = threading.Lock()
_process_restart_at: Optional[datetime] = None
_local_first_dashboard_recorded = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_dt(val: Any) -> str:
    if val is None:
        return "-"
    if isinstance(val, datetime):
        dt = val
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    s = str(val).strip()
    return s if s else "-"


def _parse_iso(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        dt = val
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    try:
        s = str(val).strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _emit(line: str) -> None:
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def _bool_or_none(val: Any) -> Optional[bool]:
    if val is None:
        return None
    return bool(val)


def request_used_safe_path(state: dict[str, Any]) -> bool:
    """True when the first dashboard request avoided paying cold warm in-request."""
    if state.get("restart_first_dashboard_used_safe_path") is True:
        return True
    if state.get("restart_first_dashboard_cached_verification") is True:
        return True
    if bool(state.get("restart_first_dashboard_heavy_warm")):
        return False
    warm_status = str(state.get("startup_warm_status") or "not_started").strip().lower()
    return warm_status in ("succeeded", "running")


def classify_restart_survival_timing(
    state: dict[str, Any],
    *,
    protected: bool,
) -> str:
    warm_status = str(state.get("startup_warm_status") or "not_started").strip().lower()
    if warm_status == "failed":
        return TIMING_WARM_FAILED

    first_at = _parse_iso(state.get("restart_first_dashboard_at"))
    warm_at = _parse_iso(state.get("restart_warm_completed_at"))
    cached = state.get("restart_first_dashboard_cached_verification") is True
    heavy = bool(state.get("restart_first_dashboard_heavy_warm"))

    if first_at is None:
        return TIMING_UNKNOWN
    if warm_at is None:
        if warm_status == "running":
            return TIMING_DURING_WARM
        if protected and cached:
            return TIMING_BEFORE_WARM_SAFE
        return TIMING_UNKNOWN
    if first_at >= warm_at:
        return TIMING_WARM_BEFORE_REQUEST
    if protected and cached:
        return TIMING_BEFORE_WARM_SAFE
    if protected and not heavy:
        return TIMING_DURING_WARM
    return TIMING_UNKNOWN


def assess_restart_survival(state: dict[str, Any]) -> dict[str, Any]:
    """
    Operational PASS/FAIL — measures protection, not warm-before-request ordering alone.
    """
    warm_status = str(state.get("startup_warm_status") or "not_started").strip().lower()
    first_at = _parse_iso(state.get("restart_first_dashboard_at"))
    heavy = bool(state.get("restart_first_dashboard_heavy_warm"))
    cached = _bool_or_none(state.get("restart_first_dashboard_cached_verification"))
    duration_ms = round(float(state.get("restart_first_dashboard_duration_ms") or 0.0), 1)
    safe_path = request_used_safe_path(state)

    if first_at is None:
        return {
            "result": "pending",
            "timing": TIMING_UNKNOWN,
            "protected": False,
            "reason": "awaiting_first_dashboard",
        }

    protected = (
        not heavy
        and duration_ms < _PASS_MAX_MS
        and (cached is True or safe_path)
    )
    timing = classify_restart_survival_timing(state, protected=protected)

    if warm_status == "failed":
        return {
            "result": "FAIL",
            "timing": TIMING_WARM_FAILED,
            "protected": False,
            "reason": "startup_warm_failed",
        }

    if duration_ms >= _PASS_MAX_MS:
        return {
            "result": "FAIL",
            "timing": timing,
            "protected": False,
            "reason": "slow_first_request",
        }

    if heavy:
        return {
            "result": "FAIL",
            "timing": timing,
            "protected": False,
            "reason": "heavy_warm_in_request",
        }

    if cached is not True and not safe_path:
        return {
            "result": "FAIL",
            "timing": timing,
            "protected": False,
            "reason": "unprotected_request",
        }

    warm_ok = warm_status in ("succeeded", "running") or (not heavy and safe_path)
    if not warm_ok:
        return {
            "result": "FAIL",
            "timing": timing,
            "protected": False,
            "reason": "startup_warm_not_ready",
        }

    return {
        "result": "PASS",
        "timing": timing,
        "protected": True,
        "reason": "fast_protected_request",
    }


def evaluate_restart_survival(state: dict[str, Any]) -> str:
    """Return ``pending``, ``PASS``, or ``FAIL``."""
    return str(assess_restart_survival(state).get("result") or "pending")


def timing_label_ar(timing: str) -> str:
    key = (timing or "").strip().lower()
    labels = {
        TIMING_WARM_BEFORE_REQUEST: "اكتملت التهيئة قبل أول طلب للوحة",
        TIMING_DURING_WARM: "طلب لوحة التاجر وصل أثناء التهيئة، وتمت حمايته",
        TIMING_BEFORE_WARM_SAFE: "طلب لوحة التاجر وصل أثناء التهيئة، وتمت حمايته",
        TIMING_WARM_FAILED: "فشل Startup Warm",
        TIMING_UNKNOWN: "غير معروف",
    }
    return labels.get(key, labels[TIMING_UNKNOWN])


def restart_survival_public_view(state: dict[str, Any]) -> dict[str, Any]:
    assessment = assess_restart_survival(state)
    stored_result = str(state.get("restart_survival_result") or "pending").strip().upper()
    result = stored_result if stored_result in ("PASS", "FAIL", "PENDING") else "PENDING"
    if result == "PENDING" and assessment.get("result") in ("PASS", "FAIL"):
        result = str(assessment.get("result")).upper()

    timing = str(
        state.get("restart_survival_timing") or assessment.get("timing") or TIMING_UNKNOWN
    )
    protected = state.get("restart_survival_protected")
    if protected is None:
        protected = assessment.get("protected")

    cached = state.get("restart_first_dashboard_cached_verification")
    pass_headline_ar = None
    if result == "PASS":
        pass_headline_ar = "تمت حماية أول طلب للوحة التاجر من تهيئة الإقلاع"

    return {
        "startup_warm_status": str(state.get("startup_warm_status") or "not_started"),
        "startup_warm_duration_ms": round(
            float(state.get("startup_warm_duration_ms") or 0.0), 1
        ),
        "startup_time": state.get("restart_startup_at"),
        "warm_completed_at": state.get("restart_warm_completed_at"),
        "first_dashboard_request_at": state.get("restart_first_dashboard_at"),
        "first_dashboard_duration_ms": round(
            float(state.get("restart_first_dashboard_duration_ms") or 0.0), 1
        ),
        "first_dashboard_cached_verification": cached,
        "first_dashboard_used_safe_path": bool(
            state.get("restart_first_dashboard_used_safe_path") or False
        ),
        "first_dashboard_heavy_warm": bool(
            state.get("restart_first_dashboard_heavy_warm") or False
        ),
        "verification_result": result,
        "timing": timing,
        "timing_label_ar": timing_label_ar(timing),
        "protected": protected,
        "reason": state.get("restart_survival_reason") or assessment.get("reason"),
        "pass_headline_ar": pass_headline_ar,
        "evaluated_at": state.get("restart_survival_evaluated_at"),
    }


def _persist_restart_survival(payload: dict[str, Any]) -> None:
    try:
        from services.db_ready_operational_snapshot_v1 import (  # noqa: PLC0415
            record_restart_survival_snapshot,
        )

        record_restart_survival_snapshot(payload)
    except Exception as exc:  # noqa: BLE001
        log.warning("restart survival snapshot persist skipped: %s", exc)


def record_restart_cycle_begin() -> None:
    """Mark a new process restart cycle (called from app startup)."""
    global _process_restart_at, _local_first_dashboard_recorded
    now = _utc_now()
    with _lock:
        _process_restart_at = now
        _local_first_dashboard_recorded = False
    payload = {
        "restart_startup_at": now.isoformat(),
        "restart_warm_completed_at": None,
        "restart_first_dashboard_at": None,
        "restart_first_dashboard_duration_ms": 0.0,
        "restart_first_dashboard_cached_verification": None,
        "restart_first_dashboard_used_safe_path": None,
        "restart_first_dashboard_heavy_warm": False,
        "restart_survival_result": "pending",
        "restart_survival_timing": TIMING_UNKNOWN,
        "restart_survival_protected": None,
        "restart_survival_reason": None,
        "restart_survival_evaluated_at": None,
    }
    _persist_restart_survival(payload)


def observe_startup_warm_status_change(*, status: str) -> None:
    """Record warm completion timestamp when startup warm finishes."""
    st = (status or "").strip().lower()
    if st not in ("succeeded", "failed"):
        return
    now = _utc_now()
    _merge_persist_and_evaluate(
        {
            "restart_warm_completed_at": now.isoformat(),
        }
    )


def record_first_dashboard_request(
    *,
    duration_ms: float,
    cached_verification: bool,
    used_safe_path: bool,
    heavy_warm_in_request: bool,
) -> None:
    """Record the first completed dashboard db_ready request for this restart cycle."""
    global _local_first_dashboard_recorded
    with _lock:
        if _local_first_dashboard_recorded:
            return
    try:
        from services.db_ready_operational_snapshot_v1 import (  # noqa: PLC0415
            load_db_ready_operational_snapshot,
        )

        snap = load_db_ready_operational_snapshot(reload_db=True)
        if snap.get("restart_first_dashboard_at"):
            with _lock:
                _local_first_dashboard_recorded = True
            return
    except Exception:  # noqa: BLE001
        pass

    now = _utc_now()
    _merge_persist_and_evaluate(
        {
            "restart_first_dashboard_at": now.isoformat(),
            "restart_first_dashboard_duration_ms": round(float(duration_ms or 0.0), 1),
            "restart_first_dashboard_cached_verification": bool(cached_verification),
            "restart_first_dashboard_used_safe_path": bool(used_safe_path),
            "restart_first_dashboard_heavy_warm": bool(heavy_warm_in_request),
        }
    )
    with _lock:
        _local_first_dashboard_recorded = True


def _merge_persist_and_evaluate(patch: dict[str, Any]) -> None:
    try:
        from services.db_ready_operational_snapshot_v1 import (  # noqa: PLC0415
            load_db_ready_operational_snapshot,
            record_restart_survival_snapshot,
        )

        snap = load_db_ready_operational_snapshot(reload_db=False)
        merged = dict(snap)
        merged.update(patch)
        assessment = assess_restart_survival(merged)
        result = str(assessment.get("result") or "pending")
        if result != "pending":
            merged["restart_survival_result"] = result
            merged["restart_survival_timing"] = str(assessment.get("timing") or TIMING_UNKNOWN)
            merged["restart_survival_protected"] = bool(assessment.get("protected"))
            merged["restart_survival_reason"] = str(assessment.get("reason") or "")[:64]
            merged["restart_survival_evaluated_at"] = _utc_now().isoformat()
            _emit_restart_survival_line(merged, assessment=assessment)
        record_restart_survival_snapshot(merged)
    except Exception as exc:  # noqa: BLE001
        log.warning("restart survival persist skipped: %s", exc)


def _emit_restart_survival_line(
    state: dict[str, Any],
    *,
    assessment: dict[str, Any],
) -> None:
    cached = state.get("restart_first_dashboard_cached_verification")
    cached_s = (
        "true"
        if cached is True
        else ("false" if cached is False else "-")
    )
    heavy = bool(state.get("restart_first_dashboard_heavy_warm"))
    line = (
        f"{_PREFIX} "
        f"timing={assessment.get('timing') or TIMING_UNKNOWN} "
        f"protected={'true' if assessment.get('protected') else 'false'} "
        f"duration_ms={round(float(state.get('restart_first_dashboard_duration_ms') or 0.0), 1)} "
        f"cached_verification={cached_s} "
        f"heavy_warm={'true' if heavy else 'false'} "
        f"result={assessment.get('result')} "
        f"reason={assessment.get('reason') or '-'}"
    )
    _emit(line)


def clear_restart_survival_for_tests() -> None:
    global _process_restart_at, _local_first_dashboard_recorded
    with _lock:
        _process_restart_at = None
        _local_first_dashboard_recorded = False


__all__ = [
    "TIMING_BEFORE_WARM_SAFE",
    "TIMING_DURING_WARM",
    "TIMING_WARM_BEFORE_REQUEST",
    "TIMING_WARM_FAILED",
    "assess_restart_survival",
    "classify_restart_survival_timing",
    "clear_restart_survival_for_tests",
    "evaluate_restart_survival",
    "observe_startup_warm_status_change",
    "record_first_dashboard_request",
    "record_restart_cycle_begin",
    "request_used_safe_path",
    "restart_survival_public_view",
    "timing_label_ar",
]
