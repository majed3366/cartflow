# -*- coding: utf-8 -*-
"""
Admin multi-store mixed-behavior load test — lifecycle + isolation (loadtest-store-* only).
"""
from __future__ import annotations

import random
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
from services.admin_multi_store_load_test import (
    _MAX_EVENTS_PER_STORE,
    _MAX_STORES,
    _MAX_TOTAL_EVENTS,
    _REASON_ROTATION,
    _SLOW_MS,
    clamp_multi_store_counts,
    provision_virtual_loadtest_stores,
    _verify_store_config_isolation,
)

MIXED_BEHAVIOR_LOAD_TEST_DISPLAY_UNAVAILABLE_AR = (
    "آخر اختبار سلوك مختلط: غير متاح مؤقتاً"
)

_SYNC_REASONS = ("add", "remove", "page_load")
_WIDGET_REASON_TAGS = (
    "price_high",
    "shipping_slow",
    "quality_issue",
    "delivery_delay",
    "warranty_question",
    "other",
)
_KINDS_BASE_50 = (
    ["sync"] * 20
    + ["abandon"] * 12
    + ["reason"] * 8
    + ["return"] * 5
    + ["purchase"] * 5
)

_lock = threading.Lock()
_latest_result: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class MixedEventPlanRow:
    store_slug: str
    store_index: int
    session_id: str
    cart_id: str
    kind: str
    reason: str
    expected_store_pk: int
    expect_vip: bool = False


def _mixed_kind_slots(events_per_store: int) -> list[str]:
    if events_per_store <= 0:
        return []
    if events_per_store == 50:
        base = list(_KINDS_BASE_50)
    else:
        sync_n = events_per_store * 40 // 100
        ab_n = events_per_store * 25 // 100
        rs_n = events_per_store * 15 // 100
        ret_n = events_per_store * 10 // 100
        pur_n = events_per_store * 10 // 100
        base = (
            ["sync"] * sync_n
            + ["abandon"] * ab_n
            + ["reason"] * rs_n
            + ["return"] * ret_n
            + ["purchase"] * pur_n
        )
        fill = 0
        while len(base) < events_per_store:
            base.append(("sync", "abandon", "reason", "return", "purchase")[fill % 5])
            fill += 1
        base = base[:events_per_store]
    return base


def _build_mixed_event_plan(
    *,
    run_id: str,
    profiles: list[dict[str, Any]],
    events_per_store: int,
) -> list[MixedEventPlanRow]:
    plan: list[MixedEventPlanRow] = []
    for prof in profiles:
        idx = int(prof["store_index"])
        slug = prof["store_slug"]
        pk = int(prof["store_pk"])
        vip_th = int(prof["vip_cart_threshold"])
        slots = list(_mixed_kind_slots(events_per_store))
        rng = random.Random(idx * 1009 + len(run_id))
        rng.shuffle(slots)
        abandon_pool: list[tuple[str, str]] = []
        for e, kind in enumerate(slots):
            reason = _REASON_ROTATION[(idx + e) % len(_REASON_ROTATION)]
            if kind in ("return", "purchase") and abandon_pool:
                sid, cid = abandon_pool[e % len(abandon_pool)]
            else:
                sid = f"msmixed-{run_id}-s{idx:03d}-e{e:03d}"[:96]
                cid = f"cart-{run_id}-s{idx:03d}-e{e:03d}"[:80]
            expect_vip = False
            if kind == "abandon":
                abandon_pool.append((sid, cid))
                if (e + idx) % 4 == 0:
                    expect_vip = True
            plan.append(
                MixedEventPlanRow(
                    store_slug=slug,
                    store_index=idx,
                    session_id=sid,
                    cart_id=cid,
                    kind=kind,
                    reason=reason,
                    expected_store_pk=pk,
                    expect_vip=expect_vip,
                )
            )
        _ = vip_th  # used at execute for cart_total
    return plan


def _vip_cart_total(prof: dict[str, Any]) -> float:
    return float(int(prof["vip_cart_threshold"]) + 150.0)


def _build_sync_payload(row: MixedEventPlanRow, event_idx: int) -> dict[str, Any]:
    reason = _SYNC_REASONS[event_idx % len(_SYNC_REASONS)]
    return {
        "store": row.store_slug,
        "session_id": row.session_id,
        "cart_id": row.cart_id,
        "event": "cart_state_sync",
        "reason": reason,
        "cart_total": 25.0,
        "items_count": 1,
    }


