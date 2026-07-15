# -*- coding: utf-8 -*-
"""
Reality Engine ingress — Phase 3.

Exercises real CartFlow service boundaries where possible.
Never injects Knowledge / dashboard / attribution conclusions.
Outbound WhatsApp is blocked by the simulation-safe adapter.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from extensions import db
from models import (
    AbandonedCart,
    AbandonmentReasonLog,
    CartRecoveryLog,
    CartRecoveryReason,
    RecoverySchedule,
    Store,
)
from services.store_reality_simulator.contracts_v1 import (
    DEMO_STORE_SLUG,
    provenance_envelope,
)
from services.store_reality_simulator.identity_guard_v1 import (
    SimulationIdentityIsolationError,
    assert_recovery_key_isolated,
    assert_written_store_is_demo,
    require_simulation_write_identity,
)
from services.store_reality_simulator.planner_v1 import PlannedEvent, UNSUPPORTED_MARKERS
from services.store_reality_simulator.row_index_v1 import register_tagged_row
from services.store_reality_simulator.safe_delivery_adapter_v1 import (
    simulation_outbound_guard,
)

log = logging.getLogger("cartflow.store_reality_simulator")


def _ensure_demo_store() -> Store:
    row = db.session.query(Store).filter(Store.zid_store_id == DEMO_STORE_SLUG).first()
    if row is None:
        row = Store(
            zid_store_id=DEMO_STORE_SLUG,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=2,
            whatsapp_recovery_enabled=False,
            is_active=True,
        )
        db.session.add(row)
        db.session.commit()
    else:
        # Safety: keep WA off for simulation target
        try:
            row.whatsapp_recovery_enabled = False
            db.session.add(row)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    return row


def _prov(ev: PlannedEvent, run_id: str, seed: int) -> dict[str, Any]:
    return provenance_envelope(
        simulation_run_id=run_id,
        simulation_scenario_id=ev.scenario_id,
        simulation_customer_id=ev.customer_id,
        simulated_event_id=ev.simulated_event_id,
        seed=seed,
    )


def execute_planned_event(
    ev: PlannedEvent,
    *,
    simulation_run_id: str,
    seed: int,
) -> dict[str, Any]:
    """
    Execute one planned event through platform-facing services / durable writers.
    Caller must wrap with simulation_scope (clock + delivery adapter).
    """
    if ev.event_type in UNSUPPORTED_MARKERS or ev.support == "unsupported":
        return {
            "ok": True,
            "bucket": "unsupported",
            "event_type": ev.event_type,
            "reason": "no_durable_platform_ingest",
        }

    try:
        require_simulation_write_identity(
            store_slug=DEMO_STORE_SLUG,
            simulation_run_id=simulation_run_id,
            surface=f"ingress:{ev.event_type}",
        )
        if ev.recovery_key:
            assert_recovery_key_isolated(
                ev.recovery_key, surface=f"ingress:{ev.event_type}"
            )
    except SimulationIdentityIsolationError as exc:
        db.session.rollback()
        return {
            "ok": False,
            "bucket": "rejected",
            "event_type": ev.event_type,
            "error": str(exc.reason),
            "isolation_failure": True,
        }

    store = _ensure_demo_store()
    at = ev.simulated_at
    if getattr(at, "tzinfo", None) is None:
        at = at.replace(tzinfo=timezone.utc)

    try:
        if ev.event_type == "cart_state_sync":
            return _upsert_cart(ev, store=store, run_id=simulation_run_id, seed=seed, at=at)
        if ev.event_type == "cart_abandoned":
            return _abandon_cart(ev, store=store, run_id=simulation_run_id, seed=seed, at=at)
        if ev.event_type == "hesitation_reason_selected":
            return _capture_reason(ev, run_id=simulation_run_id, seed=seed, at=at)
        if ev.event_type == "phone_submitted":
            return _capture_phone(ev, run_id=simulation_run_id, seed=seed, at=at)
        if ev.event_type in ("returned_to_site", "passive_return"):
            return _movement_return(ev, run_id=simulation_run_id)
        if ev.event_type == "whatsapp_scheduled":
            return _schedule_whatsapp(ev, run_id=simulation_run_id, seed=seed, at=at)
        if ev.event_type == "whatsapp_sent_mock":
            return _mock_whatsapp_send(ev, run_id=simulation_run_id, seed=seed, at=at)
        if ev.event_type == "purchase_created":
            return _purchase(ev, run_id=simulation_run_id, seed=seed, at=at)
        return {
            "ok": False,
            "bucket": "unsupported",
            "event_type": ev.event_type,
            "reason": "executor_unmapped",
        }
    except SimulationIdentityIsolationError as exc:
        db.session.rollback()
        return {
            "ok": False,
            "bucket": "rejected",
            "event_type": ev.event_type,
            "error": str(exc.reason),
            "isolation_failure": True,
        }
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        log.exception("SRS ingress failed event=%s", ev.simulated_event_id)
        return {
            "ok": False,
            "bucket": "failed",
            "event_type": ev.event_type,
            "error": str(exc)[:300],
        }


def _upsert_cart(
    ev: PlannedEvent,
    *,
    store: Store,
    run_id: str,
    seed: int,
    at: datetime,
) -> dict[str, Any]:
    require_simulation_write_identity(
        store_slug=DEMO_STORE_SLUG, simulation_run_id=run_id, surface="abandoned_carts"
    )
    if str(getattr(store, "zid_store_id", "") or "").strip() != DEMO_STORE_SLUG:
        raise SimulationIdentityIsolationError(
            "demo_store_row_escape",
            details={"zid_store_id": getattr(store, "zid_store_id", None)},
        )
    ac = (
        db.session.query(AbandonedCart)
        .filter(AbandonedCart.zid_cart_id == ev.cart_id)
        .first()
    )
    if ac is None:
        ac = AbandonedCart(
            store_id=int(store.id),
            zid_cart_id=ev.cart_id,
            status="detected",
            cart_value=float(ev.product_price),
            recovery_session_id=ev.session_id,
            customer_phone=ev.customer_phone or None,
            first_seen_at=at.replace(tzinfo=None) if at.tzinfo else at,
            last_seen_at=at.replace(tzinfo=None) if at.tzinfo else at,
        )
        AbandonedCart.set_raw(
            ac,
            {
                "items": [
                    {
                        "id": ev.product_id,
                        "name": ev.product_key,
                        "price": ev.product_price,
                        "qty": 1,
                    }
                ],
                **_prov(ev, run_id, seed),
            },
        )
        db.session.add(ac)
        db.session.flush()
        register_tagged_row(
            simulation_run_id=run_id,
            table_name="abandoned_carts",
            row_pk=str(ac.id),
        )
    else:
        ac.cart_value = float(ev.product_price)
        ac.last_seen_at = at.replace(tzinfo=None) if at.tzinfo else at
        if ev.customer_phone:
            ac.customer_phone = ev.customer_phone
        db.session.add(ac)
    db.session.commit()
    return {"ok": True, "bucket": "persisted", "abandoned_cart_id": ac.id}


def _abandon_cart(
    ev: PlannedEvent,
    *,
    store: Store,
    run_id: str,
    seed: int,
    at: datetime,
) -> dict[str, Any]:
    out = _upsert_cart(ev, store=store, run_id=run_id, seed=seed, at=at)
    ac = (
        db.session.query(AbandonedCart)
        .filter(AbandonedCart.zid_cart_id == ev.cart_id)
        .first()
    )
    if ac is not None:
        ac.status = "abandoned"
        db.session.add(ac)
        db.session.commit()
    out["status"] = "abandoned"
    out["bucket"] = "processed"
    return out


def _capture_reason(
    ev: PlannedEvent, *, run_id: str, seed: int, at: datetime
) -> dict[str, Any]:
    require_simulation_write_identity(
        store_slug=DEMO_STORE_SLUG, simulation_run_id=run_id, surface="reasons"
    )
    reason = (ev.reason_tag or "other").strip() or "other"
    row = (
        db.session.query(CartRecoveryReason)
        .filter(
            CartRecoveryReason.store_slug == DEMO_STORE_SLUG,
            CartRecoveryReason.session_id == ev.session_id,
        )
        .first()
    )
    naive = at.replace(tzinfo=None) if at.tzinfo else at
    if row is None:
        row = CartRecoveryReason(
            store_slug=DEMO_STORE_SLUG,
            session_id=ev.session_id,
            reason=reason,
            created_at=naive,
            updated_at=naive,
        )
        db.session.add(row)
        db.session.flush()
        register_tagged_row(
            simulation_run_id=run_id,
            table_name="cart_recovery_reasons",
            row_pk=str(row.id),
        )
    else:
        row.reason = reason
        row.updated_at = naive
        db.session.add(row)

    # Optional columns may exist depending on schema patches
    for attr, val in (
        ("cart_id", ev.cart_id),
        ("customer_phone", ev.customer_phone or None),
        ("reason_tag", reason),
    ):
        if hasattr(row, attr):
            try:
                setattr(row, attr, val)
            except Exception:  # noqa: BLE001
                pass

    log_row = AbandonmentReasonLog(
        store_slug=DEMO_STORE_SLUG,
        session_id=ev.session_id,
        reason=reason,
    )
    if hasattr(log_row, "created_at"):
        try:
            log_row.created_at = naive
        except Exception:  # noqa: BLE001
            pass
    db.session.add(log_row)
    db.session.flush()
    register_tagged_row(
        simulation_run_id=run_id,
        table_name="abandonment_reason_logs",
        row_pk=str(log_row.id),
    )
    db.session.commit()
    return {"ok": True, "bucket": "processed", "reason": reason}


def _capture_phone(
    ev: PlannedEvent, *, run_id: str, seed: int, at: datetime
) -> dict[str, Any]:
    ac = (
        db.session.query(AbandonedCart)
        .filter(AbandonedCart.zid_cart_id == ev.cart_id)
        .first()
    )
    if ac is not None and ev.customer_phone:
        ac.customer_phone = ev.customer_phone
        db.session.add(ac)
        db.session.commit()
    return {"ok": True, "bucket": "processed", "phone": bool(ev.customer_phone)}


def _movement_return(ev: PlannedEvent, *, run_id: str) -> dict[str, Any]:
    from services.customer_movement_snapshot_v1 import (
        EVENT_PASSIVE_RETURN,
        EVENT_RETURNED_TO_SITE,
        apply_movement_event,
    )

    require_simulation_write_identity(
        store_slug=DEMO_STORE_SLUG, simulation_run_id=run_id, surface="movement"
    )
    et = (
        EVENT_PASSIVE_RETURN
        if ev.event_type == "passive_return"
        else EVENT_RETURNED_TO_SITE
    )
    ok = apply_movement_event(
        recovery_key=ev.recovery_key,
        event_type=et,
        event_at=ev.simulated_at,
        store_slug=DEMO_STORE_SLUG,
        session_id=ev.session_id,
        cart_id=ev.cart_id,
    )
    try:
        from models import MovementSnapshot

        ms = (
            db.session.query(MovementSnapshot)
            .filter(MovementSnapshot.recovery_key == ev.recovery_key)
            .first()
        )
        if ms is not None:
            assert_written_store_is_demo(
                getattr(ms, "store_slug", None) or DEMO_STORE_SLUG,
                surface="movement_snapshots",
                simulation_run_id=run_id,
                recovery_key=ev.recovery_key,
            )
            register_tagged_row(
                simulation_run_id=run_id,
                table_name="movement_snapshots",
                row_pk=str(ms.id),
            )
            db.session.commit()
    except SimulationIdentityIsolationError:
        raise
    except Exception:  # noqa: BLE001
        db.session.rollback()
    return {"ok": bool(ok), "bucket": "processed" if ok else "failed", "event_type": et}


def _schedule_whatsapp(
    ev: PlannedEvent, *, run_id: str, seed: int, at: datetime
) -> dict[str, Any]:
    require_simulation_write_identity(
        store_slug=DEMO_STORE_SLUG, simulation_run_id=run_id, surface="recovery_schedule"
    )
    naive = at.replace(tzinfo=None) if at.tzinfo else at
    due = naive
    existing = (
        db.session.query(RecoverySchedule)
        .filter(RecoverySchedule.recovery_key == ev.recovery_key)
        .first()
    )
    if existing is None:
        sched = RecoverySchedule(
            recovery_key=ev.recovery_key,
            store_slug=DEMO_STORE_SLUG,
            session_id=ev.session_id,
            cart_id=ev.cart_id,
            reason_tag=ev.reason_tag or None,
            customer_phone=ev.customer_phone or None,
            scheduled_at=naive,
            due_at=due,
            effective_delay_seconds=0.0,
            delay_source="store_reality_simulator",
            status="scheduled",
            step=1,
            multi_slot_index=-1,
            context_json=json.dumps(_prov(ev, run_id, seed), ensure_ascii=False),
            created_at=naive,
            updated_at=naive,
        )
        db.session.add(sched)
        db.session.flush()
        register_tagged_row(
            simulation_run_id=run_id,
            table_name="recovery_schedules",
            row_pk=str(sched.id),
        )
        db.session.commit()
        sched_id = sched.id
    else:
        sched_id = existing.id
    # Timeline via real writer (clock-patched inside simulation_scope)
    try:
        from services.recovery_truth_timeline_v1 import record_recovery_truth_event

        record_recovery_truth_event(
            recovery_key=ev.recovery_key,
            status="scheduled",
            source="store_reality_simulator",
            store_slug=DEMO_STORE_SLUG,
            session_id=ev.session_id,
            cart_id=ev.cart_id,
        )
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "bucket": "processed", "schedule_id": sched_id}


def _mock_whatsapp_send(
    ev: PlannedEvent, *, run_id: str, seed: int, at: datetime
) -> dict[str, Any]:
    require_simulation_write_identity(
        store_slug=DEMO_STORE_SLUG, simulation_run_id=run_id, surface="whatsapp_mock"
    )
    guard = simulation_outbound_guard(
        store_slug=DEMO_STORE_SLUG,
        channel="whatsapp_twilio",
        reason_tag=ev.reason_tag or "simulation",
    )
    if guard is None:
        return {
            "ok": False,
            "bucket": "failed",
            "error": "simulation_adapter_inactive",
        }
    if not guard.get("ok") and guard.get("error") == "simulation_non_demo_rejected":
        return {"ok": False, "bucket": "rejected", "result": guard}

    naive = at.replace(tzinfo=None) if at.tzinfo else at
    log_row = CartRecoveryLog(
        store_slug=DEMO_STORE_SLUG,
        session_id=ev.session_id,
        cart_id=ev.cart_id,
        phone=ev.customer_phone or None,
        message="[SRS] mock_sent — no provider call",
        status="mock_sent",
        recovery_key=ev.recovery_key,
        reason_tag=(ev.reason_tag or "simulation")[:64],
    )
    if hasattr(log_row, "created_at"):
        try:
            log_row.created_at = naive
        except Exception:  # noqa: BLE001
            pass
    db.session.add(log_row)
    db.session.flush()
    register_tagged_row(
        simulation_run_id=run_id,
        table_name="cart_recovery_logs",
        row_pk=str(log_row.id),
    )
    db.session.commit()
    try:
        from services.recovery_truth_timeline_v1 import record_recovery_truth_event

        record_recovery_truth_event(
            recovery_key=ev.recovery_key,
            status="provider_sent",
            source="store_reality_simulator_mock",
            store_slug=DEMO_STORE_SLUG,
            session_id=ev.session_id,
            cart_id=ev.cart_id,
        )
    except Exception:  # noqa: BLE001
        pass
    return {
        "ok": True,
        "bucket": "suppressed",
        "provider_called": False,
        "guard": guard,
        "log_id": log_row.id,
    }


def _purchase(
    ev: PlannedEvent, *, run_id: str, seed: int, at: datetime
) -> dict[str, Any]:
    from services.purchase_truth import ingest_purchase_truth

    require_simulation_write_identity(
        store_slug=DEMO_STORE_SLUG,
        simulation_run_id=run_id,
        surface="purchase_truth",
    )
    assert_recovery_key_isolated(ev.recovery_key, surface="purchase_truth")

    written = ingest_purchase_truth(
        recovery_key=ev.recovery_key,
        purchase_source="store_reality_simulator",
        store_slug=DEMO_STORE_SLUG,
        session_id=ev.session_id,
        cart_id=ev.cart_id,
        customer_phone=ev.customer_phone or None,
        evidence_detail="srs_phase3_planned_purchase",
        purchase_time=at,
        context_payload={
            **_prov(ev, run_id, seed),
            "purchase_completed_at": at,
            "organic": bool((ev.payload or {}).get("organic")),
        },
        apply_lifecycle=True,
    )
    try:
        from models import PurchaseTruthRecord

        pt = (
            db.session.query(PurchaseTruthRecord)
            .filter(PurchaseTruthRecord.recovery_key == ev.recovery_key)
            .first()
        )
        if pt is not None:
            assert_written_store_is_demo(
                pt.store_slug,
                surface="purchase_truth_records",
                simulation_run_id=run_id,
                recovery_key=ev.recovery_key,
            )
            register_tagged_row(
                simulation_run_id=run_id,
                table_name="purchase_truth_records",
                row_pk=str(pt.id),
            )
            db.session.commit()
    except SimulationIdentityIsolationError:
        raise
    except Exception:  # noqa: BLE001
        db.session.rollback()
    return {
        "ok": bool(written),
        "bucket": "processed" if written else "rejected",
        "truth_written": bool(written),
        "store_slug": DEMO_STORE_SLUG,
    }
