# -*- coding: utf-8 -*-
"""
Demo Commerce Lab V1 — Scenario 1 runner (P2).

Deterministic Visit → … → Purchase on store_slug=demo only.
Always Lab-Resets first. No UI. No new tables. No new Signal families.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import (
    AbandonedCart,
    PurchaseTruthRecord,
    RecoverySchedule,
    RecoveryTruthTimelineEvent,
    Store,
)
from services.cf_test_phone_override import normalize_cf_test_customer_phone
from services.commerce_signals_v1 import (
    SIGNAL_PURCHASE_CONFIRMED,
    SIGNAL_RECOVERY_COMPLETED,
    SIGNAL_RECOVERY_STARTED,
    load_commerce_signals_for_recovery_key,
    load_store_commerce_signals_v1,
)
from services.commerce_signals_v1_flag import ENV_COMMERCE_SIGNALS_V1
from services.customer_movement_snapshot_v1 import diagnose_movement_snapshot
from services.demo_lab_reset_v1 import (
    LAB_CART_ID,
    LAB_CUSTOMER_PHONE,
    LAB_RECOVERY_KEY,
    LAB_SESSION_ID,
    LAB_STORE_SLUG,
    lab_baseline_identity,
    lab_reset_v1,
    validate_lab_reset_scope,
)
from services.demo_sandbox_catalog import (
    SANDBOX_PRODUCTS,
    SANDBOX_PRODUCT_NUM_BY_KEY,
    merchant_catalog_json_string,
)
from services.merchant_pulse_v1 import (
    FORK_LEAVE,
    STATUS_REQUIRE_ACTION,
    build_merchant_pulse_v1_from_summary,
)
from services.purchase_lifecycle_closure import is_purchase_lifecycle_closed
from services.recovery_truth_timeline_v1 import get_recovery_truth_timeline

log = logging.getLogger("cartflow")

SCENARIO_ID = "lab_v1_recovery_to_purchase"
LAB_PRODUCT_KEY = "hp_pro"
LAB_PRODUCT_PRICE = 449.0
LAB_PRODUCT_NUM = int(SANDBOX_PRODUCT_NUM_BY_KEY[LAB_PRODUCT_KEY])
LAB_PRODUCT_PATH = f"/demo/store/product/{LAB_PRODUCT_NUM}"
LAB_REASON = "price"
LAB_REASON_SUB = "price_discount_request"

_ERROR_REJECTED = "lab_scenario1_rejected"


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _reject(reason: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": False,
        "pass": False,
        "error": _ERROR_REJECTED,
        "reject_reason": reason,
        "scenario_id": SCENARIO_ID,
        "store_slug": LAB_STORE_SLUG,
    }
    out.update(extra)
    return out


def validate_lab_scenario1_scope(
    *,
    store_slug: str,
    merchant_activation: bool = False,
) -> Optional[dict[str, Any]]:
    """Hard gates — no writes when this returns a reject payload."""
    gate = validate_lab_reset_scope(
        store_slug=store_slug,
        merchant_activation=merchant_activation,
    )
    if gate is None:
        return None
    # Re-tag as scenario reject while preserving reason.
    return _reject(
        str(gate.get("reject_reason") or "lab_reset_rejected"),
        requested_store_slug=gate.get("requested_store_slug"),
    )


def _price_templates_json() -> str:
    return json.dumps(
        {
            "price": {
                "enabled": True,
                "message": "رسالة 1",
                "message_count": 3,
                "messages": [
                    {"delay": 0, "unit": "minutes", "text": "رسالة 1"},
                    {"delay": 1, "unit": "minutes", "text": "رسالة 2"},
                    {"delay": 2, "unit": "minutes", "text": "رسالة 3"},
                ],
            }
        }
    )


def _hp_pro_line() -> dict[str, Any]:
    prod = SANDBOX_PRODUCTS[LAB_PRODUCT_KEY]
    return {
        "id": LAB_PRODUCT_KEY,
        "sku": LAB_PRODUCT_KEY,
        "name": prod.get("name") or "TrueSound Pro",
        "price": LAB_PRODUCT_PRICE,
        "unit_price": LAB_PRODUCT_PRICE,
        "quantity": 1,
        "category": prod.get("category") or "",
    }


def _prepare_demo_store_for_lab() -> dict[str, Any]:
    """
    Ensure demo Store exists with Lab-ready timing + catalog preserved/seeded.
    Never deletes the Store row. Never touches non-demo stores.
    """
    st = db.session.query(Store).filter(Store.zid_store_id == LAB_STORE_SLUG).first()
    created = False
    if st is None:
        st = Store(zid_store_id=LAB_STORE_SLUG)
        db.session.add(st)
        db.session.flush()
        created = True

    catalog_before = str(getattr(st, "cf_product_catalog_json", None) or "")
    if not catalog_before.strip():
        st.cf_product_catalog_json = merchant_catalog_json_string()

    st.recovery_delay = 0
    st.recovery_delay_unit = "minutes"
    st.recovery_attempts = int(getattr(st, "recovery_attempts", None) or 3)
    st.reason_templates_json = _price_templates_json()
    # Prefer sandbox path without live provider sends during Lab.
    if getattr(st, "whatsapp_recovery_enabled", None) is None:
        st.whatsapp_recovery_enabled = False

    db.session.commit()
    catalog_after = str(getattr(st, "cf_product_catalog_json", None) or "")
    return {
        "store_created": created,
        "catalog_present": bool(catalog_after.strip()),
        "catalog_seeded": not bool(catalog_before.strip()) and bool(catalog_after.strip()),
        "recovery_delay": 0,
    }


def _step(
    name: str,
    *,
    ok: bool,
    truth: Optional[dict[str, Any]] = None,
    timeline: Optional[list[Any]] = None,
    movement: Optional[dict[str, Any]] = None,
    signals: Optional[list[Any]] = None,
    cart_state: Optional[dict[str, Any]] = None,
    detail: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "step": name,
        "ok": bool(ok),
        "error": error,
        "truth": truth or {},
        "timeline_events": list(timeline or []),
        "movement_snapshot": movement or {},
        "signals": list(signals or []),
        "cart_state": cart_state or {},
        "detail": detail or {},
    }


def _lab_phone(cf_test_phone: str = "") -> str:
    raw = (cf_test_phone or "").strip() or LAB_CUSTOMER_PHONE
    return normalize_cf_test_customer_phone(raw) or raw


def _capture_timeline() -> list[dict[str, Any]]:
    try:
        return list(get_recovery_truth_timeline(LAB_RECOVERY_KEY) or [])
    except Exception:  # noqa: BLE001
        return []


def _capture_movement() -> dict[str, Any]:
    try:
        return dict(diagnose_movement_snapshot(LAB_RECOVERY_KEY) or {})
    except Exception:  # noqa: BLE001
        return {}


def _capture_signals(*, force: bool = True) -> list[dict[str, Any]]:
    loaded = load_commerce_signals_for_recovery_key(
        store_slug=LAB_STORE_SLUG,
        recovery_key=LAB_RECOVERY_KEY,
        force=force,
    )
    return list(loaded.get("signals") or [])


def _capture_cart_state(*, phone: str) -> dict[str, Any]:
    st = db.session.query(Store).filter(Store.zid_store_id == LAB_STORE_SLUG).first()
    ac = None
    if st is not None:
        ac = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.zid_cart_id == LAB_CART_ID)
            .first()
        )
        if ac is None:
            ac = (
                db.session.query(AbandonedCart)
                .filter(
                    AbandonedCart.store_id == int(st.id),
                    AbandonedCart.recovery_session_id == LAB_SESSION_ID,
                )
                .first()
            )
    purchase = (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.recovery_key == LAB_RECOVERY_KEY)
        .first()
    )
    status = _norm(getattr(ac, "status", None)).lower() if ac is not None else ""
    cart_value = None
    if ac is not None and getattr(ac, "cart_value", None) is not None:
        try:
            cart_value = float(ac.cart_value)
        except (TypeError, ValueError):
            cart_value = None
    closed = False
    try:
        closed = bool(is_purchase_lifecycle_closed(LAB_RECOVERY_KEY))
    except Exception:  # noqa: BLE001
        closed = False
    return {
        "abandoned_cart_present": ac is not None,
        "status": status or None,
        "cart_value": cart_value,
        "amount_sar": cart_value,
        "session_id": _norm(getattr(ac, "recovery_session_id", None)) or LAB_SESSION_ID,
        "cart_id": _norm(getattr(ac, "zid_cart_id", None)) or LAB_CART_ID,
        "customer_phone": _norm(getattr(ac, "customer_phone", None)) or phone,
        "purchase_detected": bool(
            purchase is not None and bool(getattr(purchase, "purchase_detected", False))
        ),
        "lifecycle_closed_purchase": closed,
        "completed": status == "recovered" or closed or (
            purchase is not None and bool(getattr(purchase, "purchase_detected", False))
        ),
    }


def _signal_types(signals: list[dict[str, Any]]) -> list[str]:
    return [_norm(s.get("signal_type")) for s in signals if isinstance(s, dict)]


def _count_signal_type(signals: list[dict[str, Any]], signal_type: str) -> int:
    st = _norm(signal_type)
    return sum(1 for s in signals if isinstance(s, dict) and _norm(s.get("signal_type")) == st)


def _build_pulse_payload(*, force_signals: bool = True) -> dict[str, Any]:
    store_signals = load_store_commerce_signals_v1(
        store_slug=LAB_STORE_SLUG,
        force=force_signals,
        recovery_keys=[LAB_RECOVERY_KEY],
    )
    body: dict[str, Any] = {
        "ok": True,
        "store_slug": LAB_STORE_SLUG,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "commerce_signals_v1": store_signals,
        "merchant_home_experience_v1": {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "empty_calm": False,
            "while_away": {"items": [], "empty_message_ar": "—"},
            "attention_today": {
                "items": [],
                "empty_message_ar": "لا أمور تتطلب انتباهك الآن.",
            },
        },
        "whatsapp_readiness_card": {
            "readiness_overall": "ready",
            "connection_state": "connected",
        },
        "store_connection": {"ok": True, "connected": True},
    }
    return build_merchant_pulse_v1_from_summary(body, store_slug=LAB_STORE_SLUG)


def _cross_store_leak_check() -> dict[str, Any]:
    """Confirm Lab identity rows are only under demo."""
    bad_purchase = (
        db.session.query(PurchaseTruthRecord)
        .filter(
            PurchaseTruthRecord.recovery_key == LAB_RECOVERY_KEY,
            PurchaseTruthRecord.store_slug != LAB_STORE_SLUG,
        )
        .count()
    )
    bad_timeline = (
        db.session.query(RecoveryTruthTimelineEvent)
        .filter(
            RecoveryTruthTimelineEvent.recovery_key == LAB_RECOVERY_KEY,
            RecoveryTruthTimelineEvent.store_slug != LAB_STORE_SLUG,
        )
        .count()
    )
    bad_sched = (
        db.session.query(RecoverySchedule)
        .filter(
            RecoverySchedule.recovery_key == LAB_RECOVERY_KEY,
            RecoverySchedule.store_slug != LAB_STORE_SLUG,
        )
        .count()
    )
    return {
        "ok": bad_purchase == 0 and bad_timeline == 0 and bad_sched == 0,
        "non_demo_purchase_rows": int(bad_purchase),
        "non_demo_timeline_rows": int(bad_timeline),
        "non_demo_schedule_rows": int(bad_sched),
    }


def _final_assertions(
    *,
    phone: str,
    signals: list[dict[str, Any]],
    pulse: dict[str, Any],
    cart_state: dict[str, Any],
) -> dict[str, Any]:
    purchase_n = _count_signal_type(signals, SIGNAL_PURCHASE_CONFIRMED)
    completed_n = _count_signal_type(signals, SIGNAL_RECOVERY_COMPLETED)
    started_n = _count_signal_type(signals, SIGNAL_RECOVERY_STARTED)
    amount = cart_state.get("cart_value")
    try:
        amount_f = float(amount) if amount is not None else None
    except (TypeError, ValueError):
        amount_f = None

    fork = _norm(pulse.get("fork"))
    decision_status = _norm((pulse.get("decision_summary") or {}).get("status"))
    merchant_decision_status = _norm((pulse.get("merchant_decision") or {}).get("status"))
    signals_used = bool((pulse.get("sources") or {}).get("commerce_signals_used"))
    progress_msg = _norm((pulse.get("cartflow_progress") or {}).get("message"))
    brief_msg = _norm((pulse.get("executive_brief") or {}).get("message"))
    recovered_language = ("استرجاع" in progress_msg + brief_msg) or (
        "شراء" in progress_msg + brief_msg
    )

    checks = {
        "A1_purchase_confirmed_exists": purchase_n >= 1,
        "A2_recovery_completed_exists": completed_n >= 1,
        "A3_exactly_one_purchase_signal": purchase_n == 1,
        "A4_exactly_one_recovery_completed_signal": completed_n == 1,
        "A5_amount_449": amount_f == LAB_PRODUCT_PRICE,
        "A6_cart_completed": bool(cart_state.get("completed")),
        "A7_no_merchant_require_action": (
            fork == FORK_LEAVE
            and decision_status != STATUS_REQUIRE_ACTION
            and merchant_decision_status != STATUS_REQUIRE_ACTION
        ),
        "A8_pulse_consumes_signals": signals_used,
        "A9_pulse_recovered_purchase_449": (
            signals_used
            and recovered_language
            and purchase_n == 1
            and completed_n == 1
            and amount_f == LAB_PRODUCT_PRICE
        ),
        "A10_no_duplicate_started_signal": started_n <= 1,
        "A11_no_cross_store_leak": bool(_cross_store_leak_check().get("ok")),
        "A12_lifecycle_closed_or_recovered": bool(
            cart_state.get("lifecycle_closed_purchase")
            or _norm(cart_state.get("status")) == "recovered"
            or cart_state.get("purchase_detected")
        ),
    }
    failed = [k for k, v in checks.items() if not v]
    return {
        "ok": len(failed) == 0,
        "checks": checks,
        "failed": failed,
        "signal_counts": {
            SIGNAL_PURCHASE_CONFIRMED: purchase_n,
            SIGNAL_RECOVERY_COMPLETED: completed_n,
            SIGNAL_RECOVERY_STARTED: started_n,
        },
        "recovered_purchase": {
            "count": purchase_n,
            "amount_sar": amount_f,
            "product_key": LAB_PRODUCT_KEY,
        },
        "phone": phone,
    }


def run_lab_scenario1_v1(
    *,
    store_slug: str = LAB_STORE_SLUG,
    cf_test_phone: str = "",
    merchant_activation: bool = False,
    client: Any = None,
    http_get: Optional[Callable[..., Any]] = None,
    http_post: Optional[Callable[..., Any]] = None,
) -> dict[str, Any]:
    """
    Authoritative Scenario 1 runner.

    Always calls lab_reset_v1(store_slug=\"demo\") first.
    Uses production HTTP paths via TestClient (or injected http_get/http_post).
    """
    gate = validate_lab_scenario1_scope(
        store_slug=store_slug,
        merchant_activation=merchant_activation,
    )
    if gate is not None:
        return gate

    phone = _lab_phone(cf_test_phone)
    if not phone:
        return _reject("cf_test_phone_required")

    identity = lab_baseline_identity()
    steps: list[dict[str, Any]] = []

    # --- HTTP helpers ---
    if client is None and (http_get is None or http_post is None):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)

    def _get(path: str, **kwargs: Any) -> Any:
        if http_get is not None:
            return http_get(path, **kwargs)
        return client.get(path, **kwargs)

    def _post(path: str, **kwargs: Any) -> Any:
        if http_post is not None:
            return http_post(path, **kwargs)
        return client.post(path, **kwargs)

    prev_signals_flag = os.environ.get(ENV_COMMERCE_SIGNALS_V1)
    os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"

    try:
        # ---- Step 0: Lab Reset ----
        reset_out = lab_reset_v1(
            store_slug=LAB_STORE_SLUG,
            cf_test_phone=phone,
            merchant_activation=False,
        )
        if not reset_out.get("ok"):
            return {
                "ok": False,
                "pass": False,
                "error": "lab_reset_failed",
                "scenario_id": SCENARIO_ID,
                "reset": reset_out,
                "steps": [],
            }

        try:
            store_prep = _prepare_demo_store_for_lab()
        except (SQLAlchemyError, OSError, TypeError, ValueError) as exc:
            return {
                "ok": False,
                "pass": False,
                "error": "lab_store_prepare_failed",
                "detail": str(exc)[:240],
                "scenario_id": SCENARIO_ID,
                "reset": reset_out,
                "steps": [],
            }

        steps.append(
            _step(
                "0_reset",
                ok=True,
                truth={"baseline_clean": bool((reset_out.get("baseline") or {}).get("clean"))},
                signals=_capture_signals(),
                cart_state=_capture_cart_state(phone=phone),
                detail={"reset": reset_out.get("fingerprint"), "store_prep": store_prep},
            )
        )

        # ---- Step 1: Visit ----
        visit_url = (
            f"/demo/store?store_slug={LAB_STORE_SLUG}&cf_test_phone={phone}"
        )
        r_visit = _get(visit_url)
        visit_ok = int(getattr(r_visit, "status_code", 0) or 0) == 200
        steps.append(
            _step(
                "1_visit",
                ok=visit_ok,
                truth={"http_status": getattr(r_visit, "status_code", None)},
                timeline=_capture_timeline(),
                movement=_capture_movement(),
                signals=_capture_signals(),
                cart_state=_capture_cart_state(phone=phone),
                detail={"url": visit_url, "identity": identity},
                error=None if visit_ok else "visit_http_failed",
            )
        )
        if not visit_ok:
            return _fail_report(steps, identity, phone, reset_out)

        # ---- Step 2: Product view ----
        pdp_url = (
            f"{LAB_PRODUCT_PATH}?store_slug={LAB_STORE_SLUG}&cf_test_phone={phone}"
        )
        r_pdp = _get(pdp_url)
        pdp_ok = int(getattr(r_pdp, "status_code", 0) or 0) == 200
        pdp_text = ""
        try:
            pdp_text = str(getattr(r_pdp, "text", "") or "")
        except Exception:  # noqa: BLE001
            pdp_text = ""
        price_visible = "449" in pdp_text
        steps.append(
            _step(
                "2_product_view",
                ok=pdp_ok and price_visible,
                truth={
                    "http_status": getattr(r_pdp, "status_code", None),
                    "product_key": LAB_PRODUCT_KEY,
                    "price_sar": LAB_PRODUCT_PRICE,
                    "price_visible_in_html": price_visible,
                },
                timeline=_capture_timeline(),
                movement=_capture_movement(),
                signals=_capture_signals(),
                cart_state=_capture_cart_state(phone=phone),
                detail={"url": pdp_url},
                error=None if (pdp_ok and price_visible) else "product_view_failed",
            )
        )
        if not (pdp_ok and price_visible):
            return _fail_report(steps, identity, phone, reset_out)

        # ---- Step 3: Add to cart (cart_state_sync) ----
        line = _hp_pro_line()
        sync_payload = {
            "event": "cart_state_sync",
            "reason": "add",
            "store": LAB_STORE_SLUG,
            "store_slug": LAB_STORE_SLUG,
            "session_id": LAB_SESSION_ID,
            "cart_id": LAB_CART_ID,
            "cart_total": LAB_PRODUCT_PRICE,
            "items_count": 1,
            "cart": [line],
            "cf_test_phone": phone,
            "customer_phone": phone,
        }
        r_sync = _post("/api/cart-event", json=sync_payload)
        sync_json = {}
        try:
            sync_json = r_sync.json() if hasattr(r_sync, "json") else {}
        except Exception:  # noqa: BLE001
            sync_json = {}
        sync_ok = int(getattr(r_sync, "status_code", 0) or 0) == 200 and bool(
            sync_json.get("cart_state_sync") or sync_json.get("ok") is not False
        )
        steps.append(
            _step(
                "3_add_to_cart",
                ok=sync_ok,
                truth={"cart_state_sync": sync_json.get("cart_state_sync"), "line": line},
                timeline=_capture_timeline(),
                movement=_capture_movement(),
                signals=_capture_signals(),
                cart_state=_capture_cart_state(phone=phone),
                detail={"http_status": getattr(r_sync, "status_code", None), "response": sync_json},
                error=None if sync_ok else "cart_state_sync_failed",
            )
        )
        if not sync_ok:
            return _fail_report(steps, identity, phone, reset_out)

        # ---- Step 4: Leave (+ reason) ----
        reason_payload = {
            "store_slug": LAB_STORE_SLUG,
            "session_id": LAB_SESSION_ID,
            "reason": LAB_REASON,
            "sub_category": LAB_REASON_SUB,
            "cart_id": LAB_CART_ID,
            "customer_phone": phone,
            "cf_test_phone": phone,
            "cart_total": LAB_PRODUCT_PRICE,
            "cart": [line],
        }
        # Patch delay to 0 for deterministic arming (store already delay=0).
        from unittest.mock import patch

        with patch("main.get_recovery_delay", return_value=0), patch(
            "main.asyncio.create_task"
        ):
            r_reason = _post("/api/cartflow/reason", json=reason_payload)
        reason_json = {}
        try:
            reason_json = r_reason.json() if hasattr(r_reason, "json") else {}
        except Exception:  # noqa: BLE001
            reason_json = {}
        reason_ok = int(getattr(r_reason, "status_code", 0) or 0) == 200 and bool(
            reason_json.get("ok")
        )
        cart_after_leave = _capture_cart_state(phone=phone)
        leave_ok = reason_ok and bool(cart_after_leave.get("abandoned_cart_present"))
        steps.append(
            _step(
                "4_leave",
                ok=leave_ok,
                truth={
                    "reason_ok": reason_ok,
                    "reason": LAB_REASON,
                    "abandoned_cart_present": cart_after_leave.get("abandoned_cart_present"),
                    "cart_value": cart_after_leave.get("cart_value"),
                },
                timeline=_capture_timeline(),
                movement=_capture_movement(),
                signals=_capture_signals(),
                cart_state=cart_after_leave,
                detail={
                    "http_status": getattr(r_reason, "status_code", None),
                    "response": reason_json,
                },
                error=None if leave_ok else "leave_reason_failed",
            )
        )
        if not leave_ok:
            return _fail_report(steps, identity, phone, reset_out)

        # ---- Step 5: Recovery starts ----
        schedules = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.recovery_key == LAB_RECOVERY_KEY)
            .all()
        )
        timeline = _capture_timeline()
        started_statuses = {
            _norm(ev.get("status")).lower()
            for ev in timeline
            if isinstance(ev, dict)
        }
        recovery_started_truth = (
            len(schedules) >= 1
            or "scheduled" in started_statuses
            or "delay_started" in started_statuses
        )
        signals_s5 = _capture_signals()
        has_started_signal = _count_signal_type(signals_s5, SIGNAL_RECOVERY_STARTED) >= 1
        s5_ok = recovery_started_truth and has_started_signal and len(schedules) >= 1
        steps.append(
            _step(
                "5_recovery_starts",
                ok=s5_ok,
                truth={
                    "schedule_count": len(schedules),
                    "timeline_statuses": sorted(started_statuses),
                    "recovery_started_signal": has_started_signal,
                },
                timeline=timeline,
                movement=_capture_movement(),
                signals=signals_s5,
                cart_state=_capture_cart_state(phone=phone),
                detail={
                    "schedule_statuses": [
                        _norm(getattr(s, "status", None)) for s in schedules
                    ]
                },
                error=None if s5_ok else "recovery_start_failed",
            )
        )
        if not s5_ok:
            return _fail_report(steps, identity, phone, reset_out)

        # ---- Step 6: Customer returns ----
        r_return_page = _get(visit_url)
        return_payload = {
            "event_type": "user_returned_to_site",
            "event": "user_returned_to_site",
            "store_slug": LAB_STORE_SLUG,
            "store": LAB_STORE_SLUG,
            "session_id": LAB_SESSION_ID,
            "cart_id": LAB_CART_ID,
            "recovery_return_context": "page",
            "return_context": "page",
            "return_visit_kind": "passive_return_visit",
            "passive_return_visit": True,
            "cf_test_phone": phone,
            "customer_phone": phone,
        }
        r_return = _post("/api/cart-event", json=return_payload)
        return_http_ok = int(getattr(r_return_page, "status_code", 0) or 0) == 200 and int(
            getattr(r_return, "status_code", 0) or 0
        ) == 200
        movement = _capture_movement()
        steps.append(
            _step(
                "6_customer_returns",
                ok=return_http_ok,
                truth={"return_posted": return_http_ok},
                timeline=_capture_timeline(),
                movement=movement,
                signals=_capture_signals(),
                cart_state=_capture_cart_state(phone=phone),
                detail={
                    "page_status": getattr(r_return_page, "status_code", None),
                    "event_status": getattr(r_return, "status_code", None),
                },
                error=None if return_http_ok else "return_failed",
            )
        )
        if not return_http_ok:
            return _fail_report(steps, identity, phone, reset_out)

        # ---- Step 7: Purchase confirmed ----
        conversion_payload = {
            "store_slug": LAB_STORE_SLUG,
            "session_id": LAB_SESSION_ID,
            "cart_id": LAB_CART_ID,
            "purchase_completed": True,
            "customer_phone": phone,
            "cf_test_phone": phone,
            "cart_total": LAB_PRODUCT_PRICE,
            "cart": [line],
        }
        r_conv = _post("/api/conversion", json=conversion_payload)
        conv_json = {}
        try:
            conv_json = r_conv.json() if hasattr(r_conv, "json") else {}
        except Exception:  # noqa: BLE001
            conv_json = {}
        conv_ok = int(getattr(r_conv, "status_code", 0) or 0) == 200 and bool(
            conv_json.get("ok")
        )
        cart_final = _capture_cart_state(phone=phone)
        signals_final = _capture_signals()
        purchase_sig_ok = _count_signal_type(signals_final, SIGNAL_PURCHASE_CONFIRMED) == 1
        completed_sig_ok = _count_signal_type(signals_final, SIGNAL_RECOVERY_COMPLETED) == 1
        s7_ok = (
            conv_ok
            and bool(cart_final.get("purchase_detected"))
            and purchase_sig_ok
            and completed_sig_ok
        )
        steps.append(
            _step(
                "7_purchase_confirmed",
                ok=s7_ok,
                truth={
                    "conversion_ok": conv_ok,
                    "purchase_detected": cart_final.get("purchase_detected"),
                    "purchase_truth_source": conv_json.get("purchase_truth_source"),
                },
                timeline=_capture_timeline(),
                movement=_capture_movement(),
                signals=signals_final,
                cart_state=cart_final,
                detail={
                    "http_status": getattr(r_conv, "status_code", None),
                    "response": {
                        k: conv_json.get(k)
                        for k in (
                            "ok",
                            "purchase_completed",
                            "purchase_truth_source",
                            "recovery_key",
                        )
                    },
                },
                error=None if s7_ok else "purchase_confirm_failed",
            )
        )

        pulse = _build_pulse_payload(force_signals=True)
        assertions = _final_assertions(
            phone=phone,
            signals=signals_final,
            pulse=pulse,
            cart_state=cart_final,
        )
        overall = bool(s7_ok and assertions.get("ok") and all(s.get("ok") for s in steps))

        return {
            "ok": overall,
            "pass": overall,
            "scenario_id": SCENARIO_ID,
            "store_slug": LAB_STORE_SLUG,
            "identity": identity,
            "lab_phone": phone,
            "product": {
                "key": LAB_PRODUCT_KEY,
                "path": LAB_PRODUCT_PATH,
                "price_sar": LAB_PRODUCT_PRICE,
            },
            "reset": reset_out.get("fingerprint"),
            "steps": steps,
            "truth_assertions": assertions,
            "signal_assertions": {
                "signals": signals_final,
                "types": _signal_types(signals_final),
                "counts": assertions.get("signal_counts"),
            },
            "pulse_payload": pulse,
            "cart_page_state": cart_final,
            "cross_store": _cross_store_leak_check(),
            "recovered_purchase": assertions.get("recovered_purchase"),
            "ran_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
    finally:
        if prev_signals_flag is None:
            os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)
        else:
            os.environ[ENV_COMMERCE_SIGNALS_V1] = prev_signals_flag


def _fail_report(
    steps: list[dict[str, Any]],
    identity: dict[str, str],
    phone: str,
    reset_out: dict[str, Any],
) -> dict[str, Any]:
    cart_state = _capture_cart_state(phone=phone)
    signals = _capture_signals()
    pulse = {}
    try:
        pulse = _build_pulse_payload(force_signals=True)
    except Exception:  # noqa: BLE001
        pulse = {}
    return {
        "ok": False,
        "pass": False,
        "error": "lab_scenario1_step_failed",
        "scenario_id": SCENARIO_ID,
        "store_slug": LAB_STORE_SLUG,
        "identity": identity,
        "lab_phone": phone,
        "reset": reset_out.get("fingerprint") if isinstance(reset_out, dict) else None,
        "steps": steps,
        "signal_assertions": {
            "signals": signals,
            "types": _signal_types(signals),
        },
        "pulse_payload": pulse,
        "cart_page_state": cart_state,
        "failed_step": next(
            (s.get("step") for s in steps if not s.get("ok")),
            None,
        ),
    }


def run_lab_scenario1_duplicate_purchase_probe(
    *,
    client: Any = None,
    cf_test_phone: str = "",
) -> dict[str, Any]:
    """
    After a successful Scenario 1, POST conversion again.
    Expect still exactly one purchase_confirmed / recovery_completed signal.
    """
    first = run_lab_scenario1_v1(
        store_slug=LAB_STORE_SLUG,
        cf_test_phone=cf_test_phone,
        client=client,
    )
    if not first.get("ok"):
        return {
            "ok": False,
            "pass": False,
            "error": "scenario1_required_first",
            "first": first,
        }

    phone = first.get("lab_phone") or _lab_phone(cf_test_phone)
    if client is None:
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app)

    line = _hp_pro_line()
    r2 = client.post(
        "/api/conversion",
        json={
            "store_slug": LAB_STORE_SLUG,
            "session_id": LAB_SESSION_ID,
            "cart_id": LAB_CART_ID,
            "purchase_completed": True,
            "customer_phone": phone,
            "cf_test_phone": phone,
            "cart_total": LAB_PRODUCT_PRICE,
            "cart": [line],
        },
    )
    signals = _capture_signals(force=True)
    purchase_n = _count_signal_type(signals, SIGNAL_PURCHASE_CONFIRMED)
    completed_n = _count_signal_type(signals, SIGNAL_RECOVERY_COMPLETED)
    ok = purchase_n == 1 and completed_n == 1
    return {
        "ok": ok,
        "pass": ok,
        "scenario_id": SCENARIO_ID,
        "second_conversion_http": getattr(r2, "status_code", None),
        "signal_counts": {
            SIGNAL_PURCHASE_CONFIRMED: purchase_n,
            SIGNAL_RECOVERY_COMPLETED: completed_n,
        },
        "signals": signals,
        "first_pass": bool(first.get("pass")),
    }


__all__ = [
    "LAB_PRODUCT_KEY",
    "LAB_PRODUCT_PATH",
    "LAB_PRODUCT_PRICE",
    "SCENARIO_ID",
    "run_lab_scenario1_duplicate_purchase_probe",
    "run_lab_scenario1_v1",
    "validate_lab_scenario1_scope",
]
