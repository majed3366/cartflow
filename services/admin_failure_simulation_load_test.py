# -*- coding: utf-8 -*-
"""
Admin failure-scenario load test — realistic edge cases via in-process TestClient.

Does not change production recovery, WhatsApp, widget, or DB foundation.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional
from unittest.mock import patch

from services.admin_cart_event_load_test import (
    _mock_whatsapp_send,
    _safe_float_ms,
    _safe_int,
)
from services.admin_multi_store_load_test import provision_virtual_loadtest_stores

FAILURE_SIMULATION_DISPLAY_UNAVAILABLE_AR = (
    "آخر محاكاة أعطال: غير متاح مؤقتاً"
)

_SLOW_DB_SLEEP_MS = 45.0
_TEST_PHONE = "9665444555666"
_STORE_A = "loadtest-store-001"
_STORE_B = "loadtest-store-002"
_UNKNOWN_STORE = "failtest-unknown-store-999"

_lock = threading.Lock()
_latest_result: Optional[dict[str, Any]] = None


@dataclass
class _ScenarioOutcome:
    scenario_id: str
    label_ar: str
    handled: bool
    crashed: bool
    http_status: int
    detail: str
    duration_ms: float


def _post_reason(client: Any, store: str, session_id: str, *, phone: bool = True) -> int:
    body: dict[str, Any] = {
        "store_slug": store,
        "session_id": session_id,
        "reason_tag": "price_high",
    }
    if phone:
        body["customer_phone"] = _TEST_PHONE
    return int(client.post("/api/cart-recovery/reason", json=body).status_code)


def _abandon_payload(
    store: str,
    session_id: str,
    cart_id: str,
    *,
    phone: bool = True,
    reason_in_payload: bool = True,
    cart_total: float = 50.0,
) -> dict[str, Any]:
    p: dict[str, Any] = {
        "event": "cart_abandoned",
        "store": store,
        "session_id": session_id,
        "cart_id": cart_id,
        "cart": [{"name": "Fail sim item", "price": cart_total, "quantity": 1}],
        "cart_total": cart_total,
    }
    if reason_in_payload:
        p["reason"] = "price"
    if phone:
        p["phone"] = _TEST_PHONE
    return p


def _run_scenario(
    fn: Callable[[], tuple[bool, int, str]],
) -> _ScenarioOutcome:
    scenario_id = getattr(fn, "__scenario_id__", "unknown")
    label_ar = getattr(fn, "__label_ar__", scenario_id)
    t0 = time.perf_counter()
    try:
        handled, status, detail = fn()
        dur = (time.perf_counter() - t0) * 1000.0
        return _ScenarioOutcome(
            scenario_id=scenario_id,
            label_ar=label_ar,
            handled=handled,
            crashed=False,
            http_status=status,
            detail=detail[:200],
            duration_ms=dur,
        )
    except Exception as exc:  # noqa: BLE001
        dur = (time.perf_counter() - t0) * 1000.0
        return _ScenarioOutcome(
            scenario_id=scenario_id,
            label_ar=label_ar,
            handled=False,
            crashed=True,
            http_status=500,
            detail=str(exc)[:200],
            duration_ms=dur,
        )


def _verify_session_conflict_clean(session_id: str) -> tuple[int, list[str]]:
    from extensions import db
    from models import CartRecoveryReason

    errors = 0
    samples: list[str] = []
    rows = (
        db.session.query(CartRecoveryReason)
        .filter(CartRecoveryReason.session_id == session_id)
        .all()
    )
    allowed = {_STORE_A, _STORE_B}
    per_store: dict[str, int] = {}
    for row in rows:
        slug = str(row.store_slug or "").strip()
        if slug not in allowed:
            errors += 1
            if len(samples) < 3:
                samples.append(f"crr_unexpected_store:{slug}")
            continue
        per_store[slug] = per_store.get(slug, 0) + 1
    if per_store.get(_STORE_A, 0) < 1 or per_store.get(_STORE_B, 0) < 1:
        errors += 1
        samples.append(f"crr_missing_store_partition:{per_store}")
    return errors, samples


def get_latest_failure_simulation_result() -> Optional[dict[str, Any]]:
    with _lock:
        return dict(_latest_result) if _latest_result else None


def get_latest_failure_simulation_display_ar() -> Optional[str]:
    try:
        r = get_latest_failure_simulation_result()
        if not r:
            return None
        if not isinstance(r, dict):
            return FAILURE_SIMULATION_DISPLAY_UNAVAILABLE_AR
        total = _safe_int(r.get("scenarios_total"), -1)
        if total < 0:
            return FAILURE_SIMULATION_DISPLAY_UNAVAILABLE_AR
        handled = max(0, _safe_int(r.get("failure_handled_count"), 0))
        crashes = max(0, _safe_int(r.get("unexpected_crash_count"), 0))
        contam = max(0, _safe_int(r.get("contamination_errors"), 0))
        life = max(0, _safe_int(r.get("lifecycle_errors"), 0))
        avg_ms = _safe_float_ms(r.get("avg_duration_ms"))
        return (
            f"آخر محاكاة أعطال: معالجة {handled}/{total}"
            f" — تعطل غير متوقع {crashes}"
            f" — تلوث {contam}"
            f" — أخطاء دورة حياة {life}"
            f" — متوسط {avg_ms:.0f}ms"
        )
    except Exception:
        return FAILURE_SIMULATION_DISPLAY_UNAVAILABLE_AR


def stash_latest_failure_simulation_result_for_tests(
    data: Optional[dict[str, Any]],
) -> None:
    global _latest_result
    with _lock:
        _latest_result = dict(data) if data else None


def clear_failure_simulation_state_for_tests() -> None:
    global _latest_result
    with _lock:
        _latest_result = None


def run_failure_scenarios_load_test(*, dry_run_whatsapp: bool = True) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    import main as main_mod

    from extensions import db, remove_scoped_session
    from main import (
        _is_user_converted,
        _is_user_returned,
        _load_store_row_for_recovery,
        _recovery_key_from_payload,
        _test_set_recovery_flow_armed_at,
        app,
    )
    from models import Store
    from services.admin_operational_health import (
        get_db_pool_snapshot_readonly,
        get_operational_counter_snapshots,
    )

    run_id = uuid.uuid4().hex[:8]
    counters_before = get_operational_counter_snapshots()
    pool_before = get_db_pool_snapshot_readonly()

    provision_virtual_loadtest_stores(2)
    row_a = db.session.query(Store).filter(Store.zid_store_id == _STORE_A).first()
    if row_a is not None:
        row_a.vip_cart_threshold = None
        db.session.commit()

    outcomes: list[_ScenarioOutcome] = []
    contamination_errors = 0
    contamination_samples: list[str] = []
    lifecycle_errors = 0

    patches: list[Any] = []
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

        def scenario_missing_phone() -> tuple[bool, int, str]:
            sid = f"failsim-{run_id}-no-phone"
            cid = f"cart-{run_id}-no-phone"
            st = _post_reason(client, _STORE_A, sid, phone=False)
            r = client.post(
                "/api/cart-event",
                json=_abandon_payload(_STORE_A, sid, cid, phone=False),
            )
            body = r.json() if r.status_code == 200 else {}
            ok = (
                r.status_code == 200
                and not body.get("recovery_scheduled", True)
                and str(body.get("recovery_state") or "") == "waiting_for_phone"
            )
            return ok, r.status_code, f"reason_post={st} state={body.get('recovery_state')}"

        scenario_missing_phone.__scenario_id__ = "missing_phone"
        scenario_missing_phone.__label_ar__ = "بدون رقم هاتف"

        def scenario_missing_reason() -> tuple[bool, int, str]:
            sid = f"failsim-{run_id}-no-reason"
            cid = f"cart-{run_id}-no-reason"
            r = client.post(
                "/api/cart-event",
                json=_abandon_payload(
                    _STORE_A, sid, cid, phone=True, reason_in_payload=False
                ),
            )
            body = r.json() if r.status_code == 200 else {}
            ok = r.status_code == 200 and str(body.get("recovery_state") or "") == (
                "waiting_for_reason"
            )
            return ok, r.status_code, str(body.get("recovery_state") or "")

        scenario_missing_reason.__scenario_id__ = "missing_reason_tag"
        scenario_missing_reason.__label_ar__ = "بدون سبب"

        def scenario_duplicate_event() -> tuple[bool, int, str]:
            sid = f"failsim-{run_id}-dup"
            cid = f"cart-{run_id}-dup"
            body = _abandon_payload(_STORE_A, sid, cid)
            _post_reason(client, _STORE_A, sid)
            with (
                patch("main.get_recovery_delay", return_value=0),
                patch("main.recovery_uses_real_whatsapp", return_value=False),
                patch("main.send_whatsapp", return_value={"ok": True, "status": "mock_sent"}),
            ):
                r1 = client.post("/api/cart-event", json=body)
                r2 = client.post("/api/cart-event", json=body)
            b2 = r2.json() if r2.status_code == 200 else {}
            ok = (
                r1.status_code == 200
                and r2.status_code == 200
                and b2.get("recovery_state") in ("skipped_duplicate", "sent")
            )
            return ok, r2.status_code, str(b2.get("recovery_state") or "")

        scenario_duplicate_event.__scenario_id__ = "duplicate_event"
        scenario_duplicate_event.__label_ar__ = "حدث مكرر"

        def scenario_purchase_during_delay() -> tuple[bool, int, str]:
            sid = f"failsim-{run_id}-purchase"
            cid = f"cart-{run_id}-purchase"
            _post_reason(client, _STORE_A, sid)
            abandon = _abandon_payload(_STORE_A, sid, cid)
            with patch("main.get_recovery_delay", return_value=60):
                client.post("/api/cart-event", json=abandon)
            key = _recovery_key_from_payload(
                {"store": _STORE_A, "session_id": sid, "cart_id": cid}
            )
            _test_set_recovery_flow_armed_at(
                key, datetime.now(timezone.utc) - timedelta(seconds=120)
            )
            conv = client.post(
                "/api/conversion",
                json={
                    "store_slug": _STORE_A,
                    "session_id": sid,
                    "purchase_completed": True,
                },
            )
            ok = conv.status_code == 200 and _is_user_converted(key)
            return ok, conv.status_code, f"converted={_is_user_converted(key)}"

        scenario_purchase_during_delay.__scenario_id__ = "purchase_during_delay"
        scenario_purchase_during_delay.__label_ar__ = "شراء أثناء التأخير"

        def scenario_return_during_delay() -> tuple[bool, int, str]:
            sid = f"failsim-{run_id}-return"
            cid = f"cart-{run_id}-return"
            _post_reason(client, _STORE_A, sid)
            abandon = _abandon_payload(_STORE_A, sid, cid)
            with patch("main.get_recovery_delay", return_value=60):
                client.post("/api/cart-event", json=abandon)
            key = _recovery_key_from_payload(
                {"store": _STORE_A, "session_id": sid, "cart_id": cid}
            )
            _test_set_recovery_flow_armed_at(
                key, datetime.now(timezone.utc) - timedelta(seconds=120)
            )
            with main_mod._recovery_session_lock:
                main_mod._session_recovery_delay_wait_started_at.pop(key, None)
            ret = client.post(
                "/api/cart-event",
                json={
                    "store": _STORE_A,
                    "session_id": sid,
                    "cart_id": cid,
                    "passive_return_visit": True,
                    "return_visit_kind": "passive_return_visit",
                    "recovery_return_context": "page",
                },
            )
            ok = ret.status_code == 200
            return ok, ret.status_code, f"returned={_is_user_returned(key)}"

        scenario_return_during_delay.__scenario_id__ = "return_during_delay"
        scenario_return_during_delay.__label_ar__ = "عودة أثناء التأخير"

        def scenario_store_config_missing() -> tuple[bool, int, str]:
            sid = f"failsim-{run_id}-nostore"
            r = client.post(
                "/api/cart-event",
                json=_abandon_payload(_UNKNOWN_STORE, sid, f"cart-{run_id}-nostore"),
            )
            ok = 200 <= r.status_code < 500
            return ok, r.status_code, "no_server_error"

        scenario_store_config_missing.__scenario_id__ = "store_config_missing"
        scenario_store_config_missing.__label_ar__ = "متجر غير معرّف"

        def scenario_vip_threshold_missing() -> tuple[bool, int, str]:
            sid = f"failsim-{run_id}-novipth"
            cid = f"cart-{run_id}-novipth"
            r = client.post(
                "/api/cart-event",
                json=_abandon_payload(
                    _STORE_A, sid, cid, cart_total=5000.0, reason_in_payload=True
                ),
            )
            body = r.json() if r.status_code == 200 else {}
            ok = r.status_code == 200 and not bool(body.get("recovery_vip_manual"))
            return ok, r.status_code, f"vip_manual={body.get('recovery_vip_manual')}"

        scenario_vip_threshold_missing.__scenario_id__ = "vip_threshold_missing"
        scenario_vip_threshold_missing.__label_ar__ = "بدون عتبة VIP"

        def scenario_whatsapp_provider_failure() -> tuple[bool, int, str]:
            sid = f"failsim-{run_id}-wafail"
            cid = f"cart-{run_id}-wafail"
            _post_reason(client, _STORE_A, sid)
            body = _abandon_payload(_STORE_A, sid, cid)
            fail_send = lambda *_a, **_k: {"ok": False, "status": "provider_error"}

            with (
                patch("main.get_recovery_delay", return_value=0),
                patch("main.recovery_uses_real_whatsapp", return_value=True),
                patch("main.send_whatsapp", side_effect=fail_send),
            ):
                r = client.post("/api/cart-event", json=body)
            ok = r.status_code == 200
            return ok, r.status_code, "survived_provider_fail"

        scenario_whatsapp_provider_failure.__scenario_id__ = "whatsapp_provider_failure"
        scenario_whatsapp_provider_failure.__label_ar__ = "فشل مزود واتساب (وهمي)"

        def scenario_slow_db_bounded() -> tuple[bool, int, str]:
            sid = f"failsim-{run_id}-slowdb"
            cid = f"cart-{run_id}-slowdb"
            real_load = _load_store_row_for_recovery

            def slow_load(store_slug: Optional[str] = None, **kwargs: Any) -> Any:
                time.sleep(_SLOW_DB_SLEEP_MS / 1000.0)
                return real_load(store_slug, **kwargs)

            with patch("main._load_store_row_for_recovery", side_effect=slow_load):
                r = client.post(
                    "/api/cart-event",
                    json=_abandon_payload(_STORE_A, sid, cid, reason_in_payload=False),
                )
            ok = r.status_code == 200
            return ok, r.status_code, f"slow_ms~{_SLOW_DB_SLEEP_MS}"

        scenario_slow_db_bounded.__scenario_id__ = "slow_db_simulation"
        scenario_slow_db_bounded.__label_ar__ = "بطء DB محدود"

        def scenario_session_conflict() -> tuple[bool, int, str]:
            sid = f"failsim-{run_id}-conflict"
            cid_a = f"cart-{run_id}-conflict-a"
            cid_b = f"cart-{run_id}-conflict-b"
            _post_reason(client, _STORE_A, sid)
            _post_reason(client, _STORE_B, sid)
            r1 = client.post(
                "/api/cart-event",
                json=_abandon_payload(_STORE_A, sid, cid_a),
            )
            r2 = client.post(
                "/api/cart-event",
                json=_abandon_payload(_STORE_B, sid, cid_b),
            )
            ce, cs = _verify_session_conflict_clean(sid)
            nonlocal contamination_errors, contamination_samples
            contamination_errors += ce
            contamination_samples.extend(cs)
            ok = r1.status_code == 200 and r2.status_code == 200 and ce == 0
            return ok, min(r1.status_code, r2.status_code), f"contam={ce}"

        scenario_session_conflict.__scenario_id__ = "session_conflict"
        scenario_session_conflict.__label_ar__ = "تعارض جلسة بين متجرين"

        scenario_fns = [
            scenario_missing_phone,
            scenario_missing_reason,
            scenario_duplicate_event,
            scenario_purchase_during_delay,
            scenario_return_during_delay,
            scenario_store_config_missing,
            scenario_vip_threshold_missing,
            scenario_whatsapp_provider_failure,
            scenario_slow_db_bounded,
            scenario_session_conflict,
        ]

        for fn in scenario_fns:
            outcomes.append(_run_scenario(fn))
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

    failure_handled = sum(1 for o in outcomes if o.handled and not o.crashed)
    unexpected_crash = sum(1 for o in outcomes if o.crashed)
    durations = [o.duration_ms for o in outcomes]
    avg_ms = sum(durations) / len(durations) if durations else 0.0
    max_ms = max(durations) if durations else 0.0

    summary: dict[str, Any] = {
        "ok": unexpected_crash == 0 and contamination_errors == 0 and lifecycle_errors == 0,
        "run_id": run_id,
        "scenarios_total": len(outcomes),
        "failure_handled_count": failure_handled,
        "unexpected_crash_count": unexpected_crash,
        "contamination_errors": contamination_errors,
        "contamination_samples": contamination_samples[:5],
        "lifecycle_errors": lifecycle_errors,
        "queuepool_timeout_count": pool_timeout_delta,
        "background_task_failures": bg_fail_delta,
        "avg_duration_ms": round(avg_ms, 1),
        "max_duration_ms": round(max_ms, 1),
        "dry_run_whatsapp": bool(dry_run_whatsapp),
        "scenario_results": [
            {
                "scenario_id": o.scenario_id,
                "label_ar": o.label_ar,
                "handled": o.handled,
                "crashed": o.crashed,
                "http_status": o.http_status,
                "detail": o.detail,
                "duration_ms": round(o.duration_ms, 1),
            }
            for o in outcomes
        ],
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "db_pool_before": pool_before,
        "db_pool_after": pool_after,
    }

    global _latest_result
    with _lock:
        _latest_result = dict(summary)

    return summary
