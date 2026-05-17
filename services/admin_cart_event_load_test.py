# -*- coding: utf-8 -*-
"""
Safe admin cart-event load test — exercises POST /api/cart-event without real WhatsApp.

Does not change recovery, decision engine, or production cart-event handlers.
Optional unittest.mock patches apply only for the duration of the test run.
"""
from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import patch

_SLOW_MS = 2500.0
_MAX_EVENTS = 100
_DEFAULT_EVENTS = 20

_lock = threading.Lock()
_latest_result: Optional[dict[str, Any]] = None


def _mock_whatsapp_send(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {"ok": True, "status": "mock_sent", "load_test": True}


def get_latest_load_test_result() -> Optional[dict[str, Any]]:
    with _lock:
        return dict(_latest_result) if _latest_result else None


def get_latest_load_test_display_ar() -> Optional[str]:
    r = get_latest_load_test_result()
    if not r:
        return None
    mode = r.get("event_mode") or "cart_state_sync"
    mode_ar = "تخلي سلة" if mode == "cart_abandoned" else "مزامنة خفيفة"
    pool_delta = int(r.get("queuepool_timeout_count") or 0)
    pool_bit = f" — QueuePool +{pool_delta}" if pool_delta else ""
    return (
        f"آخر اختبار ضغط ({mode_ar}): نجاح {r.get('success_count', 0)}/{r.get('total_events', 0)}"
        f" — أخطاء {r.get('error_count', 0)}"
        f" — متوسط {r.get('avg_duration_ms', 0):.0f}ms"
        f" — أقصى {r.get('max_duration_ms', 0):.0f}ms"
        f"{pool_bit}"
    )


def clear_load_test_state_for_tests() -> None:
    global _latest_result
    with _lock:
        _latest_result = None


def _build_payload(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
    reason_tag: Optional[str],
    phone_present: bool,
) -> dict[str, Any]:
    cart = [{"name": "Load test item", "price": 1, "quantity": 1}]
    base: dict[str, Any] = {
        "store": store_slug,
        "session_id": session_id,
        "cart_id": cart_id,
        "cart": cart,
    }
    if reason_tag:
        base["event"] = "cart_abandoned"
        base["reason"] = reason_tag.strip()[:64]
    else:
        base["event"] = "cart_state_sync"
        base["reason"] = "add"
    if phone_present:
        base["phone"] = "966500000001"
    return base


def run_cart_event_load_test(
    *,
    store_slug: str = "demo",
    events_count: int = _DEFAULT_EVENTS,
    dry_run_whatsapp: bool = True,
    reason_tag: Optional[str] = None,
    phone_present: bool = True,
) -> dict[str, Any]:
    """
  Run sequential cart-event requests via in-process TestClient; return summary only.
    """
    from fastapi.testclient import TestClient

    from extensions import db, remove_scoped_session
    from main import app
    from services.admin_operational_health import (
        get_db_pool_snapshot_readonly,
        get_operational_counter_snapshots,
    )

    slug = (store_slug or "demo").strip()[:96] or "demo"
    n = max(1, min(_MAX_EVENTS, int(events_count or _DEFAULT_EVENTS)))
    run_id = uuid.uuid4().hex[:10]
    rt = (reason_tag or "").strip() or None

    counters_before = get_operational_counter_snapshots()
    pool_before = get_db_pool_snapshot_readonly()

    durations_ms: list[float] = []
    success_count = 0
    error_count = 0
    error_samples: list[str] = []

    patches = []
    if dry_run_whatsapp:
        patches = [
            patch("services.whatsapp_send.send_whatsapp", _mock_whatsapp_send),
            patch("services.whatsapp_send.send_whatsapp_real", _mock_whatsapp_send),
            patch("services.whatsapp_queue.send_whatsapp_real", _mock_whatsapp_send),
        ]

    started_at = datetime.now(timezone.utc).isoformat()

    try:
        for p in patches:
            p.start()
        client = TestClient(app)
        for i in range(n):
            sid = f"loadtest-{run_id}-{i}"[:96]
            cid = f"cart-{run_id}-{i}"[:80]
            payload = _build_payload(
                store_slug=slug,
                session_id=sid,
                cart_id=cid,
                reason_tag=rt,
                phone_present=bool(phone_present),
            )
            t0 = time.perf_counter()
            try:
                resp = client.post("/api/cart-event", json=payload)
                dur = (time.perf_counter() - t0) * 1000.0
                durations_ms.append(dur)
                if 200 <= resp.status_code < 300:
                    success_count += 1
                else:
                    error_count += 1
                    if len(error_samples) < 3:
                        error_samples.append(f"HTTP {resp.status_code}")
            except Exception as exc:  # noqa: BLE001
                dur = (time.perf_counter() - t0) * 1000.0
                durations_ms.append(dur)
                error_count += 1
                if len(error_samples) < 3:
                    error_samples.append(str(exc)[:120])
            finally:
                try:
                    remove_scoped_session()
                except Exception:
                    pass
    finally:
        for p in reversed(patches):
            try:
                p.stop()
            except Exception:
                pass
        try:
            db.session.rollback()
        except Exception:
            pass
        remove_scoped_session()

    counters_after = get_operational_counter_snapshots()
    pool_after = get_db_pool_snapshot_readonly()

    pool_timeout_delta = int(counters_after.get("pool_timeout_count", 0)) - int(
        counters_before.get("pool_timeout_count", 0)
    )
    bg_fail_delta = int(counters_after.get("background_task_errors", 0)) - int(
        counters_before.get("background_task_errors", 0)
    )

    avg_ms = sum(durations_ms) / len(durations_ms) if durations_ms else 0.0
    max_ms = max(durations_ms) if durations_ms else 0.0
    slow_count = sum(1 for d in durations_ms if d > _SLOW_MS)

    summary: dict[str, Any] = {
        "ok": error_count == 0 and pool_timeout_delta == 0,
        "run_id": run_id,
        "store_slug": slug,
        "max_events_allowed": _MAX_EVENTS,
        "events_count": n,
        "event_mode": "cart_abandoned" if rt else "cart_state_sync",
        "dry_run_whatsapp": bool(dry_run_whatsapp),
        "reason_tag": rt,
        "phone_present": bool(phone_present),
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_events": n,
        "success_count": success_count,
        "error_count": error_count,
        "error_samples": error_samples,
        "avg_duration_ms": round(avg_ms, 1),
        "max_duration_ms": round(max_ms, 1),
        "slow_count_over_2500ms": slow_count,
        "queuepool_timeout_count": pool_timeout_delta,
        "background_task_failures": bg_fail_delta,
        "db_pool_before": pool_before,
        "db_pool_after": pool_after,
    }

    global _latest_result
    with _lock:
        _latest_result = dict(summary)

    return summary
