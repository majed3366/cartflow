# -*- coding: utf-8 -*-
"""
Restart survival verification for Startup DB Warm (Operational Hardening V1 — Step 4B.4).

Read-only observability: records whether the first dashboard request after a process
restart was protected by background startup warm.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger("cartflow")

_PREFIX = "[RESTART SURVIVAL]"
_PASS_MAX_MS = 1000.0

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


def evaluate_restart_survival(state: dict[str, Any]) -> str:
    """Return ``pending``, ``PASS``, or ``FAIL``."""
    warm_status = str(state.get("startup_warm_status") or "not_started").strip().lower()
    if warm_status == "failed":
        return "FAIL"

    first_at = _parse_iso(state.get("restart_first_dashboard_at"))
    if first_at is None:
        return "pending"

    warm_at = _parse_iso(state.get("restart_warm_completed_at"))
    if warm_status != "succeeded":
        return "FAIL"
    if warm_at is None:
        return "FAIL"
    if first_at < warm_at:
        return "FAIL"

    if bool(state.get("restart_first_dashboard_heavy_warm")):
        return "FAIL"

    cached = state.get("restart_first_dashboard_cached_verification")
    if cached is not True:
        return "FAIL"

    duration_ms = float(state.get("restart_first_dashboard_duration_ms") or 0.0)
    if duration_ms >= _PASS_MAX_MS:
        return "FAIL"

    return "PASS"


def restart_survival_public_view(state: dict[str, Any]) -> dict[str, Any]:
    result = str(state.get("restart_survival_result") or "pending").strip().upper()
    if result not in ("PASS", "FAIL", "PENDING"):
        result = "PENDING"
    cached = state.get("restart_first_dashboard_cached_verification")
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
        "first_dashboard_heavy_warm": bool(
            state.get("restart_first_dashboard_heavy_warm") or False
        ),
        "verification_result": result,
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
        "restart_first_dashboard_heavy_warm": False,
        "restart_survival_result": "pending",
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
        result = evaluate_restart_survival(merged)
        if result != "pending":
            merged["restart_survival_result"] = result
            merged["restart_survival_evaluated_at"] = _utc_now().isoformat()
            _emit_restart_survival_line(merged, result=result)
        record_restart_survival_snapshot(merged)
    except Exception as exc:  # noqa: BLE001
        log.warning("restart survival persist skipped: %s", exc)


def _emit_restart_survival_line(state: dict[str, Any], *, result: str) -> None:
    cached = state.get("restart_first_dashboard_cached_verification")
    cached_s = (
        "true"
        if cached is True
        else ("false" if cached is False else "-")
    )
    line = (
        f"{_PREFIX} "
        f"startup_time={_iso_dt(state.get('restart_startup_at'))} "
        f"warm_complete={_iso_dt(state.get('restart_warm_completed_at'))} "
        f"first_dashboard_request={_iso_dt(state.get('restart_first_dashboard_at'))} "
        f"duration_ms={round(float(state.get('restart_first_dashboard_duration_ms') or 0.0), 1)} "
        f"cached_verification={cached_s} "
        f"result={result}"
    )
    _emit(line)


def clear_restart_survival_for_tests() -> None:
    global _process_restart_at, _local_first_dashboard_recorded
    with _lock:
        _process_restart_at = None
        _local_first_dashboard_recorded = False


__all__ = [
    "clear_restart_survival_for_tests",
    "evaluate_restart_survival",
    "observe_startup_warm_status_change",
    "record_first_dashboard_request",
    "record_restart_cycle_begin",
    "restart_survival_public_view",
]