def _build_abandon_payload(
    row: MixedEventPlanRow, prof: dict[str, Any]
) -> dict[str, Any]:
    total = _vip_cart_total(prof) if row.expect_vip else 25.0
    return {
        "store": row.store_slug,
        "session_id": row.session_id,
        "cart_id": row.cart_id,
        "event": "cart_abandoned",
        "reason": row.reason,
        "phone": "966500000001",
        "cart_total": total,
        "cart": [{"name": "Mixed load item", "price": total, "quantity": 1}],
    }


def _build_return_payload(row: MixedEventPlanRow) -> dict[str, Any]:
    return {
        "store": row.store_slug,
        "session_id": row.session_id,
        "cart_id": row.cart_id,
        "passive_return_visit": True,
        "return_visit_kind": "passive_return_visit",
        "recovery_return_context": "page",
    }


def _execute_mixed_row(
    client: Any,
    row: MixedEventPlanRow,
    prof: dict[str, Any],
    abandon_pool: dict[str, list[tuple[str, str]]],
) -> tuple[int, Optional[str]]:
    """Returns (http_status, error_sample)."""
    slug = row.store_slug
    pool = abandon_pool.setdefault(slug, [])

    if row.kind in ("return", "purchase") and not any(
        p[0] == row.session_id for p in pool
    ):
        seed = _build_abandon_payload(row, prof)
        r0 = client.post("/api/cart-event", json=seed)
        if 200 <= r0.status_code < 300:
            pool.append((row.session_id, row.cart_id))

    if row.kind == "sync":
        resp = client.post(
            "/api/cart-event",
            json=_build_sync_payload(row, row.store_index),
        )
    elif row.kind == "abandon":
        resp = client.post("/api/cart-event", json=_build_abandon_payload(row, prof))
        if 200 <= resp.status_code < 300:
            pool.append((row.session_id, row.cart_id))
    elif row.kind == "reason":
        tag = _WIDGET_REASON_TAGS[row.store_index % len(_WIDGET_REASON_TAGS)]
        reason_body: dict[str, Any] = {
            "store_slug": row.store_slug,
            "session_id": row.session_id,
            "reason_tag": tag,
        }
        if tag == "other":
            reason_body["custom_reason"] = f"Load test mixed {row.session_id[-12:]}"
        resp = client.post("/api/cart-recovery/reason", json=reason_body)
    elif row.kind == "return":
        resp = client.post("/api/cart-event", json=_build_return_payload(row))
    elif row.kind == "purchase":
        resp = client.post(
            "/api/conversion",
            json={
                "store_slug": row.store_slug,
                "session_id": row.session_id,
                "purchase_completed": True,
            },
        )
    else:
        return 400, f"unknown_kind:{row.kind}"

    if 200 <= resp.status_code < 300:
        return resp.status_code, None
    return resp.status_code, f"{row.kind}:HTTP {resp.status_code}"


def _verify_mixed_event_rows_isolation(
    plan: list[MixedEventPlanRow],
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
        if expected.expect_vip and not bool(getattr(ac, "vip_mode", False)):
            errors += 1
            if len(samples) < 5:
                samples.append(f"vip_mode_expected:{sid} store={expected.store_slug}")

    return errors, samples


def _verify_lifecycle_isolation(plan: list[MixedEventPlanRow]) -> tuple[int, list[str]]:
    from extensions import db
    from main import _is_user_converted, _recovery_key_from_store_and_session
    from models import AbandonedCart

    errors = 0
    samples: list[str] = []

    for row in plan:
        if row.kind == "purchase":
            key = _recovery_key_from_store_and_session(row.store_slug, row.session_id)
            if not _is_user_converted(key):
                errors += 1
                if len(samples) < 5:
                    samples.append(f"lifecycle_purchase_not_converted:{row.session_id}")

    store_pks = {p.store_slug: p.expected_store_pk for p in plan}
    for row in plan:
        if row.kind != "abandon" or not row.expect_vip:
            continue
        ac = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.recovery_session_id == row.session_id)
            .order_by(AbandonedCart.id.desc())
            .first()
        )
        if ac is None:
            errors += 1
            if len(samples) < 5:
                samples.append(f"lifecycle_vip_row_missing:{row.session_id}")
            continue
        if int(getattr(ac, "store_id", 0) or 0) != row.expected_store_pk:
            errors += 1
            if len(samples) < 5:
                samples.append(f"lifecycle_vip_wrong_store:{row.session_id}")

    for ac in (
        db.session.query(AbandonedCart)
        .filter(AbandonedCart.recovery_session_id.in_([p.session_id for p in plan]))
        .all()
    ):
        sid = str(ac.recovery_session_id or "")
        row = next((p for p in plan if p.session_id == sid), None)
        if row is None:
            continue
        expected_pk = store_pks.get(row.store_slug)
        if expected_pk is not None and int(getattr(ac, "store_id", 0) or 0) != expected_pk:
            errors += 1
            if len(samples) < 5:
                samples.append(f"lifecycle_ac_wrong_store_pk:{sid}")

    return errors, samples


