# -*- coding: utf-8 -*-
"""
Non-blocking DB warm at application startup (Operational Hardening V1 — Step 4B.3).

Runs the existing ``_ensure_cartflow_api_db_warmed`` path in a background thread so
user-facing requests do not pay cold-start schema/backfill cost when warm completes
before they arrive.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Callable, Optional

log = logging.getLogger("cartflow")

_PREFIX = "[DB READY STARTUP WARM]"

_status_lock = threading.Lock()
_condition = threading.Condition(_status_lock)

_status = "not_started"
_duration_ms = 0.0
_error: Optional[str] = None
_thread: Optional[threading.Thread] = None
_last_request_cached_verification: Optional[bool] = None


def _startup_warm_disabled() -> bool:
    raw = (os.environ.get("CARTFLOW_DISABLE_STARTUP_DB_WARM") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _emit(line: str) -> None:
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def startup_warm_status() -> str:
    with _status_lock:
        return str(_status or "not_started")


def is_startup_warm_running() -> bool:
    with _status_lock:
        return _status == "running"


def startup_warm_public_snapshot() -> dict[str, Any]:
    with _status_lock:
        return {
            "startup_warm_status": str(_status or "not_started"),
            "startup_warm_duration_ms": round(float(_duration_ms or 0.0), 1),
            "startup_warm_error": (_error or None),
            "last_request_cached_verification": _last_request_cached_verification,
        }


def record_request_cached_verification(used: bool) -> None:
    global _last_request_cached_verification
    with _status_lock:
        _last_request_cached_verification = bool(used)
    _persist_startup_warm_fields()


def _set_status(
    status: str,
    *,
    duration_ms: float = 0.0,
    error: Optional[str] = None,
) -> None:
    global _status, _duration_ms, _error
    with _condition:
        _status = (status or "not_started").strip()[:16]
        if duration_ms > 0:
            _duration_ms = round(float(duration_ms), 1)
        if error is not None:
            _error = (str(error)[:255] if error else None)
        _condition.notify_all()
    _persist_startup_warm_fields()


def wait_for_startup_warm(*, timeout_s: float = 0.0) -> bool:
    """Wait until warm flag is set or startup warm finishes. Returns ``_cartflow_api_db_warmed``."""
    try:
        import main

        if bool(getattr(main, "_cartflow_api_db_warmed", False)):
            return True
    except Exception:  # noqa: BLE001
        pass

    deadline = time.perf_counter() + max(0.0, float(timeout_s or 0.0))
    with _condition:
        while True:
            try:
                import main

                if bool(getattr(main, "_cartflow_api_db_warmed", False)):
                    return True
            except Exception:  # noqa: BLE001
                pass
            st = _status
            if st in ("succeeded", "failed", "not_started"):
                try:
                    import main

                    return bool(getattr(main, "_cartflow_api_db_warmed", False))
                except Exception:  # noqa: BLE001
                    return False
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                try:
                    import main

                    return bool(getattr(main, "_cartflow_api_db_warmed", False))
                except Exception:  # noqa: BLE001
                    return False
            _condition.wait(timeout=remaining)


def should_defer_user_db_ready(*, allow_defer: bool) -> bool:
    """
    True when a user-facing route should skip blocking warm work.

    Used by refresh-state to return a safe partial payload while startup warm runs.
    """
    if not allow_defer:
        return False
    try:
        import main

        if bool(getattr(main, "_cartflow_api_db_warmed", False)):
            return False
    except Exception:  # noqa: BLE001
        pass
    return is_startup_warm_running()


def dashboard_warm_wait_budget_s() -> float:
    raw = (os.environ.get("CARTFLOW_DASHBOARD_WARM_WAIT_S") or "").strip()
    if not raw:
        return 2.0
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return 2.0
    return max(0.0, min(30.0, val))


def start_db_ready_startup_warm_async(*, warm_fn: Callable[[], None]) -> None:
    """Spawn daemon thread — idempotent per process."""
    global _thread, _status
    if _startup_warm_disabled():
        return
    try:
        import main

        if bool(getattr(main, "_cartflow_api_db_warmed", False)):
            _set_status("succeeded")
            return
    except Exception:  # noqa: BLE001
        pass
    with _status_lock:
        if _status in ("running", "succeeded"):
            return

    def _runner() -> None:
        from services.db_session_lifecycle import (  # noqa: PLC0415
            release_scoped_db_session,
            scoped_db_session_begin,
        )

        _emit(f"{_PREFIX} stage=start")
        t0 = time.perf_counter()
        scoped_db_session_begin()
        try:
            warm_fn()
            dur = (time.perf_counter() - t0) * 1000.0
            try:
                import main

                warmed = bool(getattr(main, "_cartflow_api_db_warmed", False))
            except Exception:  # noqa: BLE001
                warmed = False
            if warmed:
                _emit(f"{_PREFIX} stage=done duration_ms={round(dur, 1)}")
                _set_status("succeeded", duration_ms=dur)
            else:
                msg = "warm finished but _cartflow_api_db_warmed is still false"
                _emit(f"{_PREFIX} stage=failed error={msg}")
                _set_status("failed", duration_ms=dur, error=msg)
        except Exception as exc:  # noqa: BLE001
            dur = (time.perf_counter() - t0) * 1000.0
            err = str(exc)[:255]
            _emit(f"{_PREFIX} stage=failed error={err}")
            _set_status("failed", duration_ms=dur, error=err)
        finally:
            release_scoped_db_session()

    with _status_lock:
        _status = "running"
    _persist_startup_warm_fields()
    _thread = threading.Thread(
        target=_runner,
        name="db-ready-startup-warm",
        daemon=True,
    )
    _thread.start()


def _persist_startup_warm_fields() -> None:
    try:
        from services.db_ready_operational_snapshot_v1 import (  # noqa: PLC0415
            record_startup_warm_snapshot,
        )

        record_startup_warm_snapshot(startup_warm_public_snapshot())
    except Exception as exc:  # noqa: BLE001
        log.warning("startup warm snapshot persist skipped: %s", exc)


def clear_db_ready_startup_warm_for_tests() -> None:
    global _status, _duration_ms, _error, _thread, _last_request_cached_verification
    with _condition:
        _status = "not_started"
        _duration_ms = 0.0
        _error = None
        _thread = None
        _last_request_cached_verification = None
        _condition.notify_all()


__all__ = [
    "clear_db_ready_startup_warm_for_tests",
    "dashboard_warm_wait_budget_s",
    "is_startup_warm_running",
    "record_request_cached_verification",
    "should_defer_user_db_ready",
    "start_db_ready_startup_warm_async",
    "startup_warm_public_snapshot",
    "startup_warm_status",
    "wait_for_startup_warm",
]
