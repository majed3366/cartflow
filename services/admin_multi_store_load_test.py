# -*- coding: utf-8 -*-
"""
Safe admin multi-store cart-event load test — virtual loadtest-store-* rows only.

Does not change recovery, WhatsApp, or production cart-event handlers.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import patch

from services.admin_cart_event_load_test import (
    _mock_whatsapp_send,
    _safe_float_ms,
    _safe_int,
)

_SLOW_MS = 2500.0
_MAX_STORES = 20
_MAX_EVENTS_PER_STORE = 50
_MAX_TOTAL_EVENTS = 1000
_LOADTEST_STORE_PREFIX = "loadtest-store-"
_REASON_ROTATION = ("price", "shipping", "quality", "delivery", "warranty", "other")
_VIP_THRESHOLDS = (300, 500, 750, 1000, 1500)
_AUTOMATION_MODES = ("manual", "assistant", "auto")

MULTI_STORE_LOAD_TEST_DISPLAY_UNAVAILABLE_AR = (
    "آخر اختبار تعدد متاجر: غير متاح مؤقتاً"
)

_lock = threading.Lock()
_latest_result: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class _EventPlanRow:
    store_slug: str
    store_index: int
    session_id: str
    cart_id: str
    reason: str
    expected_store_pk: int


def _loadtest_store_slug(index: int) -> str:
    return f"{_LOADTEST_STORE_PREFIX}{index:03d}"


def is_loadtest_store_slug(slug: str) -> bool:
    s = (slug or "").strip()
    return s.startswith(_LOADTEST_STORE_PREFIX) and len(s) > len(_LOADTEST_STORE_PREFIX)


def clamp_multi_store_counts(
    stores_count: int,
    events_per_store: int,
) -> tuple[int, int, int]:
    """Return (stores, events_per_store, total_events) within v1 hard limits."""
    stores = max(1, min(_MAX_STORES, int(stores_count or 1)))
    per = max(1, min(_MAX_EVENTS_PER_STORE, int(events_per_store or 1)))
    total = stores * per
    if total > _MAX_TOTAL_EVENTS:
        per = max(1, _MAX_TOTAL_EVENTS // stores)
        total = stores * per
    return stores, per, total


def _build_reason_templates_json(store_index: int) -> str:
    marker = f"LOADTEST_STORE_{store_index:03d}"
    templates: dict[str, Any] = {}
    for i, tag in enumerate(_REASON_ROTATION):
        templates[tag] = {
            "enabled": True,
            "message": f"{marker}_{tag}",
            "message_count": 1 + (i % 2),
        }
    return json.dumps(templates, ensure_ascii=False)


def build_virtual_store_profile(store_index: int) -> dict[str, Any]:
    """Per-store config fingerprint for provisioning and contamination checks."""
    idx = int(store_index)
    slug = _loadtest_store_slug(idx)
    vip = _VIP_THRESHOLDS[idx % len(_VIP_THRESHOLDS)]
    templates_json = _build_reason_templates_json(idx)
    return {
        "store_index": idx,
        "store_slug": slug,
        "zid_store_id": slug,
        "vip_cart_threshold": vip,
        "widget_display_name": f"CartFlow {idx:03d}",
        "widget_enabled": bool(idx % 2 == 0),
        "merchant_automation_mode": _AUTOMATION_MODES[idx % len(_AUTOMATION_MODES)],
        "reason_templates_json": templates_json,
        "template_marker": f"LOADTEST_STORE_{idx:03d}",
    }


def provision_virtual_loadtest_stores(stores_count: int) -> list[dict[str, Any]]:
    """Upsert loadtest-store-* rows only; returns profiles with store_pk."""
    from extensions import db
    from models import Store

    profiles: list[dict[str, Any]] = []
    for i in range(1, stores_count + 1):
        prof = build_virtual_store_profile(i)
        slug = prof["store_slug"]
        row = db.session.query(Store).filter(Store.zid_store_id == slug).first()
        if row is None:
            row = Store(
                zid_store_id=slug,
                recovery_delay=1,
                recovery_delay_unit="minutes",
                recovery_attempts=1,
                is_active=True,
            )
            db.session.add(row)
            db.session.flush()
        row.vip_cart_threshold = prof["vip_cart_threshold"]
        row.widget_display_name = prof["widget_display_name"]
        row.widget_enabled = prof["widget_enabled"]
        row.merchant_automation_mode = prof["merchant_automation_mode"]
        row.reason_templates_json = prof["reason_templates_json"]
        prof["store_pk"] = int(row.id)
        profiles.append(prof)
    db.session.commit()
    return profiles


def _build_abandon_payload(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "store": store_slug,
        "session_id": session_id,
        "cart_id": cart_id,
        "event": "cart_abandoned",
        "reason": reason,
        "phone": "966500000001",
        "cart": [{"name": "Multi-store load test item", "price": 1, "quantity": 1}],
    }


def _build_event_plan(
    *,
    run_id: str,
    profiles: list[dict[str, Any]],
    events_per_store: int,
) -> list[_EventPlanRow]:
    plan: list[_EventPlanRow] = []
    for prof in profiles:
        idx = int(prof["store_index"])
        slug = prof["store_slug"]
        pk = int(prof["store_pk"])
        for e in range(events_per_store):
            reason = _REASON_ROTATION[(idx + e) % len(_REASON_ROTATION)]
            sid = f"msload-{run_id}-s{idx:03d}-e{e:03d}"[:96]
            cid = f"cart-{run_id}-s{idx:03d}-e{e:03d}"[:80]
            plan.append(
                _EventPlanRow(
                    store_slug=slug,
                    store_index=idx,
                    session_id=sid,
                    cart_id=cid,
                    reason=reason,
                    expected_store_pk=pk,
                )
            )
    return plan


def _verify_store_config_isolation(
    profiles: list[dict[str, Any]],
) -> tuple[int, list[str]]:
    from extensions import db
    from models import Store

    errors = 0
    samples: list[str] = []

    for prof in profiles:
        slug = prof["store_slug"]
        row = db.session.query(Store).filter(Store.zid_store_id == slug).first()
        if row is None:
            errors += 1
            if len(samples) < 5:
                samples.append(f"missing_store_row:{slug}")
            continue
        marker = prof["template_marker"]
        if getattr(row, "vip_cart_threshold", None) != prof["vip_cart_threshold"]:
            errors += 1
            if len(samples) < 5:
                samples.append(f"vip_threshold_mismatch:{slug}")
        if (getattr(row, "widget_display_name", None) or "") != prof["widget_display_name"]:
            errors += 1
            if len(samples) < 5:
                samples.append(f"widget_name_mismatch:{slug}")
        if bool(getattr(row, "widget_enabled", True)) != bool(prof["widget_enabled"]):
            errors += 1
            if len(samples) < 5:
                samples.append(f"widget_enabled_mismatch:{slug}")
        if (getattr(row, "merchant_automation_mode", None) or "") != prof[
            "merchant_automation_mode"
        ]:
            errors += 1
            if len(samples) < 5:
                samples.append(f"automation_mode_mismatch:{slug}")
        rt_raw = getattr(row, "reason_templates_json", None) or ""
        if marker not in rt_raw:
            errors += 1
            if len(samples) < 5:
                samples.append(f"reason_templates_marker_missing:{slug}")
        for other in profiles:
            if other["store_slug"] == slug:
                continue
            other_marker = other["template_marker"]
            if other_marker in rt_raw:
                errors += 1
                if len(samples) < 5:
                    samples.append(
                        f"reason_templates_cross_leak:{slug} contains {other_marker}"
                    )
    return errors, samples


def _verify_event_rows_isolation(
    plan: list[_EventPlanRow],
) -> tuple[int, list[str]]:
    from extensions import db
    from models import AbandonedCart, CartRecoveryLog, CartRecoveryReason

    errors = 0
    samples: list[str] = []
    session_ids = [p.session_id for p in plan]
    if not session_ids:
        return 0, []

    by_session = {p.session_id: p for p in plan}

    for crr in (
        db.session.query(CartRecoveryReason)
        .filter(CartRecoveryReason.session_id.in_(session_ids))
        .all()
    ):
        sid = str(crr.session_id or "")
        expected = by_session.get(sid)
        if expected is None:
            continue
        got_slug = str(crr.store_slug or "").strip()
        if got_slug != expected.store_slug:
            errors += 1
            if len(samples) < 5:
                samples.append(
                    f"crr_store_slug:{sid} expected={expected.store_slug} got={got_slug}"
                )
        got_reason = str(crr.reason or "").strip().lower()
        if got_reason != expected.reason:
            errors += 1
            if len(samples) < 5:
                samples.append(
                    f"crr_reason:{sid} expected={expected.reason} got={got_reason}"
                )

    for crl in (
        db.session.query(CartRecoveryLog)
        .filter(CartRecoveryLog.session_id.in_(session_ids))
        .all()
    ):
        sid = str(crl.session_id or "")
        expected = by_session.get(sid)
        if expected is None:
            continue
        got_slug = str(crl.store_slug or "").strip()
        if got_slug != expected.store_slug:
            errors += 1
            if len(samples) < 5:
                samples.append(
                    f"crl_store_slug:{sid} expected={expected.store_slug} got={got_slug}"
                )

    for ac in (
        db.session.query(AbandonedCart)
        .filter(AbandonedCart.recovery_session_id.in_(session_ids))
        .all()
    ):
        sid = str(ac.recovery_session_id or "")
        expected = by_session.get(sid)
        if expected is None:
            continue
        ac_store_id = getattr(ac, "store_id", None)
        if ac_store_id is not None and int(ac_store_id) != expected.expected_store_pk:
            errors += 1
            if len(samples) < 5:
                samples.append(
                    f"abandoned_cart_store_id:{sid} expected_pk={expected.expected_store_pk} "
                    f"got_pk={ac_store_id}"
                )

    return errors, samples


def verify_multi_store_contamination(
    profiles: list[dict[str, Any]],
    plan: list[_EventPlanRow],
) -> tuple[int, list[str]]:
    cfg_err, cfg_samples = _verify_store_config_isolation(profiles)
    evt_err, evt_samples = _verify_event_rows_isolation(plan)
    return cfg_err + evt_err, (cfg_samples + evt_samples)[:5]


def get_latest_multi_store_load_test_result() -> Optional[dict[str, Any]]:
    with _lock:
        return dict(_latest_result) if _latest_result else None


def get_latest_multi_store_load_test_display_ar() -> Optional[str]:
    try:
        r = get_latest_multi_store_load_test_result()
        if not r:
            return None
        if not isinstance(r, dict):
            return MULTI_STORE_LOAD_TEST_DISPLAY_UNAVAILABLE_AR
        total = _safe_int(r.get("total_events"), -1)
        if total < 0:
            return MULTI_STORE_LOAD_TEST_DISPLAY_UNAVAILABLE_AR
        success = max(0, _safe_int(r.get("success_count"), 0))
        stores = max(0, _safe_int(r.get("stores_count"), 0))
        contam = max(0, _safe_int(r.get("contamination_errors"), 0))
        errors = max(0, _safe_int(r.get("error_count"), 0))
        avg_ms = _safe_float_ms(r.get("avg_duration_ms"))
        return (
            f"آخر اختبار تعدد متاجر: نجاح {success}/{total}"
            f" — متاجر {stores}"
            f" — تلوث {contam}"
            f" — أخطاء {errors}"
            f" — متوسط {avg_ms:.0f}ms"
        )
    except Exception:
        return MULTI_STORE_LOAD_TEST_DISPLAY_UNAVAILABLE_AR


def stash_latest_multi_store_load_test_result_for_tests(
    data: Optional[dict[str, Any]],
) -> None:
    global _latest_result
    with _lock:
        _latest_result = dict(data) if data else None


def clear_multi_store_load_test_state_for_tests() -> None:
    global _latest_result
    with _lock:
        _latest_result = None


def run_multi_store_cart_event_load_test(
    *,
    stores_count: int = 20,
    events_per_store: int = 50,
    dry_run_whatsapp: bool = True,
) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    from extensions import db, remove_scoped_session
    from main import app
    from services.admin_operational_health import (
        get_db_pool_snapshot_readonly,
        get_operational_counter_snapshots,
    )

    stores_n, per_store, total = clamp_multi_store_counts(stores_count, events_per_store)
    run_id = uuid.uuid4().hex[:10]

    counters_before = get_operational_counter_snapshots()
    pool_before = get_db_pool_snapshot_readonly()

    profiles = provision_virtual_loadtest_stores(stores_n)
    plan = _build_event_plan(run_id=run_id, profiles=profiles, events_per_store=per_store)

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
        for row in plan:
            payload = _build_abandon_payload(
                store_slug=row.store_slug,
                session_id=row.session_id,
                cart_id=row.cart_id,
                reason=row.reason,
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
                        error_samples.append(
                            f"{row.store_slug}:{row.session_id}:HTTP {resp.status_code}"
                        )
            except Exception as exc:  # noqa: BLE001
                dur = (time.perf_counter() - t0) * 1000.0
                durations_ms.append(dur)
                error_count += 1
                if len(error_samples) < 3:
                    error_samples.append(f"{row.store_slug}:{str(exc)[:80]}")
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

    contam_errors, contam_samples = verify_multi_store_contamination(profiles, plan)

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
        "ok": error_count == 0 and pool_timeout_delta == 0 and contam_errors == 0,
        "run_id": run_id,
        "stores_count": stores_n,
        "events_per_store": per_store,
        "max_stores_allowed": _MAX_STORES,
        "max_events_per_store_allowed": _MAX_EVENTS_PER_STORE,
        "max_total_events_allowed": _MAX_TOTAL_EVENTS,
        "total_events": total,
        "success_count": success_count,
        "error_count": error_count,
        "error_samples": error_samples,
        "contamination_errors": contam_errors,
        "contamination_samples": contam_samples,
        "avg_duration_ms": round(avg_ms, 1),
        "max_duration_ms": round(max_ms, 1),
        "slow_count_over_2500ms": slow_count,
        "queuepool_timeout_count": pool_timeout_delta,
        "background_task_failures": bg_fail_delta,
        "dry_run_whatsapp": bool(dry_run_whatsapp),
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "db_pool_before": pool_before,
        "db_pool_after": pool_after,
    }

    global _latest_result
    with _lock:
        _latest_result = dict(summary)

    return summary