def verify_mixed_behavior(
    profiles: list[dict[str, Any]],
    plan: list[MixedEventPlanRow],
) -> tuple[int, int, list[str]]:
    cfg_err, cfg_samples = _verify_store_config_isolation(profiles)
    evt_err, evt_samples = _verify_mixed_event_rows_isolation(plan)
    life_err, life_samples = _verify_lifecycle_isolation(plan)
    contam = cfg_err + evt_err
    life = life_err
    return contam, life, (cfg_samples + evt_samples + life_samples)[:5]


def get_latest_mixed_behavior_load_test_result() -> Optional[dict[str, Any]]:
    with _lock:
        return dict(_latest_result) if _latest_result else None


def get_latest_mixed_behavior_load_test_display_ar() -> Optional[str]:
    try:
        r = get_latest_mixed_behavior_load_test_result()
        if not r:
            return None
        if not isinstance(r, dict):
            return MIXED_BEHAVIOR_LOAD_TEST_DISPLAY_UNAVAILABLE_AR
        total = _safe_int(r.get("total_events"), -1)
        if total < 0:
            return MIXED_BEHAVIOR_LOAD_TEST_DISPLAY_UNAVAILABLE_AR
        success = max(0, _safe_int(r.get("success_count"), 0))
        stores = max(0, _safe_int(r.get("stores_count"), 0))
        contam = max(0, _safe_int(r.get("contamination_errors"), 0))
        life = max(0, _safe_int(r.get("lifecycle_errors"), 0))
        errors = max(0, _safe_int(r.get("error_count"), 0))
        avg_ms = _safe_float_ms(r.get("avg_duration_ms"))
        return (
            f"آخر اختبار سلوك مختلط: نجاح {success}/{total}"
            f" — متاجر {stores}"
            f" — تلوث {contam}"
            f" — أخطاء دورة حياة {life}"
            f" — أخطاء {errors}"
            f" — متوسط {avg_ms:.0f}ms"
        )
    except Exception:
        return MIXED_BEHAVIOR_LOAD_TEST_DISPLAY_UNAVAILABLE_AR


def stash_latest_mixed_behavior_load_test_result_for_tests(
    data: Optional[dict[str, Any]],
) -> None:
    global _latest_result
    with _lock:
        _latest_result = dict(data) if data else None


def clear_mixed_behavior_load_test_state_for_tests() -> None:
    global _latest_result
    with _lock:
        _latest_result = None


def run_multi_store_mixed_behavior_load_test(
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
    prof_by_slug = {p["store_slug"]: p for p in profiles}
    plan = _build_mixed_event_plan(
        run_id=run_id, profiles=profiles, events_per_store=per_store
    )

    durations_ms: list[float] = []
    success_count = 0
    error_count = 0
    error_samples: list[str] = []
    kind_counts: dict[str, int] = {}

    patches = []
    if dry_run_whatsapp:
        patches = [
            patch("services.whatsapp_send.send_whatsapp", _mock_whatsapp_send),
            patch("services.whatsapp_send.send_whatsapp_real", _mock_whatsapp_send),
            patch("services.whatsapp_queue.send_whatsapp_real", _mock_whatsapp_send),
        ]

    started_at = datetime.now(timezone.utc).isoformat()
    abandon_pool: dict[str, list[tuple[str, str]]] = {}

    try:
        for p in patches:
            p.start()
        client = TestClient(app)
        for row in plan:
            prof = prof_by_slug[row.store_slug]
            kind_counts[row.kind] = kind_counts.get(row.kind, 0) + 1
            t0 = time.perf_counter()
            try:
                status, err = _execute_mixed_row(client, row, prof, abandon_pool)
                dur = (time.perf_counter() - t0) * 1000.0
                durations_ms.append(dur)
                if 200 <= status < 300:
                    success_count += 1
                else:
                    error_count += 1
                    if err and len(error_samples) < 5:
                        error_samples.append(f"{row.store_slug}:{row.session_id}:{err}")
            except Exception as exc:  # noqa: BLE001
                dur = (time.perf_counter() - t0) * 1000.0
                durations_ms.append(dur)
                error_count += 1
                if len(error_samples) < 5:
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

    contam_errors, lifecycle_errors, verify_samples = verify_mixed_behavior(profiles, plan)

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
        "ok": (
            error_count == 0
            and pool_timeout_delta == 0
            and contam_errors == 0
            and lifecycle_errors == 0
        ),
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
        "contamination_samples": verify_samples,
        "lifecycle_errors": lifecycle_errors,
        "event_kind_counts": kind_counts,
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
