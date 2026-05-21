# -*- coding: utf-8 -*-
"""
Read-only runtime observability for the DB due scanner loop (Part 12).

Does not change scanner, recovery, or dispatch behavior.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_lock = threading.Lock()
_last_logged_status: Optional[str] = None

_metrics: Dict[str, Any] = {
    "loop_running": False,
    "last_tick_at": None,
    "last_dispatch_at": None,
    "last_found": 0,
    "last_dispatched": 0,
    "last_skipped": 0,
    "last_error": None,
    "last_tick_skipped_reason": None,
    "total_ticks": 0,
    "total_dispatches": 0,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat()


def _seconds_ago_label(iso_ts: Optional[str]) -> Optional[str]:
    if not iso_ts:
        return None
    try:
        raw = iso_ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = (_utc_now() - dt.astimezone(timezone.utc)).total_seconds()
        if delta < 0:
            return "just now"
        if delta < 60:
            return f"{int(delta)} sec ago"
        if delta < 3600:
            return f"{int(delta // 60)} min ago"
        return f"{int(delta // 3600)} hr ago"
    except (TypeError, ValueError):
        return None


def _resolve_enabled() -> bool:
    from services.recovery_db_due_scanner_loop import is_db_due_scanner_loop_enabled

    return is_db_due_scanner_loop_enabled()


def _resolve_interval_seconds() -> float:
    from services.recovery_db_due_scanner_loop import db_due_scanner_loop_interval_seconds

    return db_due_scanner_loop_interval_seconds()


def _resolve_loop_running() -> bool:
    from services.recovery_db_due_scanner_loop import is_db_due_scanner_loop_task_running

    return is_db_due_scanner_loop_task_running()


def _compute_status(*, enabled: bool, loop_running: bool, last_error: Optional[str]) -> str:
    if not enabled:
        return "disabled"
    if last_error:
        return "error"
    if loop_running:
        return "healthy"
    return "idle"


def _maybe_log_health_update(status: str) -> None:
    global _last_logged_status
    if status == _last_logged_status:
        return
    _last_logged_status = status
    try:
        print(f"[DB DUE SCANNER HEALTH UPDATE] status={status}", flush=True)
    except OSError:
        pass


def clear_db_due_scanner_health_for_tests() -> None:
    """Reset metrics (tests only)."""
    global _last_logged_status
    with _lock:
        _metrics.update(
            {
                "loop_running": False,
                "last_tick_at": None,
                "last_dispatch_at": None,
                "last_found": 0,
                "last_dispatched": 0,
                "last_skipped": 0,
                "last_error": None,
                "last_tick_skipped_reason": None,
                "total_ticks": 0,
                "total_dispatches": 0,
            }
        )
    _last_logged_status = None


def record_db_due_scanner_loop_started() -> None:
    with _lock:
        _metrics["loop_running"] = True
    _refresh_health_log()


def record_db_due_scanner_loop_stopped() -> None:
    with _lock:
        _metrics["loop_running"] = False
    _refresh_health_log()


def record_db_due_scanner_tick_skipped(*, reason: str) -> None:
    now = _utc_now()
    with _lock:
        _metrics["total_ticks"] = int(_metrics.get("total_ticks") or 0) + 1
        _metrics["last_tick_at"] = now
        _metrics["last_tick_skipped_reason"] = (reason or "")[:96]
    _refresh_health_log()


def record_db_due_scanner_tick_result(out: Dict[str, Any]) -> None:
    now = _utc_now()
    found = int(out.get("found", 0) or 0)
    dispatched = int(out.get("dispatched", 0) or 0)
    skipped = int(out.get("skipped", 0) or 0)
    err = out.get("error")
    err_s = str(err).strip()[:512] if err else None
    if out.get("skipped") is True and out.get("reason") == "tick_in_progress":
        record_db_due_scanner_tick_skipped(reason="tick_in_progress")
        return

    with _lock:
        _metrics["total_ticks"] = int(_metrics.get("total_ticks") or 0) + 1
        _metrics["last_tick_at"] = now
        _metrics["last_found"] = found
        _metrics["last_dispatched"] = dispatched
        _metrics["last_skipped"] = skipped
        _metrics["last_error"] = err_s
        _metrics["last_tick_skipped_reason"] = None
        if dispatched > 0:
            _metrics["last_dispatch_at"] = now
            _metrics["total_dispatches"] = int(_metrics.get("total_dispatches") or 0) + dispatched
    _refresh_health_log()


def record_db_due_scanner_loop_error(*, detail: str) -> None:
    with _lock:
        _metrics["last_error"] = (detail or "")[:512]
    _refresh_health_log()


def _refresh_health_log() -> None:
    snap = build_db_due_scanner_health()
    _maybe_log_health_update(str(snap.get("status") or "idle"))


def build_db_due_scanner_health() -> Dict[str, Any]:
    """Snapshot for admin API and operational health card."""
    enabled = _resolve_enabled()
    interval = _resolve_interval_seconds()
    with _lock:
        last_tick = _metrics.get("last_tick_at")
        last_dispatch = _metrics.get("last_dispatch_at")
        last_error = _metrics.get("last_error")
        loop_running = bool(_metrics.get("loop_running")) and _resolve_loop_running()
        payload = {
            "enabled": enabled,
            "interval_seconds": interval,
            "loop_running": loop_running,
            "last_tick_at": _iso(last_tick if isinstance(last_tick, datetime) else None),
            "last_dispatch_at": _iso(
                last_dispatch if isinstance(last_dispatch, datetime) else None
            ),
            "last_found": int(_metrics.get("last_found") or 0),
            "last_dispatched": int(_metrics.get("last_dispatched") or 0),
            "last_skipped": int(_metrics.get("last_skipped") or 0),
            "last_error": last_error,
            "last_tick_skipped_reason": _metrics.get("last_tick_skipped_reason"),
            "total_ticks": int(_metrics.get("total_ticks") or 0),
            "total_dispatches": int(_metrics.get("total_dispatches") or 0),
        }
    status = _compute_status(
        enabled=enabled,
        loop_running=loop_running,
        last_error=last_error if isinstance(last_error, str) else None,
    )
    payload["status"] = status
    payload["last_tick_ago"] = _seconds_ago_label(payload.get("last_tick_at"))
    payload["last_dispatch_ago"] = _seconds_ago_label(payload.get("last_dispatch_at"))
    payload["status_emoji"] = {
        "healthy": "🟢",
        "idle": "🟡",
        "disabled": "⚪",
        "error": "🔴",
    }.get(status, "🟡")
    payload["status_label"] = status
    return payload


def refresh_db_due_scanner_health_observability() -> None:
    """Refresh status log line (e.g. after startup when loop disabled)."""
    _refresh_health_log()


def build_db_due_scanner_health_admin_card() -> Dict[str, Any]:
    """Formatted lines for Jinja admin diagnostics card."""
    h = build_db_due_scanner_health()
    return {
        **h,
        "title": "DB Due Scanner",
        "detail_lines": [
            f"Status: {h.get('status_emoji', '')} {h.get('status_label', '—')}",
            f"Enabled: {str(h.get('enabled')).lower()}",
            f"Interval: {int(h.get('interval_seconds') or 0)}s",
            f"Loop running: {str(h.get('loop_running')).lower()}",
            f"Last tick: {h.get('last_tick_ago') or '—'}",
            f"Last dispatch: {h.get('last_dispatch_ago') or '—'}",
            f"Last found / dispatched / skipped: {h.get('last_found')} / {h.get('last_dispatched')} / {h.get('last_skipped')}",
            f"Total ticks / dispatches: {h.get('total_ticks')} / {h.get('total_dispatches')}",
            f"Last error: {h.get('last_error') or 'None'}",
        ],
    }
