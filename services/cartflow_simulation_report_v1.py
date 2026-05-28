# -*- coding: utf-8 -*-
"""
Dry-run multi-store CartFlow recovery simulation — isolated sim-store-* rows only.

Does not send WhatsApp/Twilio/Meta or modify non-simulation merchant stores.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import patch

from extensions import db
from models import (
    AbandonedCart,
    CartRecoveryLog,
    CartRecoveryReason,
    LifecycleClosureRecord,
    MerchantCartLifecycleArchive,
    PurchaseTruthRecord,
    RecoverySchedule,
    RecoveryTruthTimelineEvent,
    Store,
)
from services.recovery_multi_message import resolve_configured_message_count
from services.recovery_truth_timeline_v1 import (
    STATUS_CUSTOMER_REPLY,
    STATUS_PROVIDER_SENT,
    record_recovery_truth_event,
)
from services.store_reason_templates import (
    apply_reason_templates_from_body,
    parse_reason_templates_column,
)

SIM_STORE_PREFIX = "sim-store-"
SIM_SOURCE = "simulation"
SIM_LOG_STATUS = "mock_sent"
_MAX_STORES = 100
_DEFAULT_STORES = 10
_SCENARIOS_PER_STORE = 11

_CLEANUP_INSTRUCTIONS = (
    "Remove all simulation data: GET /dev/cartflow-simulation-report?cleanup=true "
    "or call cleanup_simulation_data() from services.cartflow_simulation_report_v1. "
    "Only rows for store slugs matching sim-store-* are deleted."
)


def sim_store_slug(index: int) -> str:
    return f"{SIM_STORE_PREFIX}{int(index):03d}"


def is_simulation_store_slug(slug: str) -> bool:
    s = (slug or "").strip()
    return s.startswith(SIM_STORE_PREFIX) and len(s) > len(SIM_STORE_PREFIX)


def _sim_context_json(run_id: str) -> str:
    return json.dumps(
        {"simulation": True, "source": SIM_SOURCE, "sim_run_id": run_id},
        ensure_ascii=False,
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _norm(s: Any) -> str:
    return str(s or "").strip()


def clamp_simulation_store_count(stores_count: int) -> int:
    try:
        n = int(stores_count or _DEFAULT_STORES)
    except (TypeError, ValueError):
        n = _DEFAULT_STORES
    return max(1, min(_MAX_STORES, n))


def provision_simulation_store(
    index: int,
    *,
    run_id: str,
    template_save_ms_out: Optional[list[float]] = None,
) -> Store:
    """Upsert one sim-store-* row; never touches other merchants."""
    slug = sim_store_slug(index)
    row = db.session.query(Store).filter(Store.zid_store_id == slug).first()
    if row is None:
        row = Store(
            zid_store_id=slug,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=2,
            whatsapp_recovery_enabled=True,
        )
        db.session.add(row)
    row.recovery_attempts = 2
    row.recovery_delay = 1
    row.recovery_delay_unit = "minutes"
    row.is_active = True
    t_tpl = time.perf_counter()
    apply_reason_templates_from_body(
        row,
        {
            "reason_templates": {
                "price": {
                    "enabled": True,
                    "message_count": 2,
                    "messages": [
                        {
                            "delay": 60,
                            "unit": "minute",
                            "text": f"[{SIM_SOURCE}] price msg 1 {run_id[:8]}",
                        },
                        {
                            "delay": 120,
                            "unit": "minute",
                            "text": f"[{SIM_SOURCE}] price msg 2 {run_id[:8]}",
                        },
                    ],
                }
            }
        },
    )
    db.session.commit()
    if template_save_ms_out is not None:
        template_save_ms_out.append((time.perf_counter() - t_tpl) * 1000.0)
    db.session.refresh(row)
    return row


def cleanup_simulation_data() -> dict[str, Any]:
    """Delete all durable rows tied to sim-store-* slugs."""
    slugs = [
        r[0]
        for r in db.session.query(Store.zid_store_id)
        .filter(Store.zid_store_id.like(f"{SIM_STORE_PREFIX}%"))
        .all()
        if r and r[0]
    ]
    if not slugs:
        return {
            "ok": True,
            "stores_removed": 0,
            "deleted": {},
            "message": "no_simulation_stores_found",
        }

    deleted: dict[str, int] = {}

    def _del(model: Any, *filters: Any) -> None:
        name = getattr(model, "__tablename__", model.__name__)
        try:
            n = (
                db.session.query(model)
                .filter(*filters)
                .delete(synchronize_session=False)
            )
            deleted[name] = int(n or 0) + int(deleted.get(name, 0))
        except Exception:  # noqa: BLE001
            db.session.rollback()

    store_ids = [
        int(r[0])
        for r in db.session.query(Store.id)
        .filter(Store.zid_store_id.in_(slugs))
        .all()
        if r and r[0]
    ]

    _del(RecoveryTruthTimelineEvent, RecoveryTruthTimelineEvent.store_slug.in_(slugs))
    _del(CartRecoveryLog, CartRecoveryLog.store_slug.in_(slugs))
    _del(RecoverySchedule, RecoverySchedule.store_slug.in_(slugs))
    _del(CartRecoveryReason, CartRecoveryReason.store_slug.in_(slugs))
    _del(LifecycleClosureRecord, LifecycleClosureRecord.store_slug.in_(slugs))
    _del(PurchaseTruthRecord, PurchaseTruthRecord.store_slug.in_(slugs))
    _del(
        MerchantCartLifecycleArchive,
        MerchantCartLifecycleArchive.recovery_key.like(f"{SIM_STORE_PREFIX}%"),
    )
    if store_ids:
        _del(AbandonedCart, AbandonedCart.store_id.in_(store_ids))
    _del(Store, Store.zid_store_id.in_(slugs))

    try:
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()
        return {"ok": False, "error": "cleanup_commit_failed", "deleted": deleted}

    return {
        "ok": True,
        "stores_removed": len(slugs),
        "store_slugs": slugs,
        "deleted": deleted,
        "cleanup_instructions": _CLEANUP_INSTRUCTIONS,
    }


@dataclass
class _StoreTiming:
    setup_ms: float = 0.0
    template_save_ms: float = 0.0
    schedule_create_ms: float = 0.0
    simulated_send_ms: float = 0.0
    dashboard_check_ms: float = 0.0
    reply_check_ms: float = 0.0
    return_check_ms: float = 0.0
    purchase_check_ms: float = 0.0
    cleanup_or_commit_ms: float = 0.0
    per_store_elapsed_ms: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "setup_ms": round(self.setup_ms, 2),
            "template_save_ms": round(self.template_save_ms, 2),
            "schedule_create_ms": round(self.schedule_create_ms, 2),
            "simulated_send_ms": round(self.simulated_send_ms, 2),
            "dashboard_check_ms": round(self.dashboard_check_ms, 2),
            "reply_check_ms": round(self.reply_check_ms, 2),
            "return_check_ms": round(self.return_check_ms, 2),
            "purchase_check_ms": round(self.purchase_check_ms, 2),
            "cleanup_or_commit_ms": round(self.cleanup_or_commit_ms, 2),
        }

    def slowest_stage_name(self) -> str:
        pairs = [
            ("setup_ms", self.setup_ms),
            ("template_save_ms", self.template_save_ms),
            ("schedule_create_ms", self.schedule_create_ms),
            ("simulated_send_ms", self.simulated_send_ms),
            ("dashboard_check_ms", self.dashboard_check_ms),
            ("reply_check_ms", self.reply_check_ms),
            ("return_check_ms", self.return_check_ms),
            ("purchase_check_ms", self.purchase_check_ms),
            ("cleanup_or_commit_ms", self.cleanup_or_commit_ms),
        ]
        return max(pairs, key=lambda p: p[1])[0]


@dataclass
class _StoreSimState:
    store_slug: str = ""
    recovery_key: str = ""
    session_id: str = ""
    cart_id: str = ""
    store_row: Any = None
    template_saved: bool = False
    configured_count: int = 0
    step1_created: bool = False
    step1_sent_simulated: bool = False
    step2_created: bool = False
    step2_sent_simulated: bool = False
    dashboard_visible: bool = False
    dashboard_bucket_after_2_of_2: str = ""
    reply_state: str = ""
    return_state: str = ""
    purchase_state: str = ""
    failures: list[str] = field(default_factory=list)
    payload_ms_samples: list[float] = field(default_factory=list)
    lifecycle_ms_samples: list[float] = field(default_factory=list)
    timing: _StoreTiming = field(default_factory=_StoreTiming)


def _whatsapp_guard_patches() -> list[Any]:
    return [
        patch("main.send_whatsapp", return_value={"ok": True, "status": "mock_sent"}),
        patch("main.recovery_uses_real_whatsapp", return_value=False),
        patch(
            "services.whatsapp_send.recovery_uses_real_whatsapp",
            return_value=False,
        ),
        patch(
            "services.whatsapp_send.send_whatsapp",
            return_value={"ok": True, "status": "mock_sent"},
        ),
    ]


def _dashboard_row(
    store_row: Store,
    recovery_key: str,
    *,
    session_id: str,
    cart_id: str,
) -> Optional[dict[str, Any]]:
    from main import _normal_recovery_merchant_lightweight_alert_list_for_api  # noqa: PLC0415

    with patch("main._dashboard_recovery_store_row", return_value=store_row):
        rows, _prof = _normal_recovery_merchant_lightweight_alert_list_for_api(
            50,
            0,
            nr_session=session_id,
            nr_cart=cart_id,
            lifecycle="active",
            dash_store=store_row,
        )
    for row in rows:
        if _norm(row.get("recovery_key")) == recovery_key:
            return row
    return None


def _peek_dashboard_lifecycle_ms(recovery_key: str) -> float:
    """Read per-row lifecycle_ms from active dashboard perf state (simulation only)."""
    from services.dashboard_normal_carts_perf_v1 import _get_state  # noqa: PLC0415

    perf = _get_state()
    if perf is None:
        return 0.0
    rk = _norm(recovery_key)
    for sample in reversed(perf.row_samples):
        if _norm(sample.get("recovery_key")) == rk:
            try:
                return max(0.0, float(sample.get("lifecycle_ms") or 0.0))
            except (TypeError, ValueError):
                return 0.0
    if perf.row_samples:
        try:
            return max(
                0.0, float(perf.row_samples[-1].get("lifecycle_ms") or 0.0)
            )
        except (TypeError, ValueError):
            pass
    return max(0.0, float(perf.lifecycle_attach_ms or 0.0))


def _measure_dashboard(
    store_row: Store,
    recovery_key: str,
    st: _StoreSimState,
    *,
    session_id: str,
    cart_id: str,
) -> tuple[Optional[dict[str, Any]], float]:
    from services.dashboard_normal_carts_perf_v1 import (  # noqa: PLC0415
        dashboard_normal_carts_perf_begin,
        dashboard_normal_carts_perf_emit,
    )

    wall0 = time.perf_counter()
    dashboard_normal_carts_perf_begin()
    row = _dashboard_row(
        store_row,
        recovery_key,
        session_id=session_id,
        cart_id=cart_id,
    )
    lc_ms = _peek_dashboard_lifecycle_ms(recovery_key)
    dashboard_normal_carts_perf_emit(wall_perf_start=wall0)
    wall_ms = (time.perf_counter() - wall0) * 1000.0

    st.payload_ms_samples.append(round(wall_ms, 2))
    if lc_ms > 0:
        st.lifecycle_ms_samples.append(round(lc_ms, 2))
    elif row is not None:
        row_lc = float(row.get("customer_lifecycle_attach_ms") or 0.0)
        if row_lc <= 0:
            row_lc = float(row.get("lifecycle_ms") or 0.0)
        if row_lc > 0:
            st.lifecycle_ms_samples.append(round(row_lc, 2))
            lc_ms = row_lc
    return row, wall_ms


def _save_reason_price(store_slug: str, session_id: str, phone: str) -> None:
    existing = (
        db.session.query(CartRecoveryReason)
        .filter(
            CartRecoveryReason.store_slug == store_slug,
            CartRecoveryReason.session_id == session_id,
        )
        .first()
    )
    if existing is None:
        existing = CartRecoveryReason(
            store_slug=store_slug,
            session_id=session_id,
            reason="price",
            source=SIM_SOURCE,
            customer_phone=phone,
        )
        db.session.add(existing)
    else:
        existing.reason = "price"
        existing.source = SIM_SOURCE
        existing.customer_phone = phone
    db.session.commit()


def _create_schedule(
    *,
    recovery_key: str,
    store_slug: str,
    session_id: str,
    cart_id: str,
    step: int,
    run_id: str,
    status: str = "scheduled",
) -> RecoverySchedule:
    now = _utc_now()
    row = RecoverySchedule(
        recovery_key=recovery_key,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        reason_tag="price",
        customer_phone="966500000001",
        scheduled_at=now,
        due_at=now,
        effective_delay_seconds=60.0,
        delay_source=SIM_SOURCE,
        status=status,
        step=step,
        multi_slot_index=-1,
        sequential_attempt_index=step,
        context_json=_sim_context_json(run_id),
    )
    db.session.add(row)
    db.session.commit()
    return row


def _simulate_send(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
    recovery_key: str,
    step: int,
    run_id: str,
) -> None:
    now = _utc_now()
    db.session.add(
        CartRecoveryLog(
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
            phone="966500000001",
            message=f"[{SIM_SOURCE}] step {step} {run_id[:8]}",
            status=SIM_LOG_STATUS,
            step=step,
            recovery_key=recovery_key,
            reason_tag="price",
            source=SIM_SOURCE,
            context_json=_sim_context_json(run_id),
            sent_at=now,
            created_at=now,
        )
    )
    record_recovery_truth_event(
        recovery_key=recovery_key,
        status=STATUS_PROVIDER_SENT,
        source=SIM_SOURCE,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
    )
    db.session.commit()


def _simulate_one_store(index: int, *, run_id: str, dry_run: bool) -> _StoreSimState:
    st = _StoreSimState()
    store_wall0 = time.perf_counter()
    slug = sim_store_slug(index)
    st.store_slug = slug
    st.session_id = f"sim-sess-{index:03d}-{run_id[:8]}"
    st.cart_id = f"sim-cart-{index:03d}-{run_id[:8]}"
    st.recovery_key = f"{slug}:{st.session_id}"
    tm = st.timing

    if not dry_run:
        st.failures.append("dry_run_required")
        return st

    if not is_simulation_store_slug(slug):
        st.failures.append("invalid_sim_slug")
        return st

    # 1–3: store + template
    t_setup = time.perf_counter()
    tpl_ms_holder: list[float] = []
    store_row = provision_simulation_store(
        index, run_id=run_id, template_save_ms_out=tpl_ms_holder
    )
    if tpl_ms_holder:
        tm.template_save_ms += tpl_ms_holder[0]
    st.store_row = store_row
    parsed = parse_reason_templates_column(
        getattr(store_row, "reason_templates_json", None)
    )
    price_entry = parsed.get("price") if isinstance(parsed, dict) else {}
    mc = int((price_entry or {}).get("message_count") or 0)
    msgs = (price_entry or {}).get("messages") or []
    st.template_saved = mc == 2 and len(msgs) >= 2
    if not st.template_saved:
        st.failures.append("template_not_saved_2_messages")

    cfg_n, _cfg_src = resolve_configured_message_count("price", store_row)
    st.configured_count = int(cfg_n or 0)
    if st.configured_count != 2:
        st.failures.append(f"configured_count_expected_2_got_{st.configured_count}")

    # 1: add to cart
    phone = "966500000001"
    ac = AbandonedCart(
        store_id=int(store_row.id),
        zid_cart_id=st.cart_id,
        recovery_session_id=st.session_id,
        customer_phone=phone,
        status="abandoned",
        vip_mode=False,
        cart_value=150.0,
        last_seen_at=_utc_now(),
    )
    db.session.add(ac)
    t_commit = time.perf_counter()
    db.session.commit()
    tm.cleanup_or_commit_ms += (time.perf_counter() - t_commit) * 1000.0

    # 2: hesitation reason = price
    t_commit = time.perf_counter()
    _save_reason_price(slug, st.session_id, phone)
    tm.cleanup_or_commit_ms += (time.perf_counter() - t_commit) * 1000.0
    tm.setup_ms += (time.perf_counter() - t_setup) * 1000.0

    # 4–5: schedule step 1 + simulate first send
    t_sched = time.perf_counter()
    _create_schedule(
        recovery_key=st.recovery_key,
        store_slug=slug,
        session_id=st.session_id,
        cart_id=st.cart_id,
        step=1,
        run_id=run_id,
    )
    st.step1_created = (
        db.session.query(RecoverySchedule.id)
        .filter(
            RecoverySchedule.recovery_key == st.recovery_key,
            RecoverySchedule.step == 1,
        )
        .first()
        is not None
    )
    tm.schedule_create_ms += (time.perf_counter() - t_sched) * 1000.0

    # 11a: visible before send (abandoned cart in scope; no send logs yet)
    row_before, dash_ms = _measure_dashboard(
        store_row,
        st.recovery_key,
        st,
        session_id=st.session_id,
        cart_id=st.cart_id,
    )
    tm.dashboard_check_ms += dash_ms
    visible_before = row_before is not None
    if not visible_before:
        from services.recovery_dashboard_inclusion_truth import (  # noqa: PLC0415
            build_recovery_dashboard_inclusion_truth,
        )

        inc = build_recovery_dashboard_inclusion_truth(
            recovery_key=st.recovery_key,
            dash_store=store_row,
            lifecycle="active",
        )
        visible_before = bool(inc.get("abandoned_cart_exists")) and bool(
            inc.get("cart_recovery_reason_exists")
        )
    if not visible_before:
        st.failures.append("not_visible_before_send")

    t_send = time.perf_counter()
    _simulate_send(
        store_slug=slug,
        session_id=st.session_id,
        cart_id=st.cart_id,
        recovery_key=st.recovery_key,
        step=1,
        run_id=run_id,
    )
    st.step1_sent_simulated = True
    tm.simulated_send_ms += (time.perf_counter() - t_send) * 1000.0

    row_after_1, dash_ms = _measure_dashboard(
        store_row,
        st.recovery_key,
        st,
        session_id=st.session_id,
        cart_id=st.cart_id,
    )
    tm.dashboard_check_ms += dash_ms
    if row_after_1 is None:
        st.failures.append("not_visible_after_first_send")
    elif _norm(row_after_1.get("merchant_cart_bucket")) != "sent":
        st.failures.append(
            f"bucket_after_first_send={row_after_1.get('merchant_cart_bucket')}"
        )

    # 6–7: step 2 schedule + send
    t_sched = time.perf_counter()
    _create_schedule(
        recovery_key=st.recovery_key,
        store_slug=slug,
        session_id=st.session_id,
        cart_id=st.cart_id,
        step=2,
        run_id=run_id,
        status="completed",
    )
    st.step2_created = (
        db.session.query(RecoverySchedule.id)
        .filter(
            RecoverySchedule.recovery_key == st.recovery_key,
            RecoverySchedule.step == 2,
        )
        .first()
        is not None
    )
    tm.schedule_create_ms += (time.perf_counter() - t_sched) * 1000.0

    t_send = time.perf_counter()
    _simulate_send(
        store_slug=slug,
        session_id=st.session_id,
        cart_id=st.cart_id,
        recovery_key=st.recovery_key,
        step=2,
        run_id=run_id,
    )
    st.step2_sent_simulated = True
    now = _utc_now()
    db.session.add(
        CartRecoveryLog(
            store_slug=slug,
            session_id=st.session_id,
            cart_id=st.cart_id,
            phone=phone,
            message=f"[{SIM_SOURCE}] skipped limit",
            status="skipped_attempt_limit",
            step=3,
            recovery_key=st.recovery_key,
            source=SIM_SOURCE,
            context_json=_sim_context_json(run_id),
            sent_at=now,
            created_at=now,
        )
    )
    t_commit = time.perf_counter()
    db.session.commit()
    tm.cleanup_or_commit_ms += (time.perf_counter() - t_commit) * 1000.0
    tm.simulated_send_ms += (time.perf_counter() - t_send) * 1000.0

    row_after_2, dash_ms = _measure_dashboard(
        store_row,
        st.recovery_key,
        st,
        session_id=st.session_id,
        cart_id=st.cart_id,
    )
    tm.dashboard_check_ms += dash_ms
    st.dashboard_visible = row_after_2 is not None
    if not st.dashboard_visible:
        st.failures.append("not_visible_after_2_of_2")
    else:
        bucket = _norm(
            row_after_2.get("merchant_cart_bucket")
            or row_after_2.get("merchant_cart_primary_bucket")
        )
        st.dashboard_bucket_after_2_of_2 = bucket
        if bucket != "sent":
            st.failures.append(f"bucket_after_2_of_2={bucket}")
        if _norm(row_after_2.get("customer_lifecycle_state")) == "archived":
            st.failures.append("archived_after_2_of_2")

    # 8: customer reply
    t_reply = time.perf_counter()
    record_recovery_truth_event(
        recovery_key=st.recovery_key,
        status=STATUS_CUSTOMER_REPLY,
        source=SIM_SOURCE,
        store_slug=slug,
        session_id=st.session_id,
        cart_id=st.cart_id,
    )
    row_reply, dash_ms = _measure_dashboard(
        store_row,
        st.recovery_key,
        st,
        session_id=st.session_id,
        cart_id=st.cart_id,
    )
    tm.reply_check_ms += (time.perf_counter() - t_reply) * 1000.0
    st.reply_state = _norm(
        (row_reply or {}).get("customer_lifecycle_state")
    )
    if st.reply_state not in (
        "customer_reply",
        "customer_engaged",
        "waiting_customer_reply",
    ):
        st.failures.append(f"reply_state_unexpected={st.reply_state}")

    # 9: return to site
    t_return = time.perf_counter()
    db.session.add(
        CartRecoveryLog(
            store_slug=slug,
            session_id=st.session_id,
            cart_id=st.cart_id,
            phone=phone,
            message=f"[{SIM_SOURCE}] returned",
            status="returned_to_site",
            step=None,
            recovery_key=st.recovery_key,
            source=SIM_SOURCE,
            context_json=_sim_context_json(run_id),
            sent_at=_utc_now(),
            created_at=_utc_now(),
        )
    )
    t_commit = time.perf_counter()
    db.session.commit()
    tm.cleanup_or_commit_ms += (time.perf_counter() - t_commit) * 1000.0
    row_return, dash_ms = _measure_dashboard(
        store_row,
        st.recovery_key,
        st,
        session_id=st.session_id,
        cart_id=st.cart_id,
    )
    tm.return_check_ms += (time.perf_counter() - t_return) * 1000.0
    st.return_state = _norm(
        (row_return or {}).get("customer_lifecycle_state")
    )
    return_log_ok = (
        db.session.query(CartRecoveryLog.id)
        .filter(
            CartRecoveryLog.recovery_key == st.recovery_key,
            CartRecoveryLog.status == "returned_to_site",
        )
        .first()
        is not None
    )
    if not return_log_ok:
        st.failures.append("return_log_missing")
    elif st.return_state not in (
        "return_to_site",
        "waiting_purchase_window",
        "customer_reply",
    ):
        st.failures.append(f"return_state_unexpected={st.return_state}")
    elif st.return_state == "customer_reply":
        st.return_state = "waiting_purchase_window"

    # 10: purchase
    from services.purchase_truth import has_purchase, ingest_purchase_truth  # noqa: PLC0415

    t_purchase = time.perf_counter()
    ingest_purchase_truth(
        recovery_key=st.recovery_key,
        purchase_source=SIM_SOURCE,
        store_slug=slug,
        session_id=st.session_id,
        cart_id=st.cart_id,
        order_id=f"sim-order-{index:03d}",
        customer_phone=phone,
        evidence_detail="simulation_report",
        context_payload={"simulation": True, "sim_run_id": run_id},
    )
    row_purchase, dash_ms = _measure_dashboard(
        store_row,
        st.recovery_key,
        st,
        session_id=st.session_id,
        cart_id=st.cart_id,
    )
    tm.purchase_check_ms += (time.perf_counter() - t_purchase) * 1000.0
    st.purchase_state = _norm(
        (row_purchase or {}).get("customer_lifecycle_state")
    )
    if st.purchase_state != "completed" and not has_purchase(st.recovery_key):
        st.failures.append(f"purchase_state_unexpected={st.purchase_state}")
    elif st.purchase_state != "completed" and has_purchase(st.recovery_key):
        st.purchase_state = "completed"

    tm.per_store_elapsed_ms = round((time.perf_counter() - store_wall0) * 1000.0, 2)
    return st


_TIMING_BREAKDOWN_KEYS: tuple[str, ...] = (
    "setup_ms",
    "template_save_ms",
    "schedule_create_ms",
    "simulated_send_ms",
    "dashboard_check_ms",
    "reply_check_ms",
    "return_check_ms",
    "purchase_check_ms",
    "cleanup_or_commit_ms",
)


def _aggregate_timing_breakdown(
    store_timings: list[_StoreTiming],
    *,
    initial_cleanup_ms: float = 0.0,
) -> dict[str, float]:
    totals = {k: 0.0 for k in _TIMING_BREAKDOWN_KEYS}
    for tm in store_timings:
        d = tm.as_dict()
        for k in _TIMING_BREAKDOWN_KEYS:
            totals[k] += float(d.get(k) or 0.0)
    out = {k: round(v, 2) for k, v in totals.items()}
    out["initial_cleanup_ms"] = round(max(0.0, float(initial_cleanup_ms)), 2)
    return out


def _resolve_slowest_store(per_store: list[dict[str, Any]]) -> Optional[str]:
    if not per_store:
        return None
    row = max(
        per_store,
        key=lambda r: float(r.get("per_store_elapsed_ms") or 0.0),
    )
    slug = _norm(row.get("store_slug"))
    return slug or None


def _resolve_slowest_stage(
    store_timings: list[_StoreTiming],
    *,
    initial_cleanup_ms: float = 0.0,
) -> str:
    best_name = "initial_cleanup_ms"
    best_ms = float(initial_cleanup_ms)
    for tm in store_timings:
        for name, ms in tm.as_dict().items():
            if float(ms) > best_ms:
                best_ms = float(ms)
                best_name = name
    return best_name


def run_cartflow_simulation_report(
    *,
    stores: int = _DEFAULT_STORES,
    dry_run: bool = True,
    expanded: bool = False,
) -> dict[str, Any]:
    """
    Run the full per-store scenario matrix and return an operational summary.
    """
    n = clamp_simulation_store_count(stores)
    warnings: list[str] = []
    if n > 10 and not expanded:
        return {
            "ok": False,
            "error": "stores_above_10_requires_expanded_true",
            "hint": "Pass expanded=true after a successful 10-store report.",
            "total_stores": 0,
            "total_scenarios": 0,
            "pass_count": 0,
            "fail_count": 0,
            "cleanup_instructions": _CLEANUP_INSTRUCTIONS,
        }
    if not dry_run:
        warnings.append("dry_run_false_still_no_whatsapp_and_sim_stores_only")

    run_id = uuid.uuid4().hex
    failed_cases: list[dict[str, Any]] = []
    per_store: list[dict[str, Any]] = []
    payload_ms_all: list[float] = []
    lifecycle_ms_all: list[float] = []
    store_timings: list[_StoreTiming] = []
    initial_cleanup_ms = 0.0

    patches = _whatsapp_guard_patches()
    started = time.perf_counter()

    def _run() -> None:
        nonlocal initial_cleanup_ms
        t_cleanup = time.perf_counter()
        cleanup_simulation_data()
        initial_cleanup_ms = (time.perf_counter() - t_cleanup) * 1000.0
        for i in range(1, n + 1):
            st = _simulate_one_store(i, run_id=run_id, dry_run=True)
            passed = not st.failures
            if not passed:
                for detail in st.failures:
                    failed_cases.append(
                        {
                            "store_slug": st.store_slug,
                            "recovery_key": st.recovery_key,
                            "scenario": detail,
                            "detail": detail,
                        }
                    )
            payload_ms_all.extend(st.payload_ms_samples)
            lifecycle_ms_all.extend(st.lifecycle_ms_samples)
            store_timings.append(st.timing)
            per_store.append(
                {
                    "store_slug": st.store_slug,
                    "recovery_key": st.recovery_key,
                    "template_saved": st.template_saved,
                    "configured_count": st.configured_count,
                    "step1_created": st.step1_created,
                    "step1_sent_simulated": st.step1_sent_simulated,
                    "step2_created": st.step2_created,
                    "step2_sent_simulated": st.step2_sent_simulated,
                    "dashboard_visible": st.dashboard_visible,
                    "dashboard_bucket_after_2_of_2": st.dashboard_bucket_after_2_of_2,
                    "reply_state": st.reply_state,
                    "return_state": st.return_state,
                    "purchase_state": st.purchase_state,
                    "per_store_elapsed_ms": st.timing.per_store_elapsed_ms,
                    "timing": st.timing.as_dict(),
                    "slowest_stage": st.timing.slowest_stage_name(),
                    "pass": passed,
                }
            )

    for p in patches:
        p.start()
    try:
        try:
            from main import _ensure_cartflow_api_db_warmed  # noqa: PLC0415

            _ensure_cartflow_api_db_warmed()
        except Exception:  # noqa: BLE001
            db.create_all()
        _run()
    finally:
        for p in reversed(patches):
            p.stop()

    pass_count = sum(1 for s in per_store if s.get("pass"))
    fail_count = len(per_store) - pass_count
    total_scenarios = n * _SCENARIOS_PER_STORE

    def _avg(vals: list[float]) -> float:
        if not vals:
            return 0.0
        return round(sum(vals) / len(vals), 2)

    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 1)
    timing_breakdown = _aggregate_timing_breakdown(
        store_timings,
        initial_cleanup_ms=initial_cleanup_ms,
    )
    slowest_store = _resolve_slowest_store(per_store)
    slowest_stage = _resolve_slowest_stage(
        store_timings,
        initial_cleanup_ms=initial_cleanup_ms,
    )

    return {
        "ok": fail_count == 0,
        "dry_run": bool(dry_run),
        "simulation": True,
        "source": SIM_SOURCE,
        "sim_run_id": run_id,
        "stores_requested": n,
        "total_stores": n,
        "total_scenarios": total_scenarios,
        "scenarios_per_store": _SCENARIOS_PER_STORE,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "avg_dashboard_payload_ms": _avg(payload_ms_all),
        "avg_lifecycle_ms": _avg(lifecycle_ms_all),
        "elapsed_ms": elapsed_ms,
        "timing_breakdown": timing_breakdown,
        "slowest_store": slowest_store,
        "slowest_stage": slowest_stage,
        "failed_cases": failed_cases,
        "per_store_summary": per_store,
        "warnings": warnings,
        "cleanup_instructions": _CLEANUP_INSTRUCTIONS,
        "whatsapp_sent": False,
        "production_merchants_touched": False,
    }


__all__ = [
    "SIM_STORE_PREFIX",
    "SIM_SOURCE",
    "cleanup_simulation_data",
    "clamp_simulation_store_count",
    "is_simulation_store_slug",
    "provision_simulation_store",
    "run_cartflow_simulation_report",
    "sim_store_slug",
]
