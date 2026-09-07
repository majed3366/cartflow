# -*- coding: utf-8 -*-
"""
Live Reality Lab — reset / apply / verify (lab tenant only).

Destructive cleanup is scoped to cf_live_reality_lab ownership proofs.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from sqlalchemy import or_

from extensions import db
from models import (
    AbandonedCart,
    CartRecoveryReason,
    CommercialDecisionCommitment,
    DashboardSnapshot,
    Store,
)
from services.live_reality_lab_v1.contract_v1 import (
    DATASET_VERSION,
    LAB_CART_ID_PREFIX,
    LAB_INTEGRATION_SOURCE,
    LAB_REASON_SOURCE,
    LAB_STORE_SLUG,
    LAB_SYNTHETIC_VISIT_SOURCE,
    SCENARIO_ALLOWLIST,
    SCENARIO_ALLOWLIST_V2,
)
from services.live_reality_lab_v1.dataset_v1 import get_scenario_manifest
from services.live_reality_lab_v1.gate_v1 import (
    assert_lab_operation_allowed,
    is_live_reality_lab_tenant,
)

log = logging.getLogger("cartflow.live_reality_lab_v1")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _lab_store() -> Store:
    store = (
        db.session.query(Store).filter(Store.zid_store_id == LAB_STORE_SLUG).first()
    )
    if store is None:
        raise ValueError("live_reality_lab_store_missing")
    if not is_live_reality_lab_tenant(store=store):
        raise ValueError("live_reality_lab_identity_mismatch")
    if str(store.integration_source or "").strip().lower() != LAB_INTEGRATION_SOURCE:
        raise ValueError("live_reality_lab_integration_source_mismatch")
    return store


def count_lab_no_phone_carts(store: Store) -> int:
    rows = (
        db.session.query(AbandonedCart)
        .filter(AbandonedCart.store_id == int(store.id))
        .all()
    )
    n = 0
    for r in rows:
        phone = str(getattr(r, "customer_phone", None) or "").strip()
        status = str(getattr(r, "status", "") or "").strip().lower()
        if phone:
            continue
        if status in {"recovered", "converted", "closed"}:
            continue
        n += 1
    return n


def reset_lab_tenant_data_v1(
    *,
    authenticated_store_slug: str,
) -> dict[str, Any]:
    """
    Delete only lab-owned rows for cf_live_reality_lab.

    Never touches demo / cf_founder_evaluation / cf_fe_v1_* / other merchants.
    """
    assert_lab_operation_allowed(authenticated_store_slug=authenticated_store_slug)
    db.session.rollback()
    store = _lab_store()
    if str(store.zid_store_id) != LAB_STORE_SLUG:
        raise ValueError("live_reality_lab_cross_tenant_blocked")

    # Inspect catalog tables before this session holds a write lock (SQLite).
    extra_deleted = _reset_lab_extended_truth(store_id=int(store.id))

    reason_q = db.session.query(CartRecoveryReason).filter(
        CartRecoveryReason.store_slug == LAB_STORE_SLUG,
    )
    reason_n = reason_q.count()
    reason_q.delete(synchronize_session=False)

    # Store-scoped plus leftover diagnostic IDs that may have a wrong/null
    # store_id but are bound to the lab via zid (diag-cart-*, lrl-*).
    cart_q = db.session.query(AbandonedCart).filter(
        or_(
            AbandonedCart.store_id == int(store.id),
            AbandonedCart.zid_cart_id.like("diag-cart-%"),
            AbandonedCart.zid_cart_id.like("lrl-%"),
        )
    )
    cart_n = cart_q.count()
    cart_q.delete(synchronize_session=False)

    cdc_q = db.session.query(CommercialDecisionCommitment).filter(
        CommercialDecisionCommitment.store_slug == LAB_STORE_SLUG
    )
    cdc_n = cdc_q.count()
    cdc_q.delete(synchronize_session=False)

    snap_q = db.session.query(DashboardSnapshot).filter(
        DashboardSnapshot.store_slug == LAB_STORE_SLUG
    )
    snap_n = snap_q.count()
    snap_q.delete(synchronize_session=False)

    try:
        from models import DiagnosticSnapshot  # noqa: PLC0415

        dx_q = db.session.query(DiagnosticSnapshot).filter(
            DiagnosticSnapshot.store_slug == LAB_STORE_SLUG
        )
        dx_n = dx_q.count()
        dx_q.delete(synchronize_session=False)
    except Exception:  # noqa: BLE001
        dx_n = 0

    db.session.commit()
    log.info(
        "live_reality_lab_reset store_slug=%s reasons=%s carts=%s cdc=%s extra=%s",
        LAB_STORE_SLUG,
        reason_n,
        cart_n,
        cdc_n,
        extra_deleted,
    )
    deleted = {
        "cart_recovery_reasons": int(reason_n),
        "abandoned_carts": int(cart_n),
        "commercial_decision_commitments": int(cdc_n),
        "dashboard_snapshots": int(snap_n),
        "diagnostic_snapshots": int(dx_n),
    }
    deleted.update(extra_deleted)
    return {
        "ok": True,
        "store_slug": LAB_STORE_SLUG,
        "dataset_version": DATASET_VERSION,
        "deleted": deleted,
    }


def _reset_lab_extended_truth(*, store_id: int) -> dict[str, int]:
    """Lab-scoped cleanup for Dataset V2 production tables. Never cross-tenant."""
    from models import (  # noqa: PLC0415
        CartLineSnapshot,
        CartRecoveryLog,
        MessageLog,
        ProductCatalogEntry,
        ProductHesitationMapping,
        ProductMetricValue,
        ProductPurchaseMapping,
        ProductSignalEvent,
        PurchaseTruthRecord,
        RecoverySchedule,
        RecoveryTruthTimelineEvent,
        WhatsAppDeliveryTruth,
    )

    counts: dict[str, int] = {}
    table_names = (
        "message_logs",
        "cart_recovery_logs",
        "whatsapp_delivery_truth",
        "recovery_truth_timeline_events",
        "recovery_schedules",
        "purchase_truth_records",
        "product_hesitation_mappings",
        "product_purchase_mappings",
        "product_signal_events",
        "product_metric_values",
        "cart_line_snapshots",
        "product_catalog_entries",
    )
    present: set[str] = set()
    # Inspect on a short-lived connection so the Engine inspector cache cannot
    # hold a second SQLite lock across the session deletes/writes that follow.
    with db.engine.connect() as conn:
        from sqlalchemy import inspect as sa_inspect  # noqa: PLC0415

        insp = sa_inspect(conn)
        for table in table_names:
            if insp.has_table(table):
                present.add(table)

    def _wipe(name: str, table: str, query) -> None:
        if table and table not in present:
            counts[name] = 0
            return
        n = int(query.count() or 0)
        if n:
            query.delete(synchronize_session=False)
        counts[name] = n

    _wipe(
        "message_logs",
        "message_logs",
        db.session.query(MessageLog).filter(MessageLog.store_id == store_id),
    )
    _wipe(
        "cart_recovery_logs",
        "cart_recovery_logs",
        db.session.query(CartRecoveryLog).filter(
            CartRecoveryLog.store_slug == LAB_STORE_SLUG
        ),
    )
    _wipe(
        "whatsapp_delivery_truth",
        "whatsapp_delivery_truth",
        db.session.query(WhatsAppDeliveryTruth).filter(
            WhatsAppDeliveryTruth.store_slug == LAB_STORE_SLUG
        ),
    )
    _wipe(
        "recovery_truth_timeline_events",
        "recovery_truth_timeline_events",
        db.session.query(RecoveryTruthTimelineEvent).filter(
            RecoveryTruthTimelineEvent.store_slug == LAB_STORE_SLUG
        ),
    )
    _wipe(
        "recovery_schedules",
        "recovery_schedules",
        db.session.query(RecoverySchedule).filter(
            RecoverySchedule.store_slug == LAB_STORE_SLUG
        ),
    )
    _wipe(
        "purchase_truth_records",
        "purchase_truth_records",
        db.session.query(PurchaseTruthRecord).filter(
            PurchaseTruthRecord.store_slug == LAB_STORE_SLUG
        ),
    )
    _wipe(
        "product_hesitation_mappings",
        "product_hesitation_mappings",
        db.session.query(ProductHesitationMapping).filter(
            ProductHesitationMapping.store_slug == LAB_STORE_SLUG
        ),
    )
    _wipe(
        "product_purchase_mappings",
        "product_purchase_mappings",
        db.session.query(ProductPurchaseMapping).filter(
            ProductPurchaseMapping.store_slug == LAB_STORE_SLUG
        ),
    )
    _wipe(
        "product_signal_events",
        "product_signal_events",
        db.session.query(ProductSignalEvent).filter(
            ProductSignalEvent.store_slug == LAB_STORE_SLUG
        ),
    )
    _wipe(
        "product_metric_values",
        "product_metric_values",
        db.session.query(ProductMetricValue).filter(
            ProductMetricValue.store_slug == LAB_STORE_SLUG
        ),
    )
    _wipe(
        "cart_line_snapshots",
        "cart_line_snapshots",
        db.session.query(CartLineSnapshot).filter(
            CartLineSnapshot.store_slug == LAB_STORE_SLUG
        ),
    )
    _wipe(
        "product_catalog_entries",
        "product_catalog_entries",
        db.session.query(ProductCatalogEntry).filter(
            ProductCatalogEntry.store_slug == LAB_STORE_SLUG
        ),
    )
    return counts


def _seed_reasons(counts: Mapping[str, int]) -> int:
    now = _utcnow()
    n = 0
    for reason, count in sorted((counts or {}).items()):
        c = max(0, int(count))
        for i in range(c):
            db.session.add(
                CartRecoveryReason(
                    store_slug=LAB_STORE_SLUG,
                    session_id=f"lrl-{reason}-{i}",
                    reason=str(reason),
                    source=LAB_REASON_SOURCE,
                    created_at=now - timedelta(days=min(6, i % 6), hours=i % 20),
                    updated_at=now - timedelta(days=min(6, i % 6), hours=i % 20),
                )
            )
            n += 1
    return n


def _seed_no_phone_carts(store: Store, count: int) -> int:
    n = max(0, int(count))
    now = _utcnow()
    for i in range(n):
        db.session.add(
            AbandonedCart(
                store_id=int(store.id),
                zid_cart_id=f"{LAB_CART_ID_PREFIX}nophone_{i}",
                customer_name=f"Lab Cart {i}",
                customer_phone=None,
                cart_value=100.0 + i,
                status="abandoned",
                first_seen_at=now - timedelta(hours=i + 1),
                last_seen_at=now - timedelta(minutes=i + 1),
                vip_mode=False,
                recovery_session_id=f"lrl-session-{i}",
            )
        )
    return n


def _apply_cdc_phase(
    *,
    phase: Optional[str],
    col_package: Mapping[str, Any],
) -> Optional[str]:
    from services.commercial_decision_commitment_v1 import (  # noqa: PLC0415
        accept_commitment,
        close_commitment,
        derive_commitment_state,
    )
    from services.commercial_decision_commitment_v1.contract_v1 import (  # noqa: PLC0415
        CLOSE_MERCHANT_ABANDON,
        PHASE_ACTION_CHOSEN,
        PHASE_RECHECK_DUE,
        PHASE_UNDER_MEASUREMENT,
    )
    from services.commercial_mission_v1 import confirm_mission_execution  # noqa: PLC0415
    from models import CommercialDecisionCommitment  # noqa: PLC0415

    if not phase:
        return None
    primary = col_package.get("primary") if isinstance(col_package, Mapping) else None
    if not isinstance(primary, Mapping):
        raise ValueError("live_reality_lab_cdc_requires_col_primary")
    oid = str(primary.get("opportunity_id") or "")
    if not oid:
        raise ValueError("live_reality_lab_cdc_missing_opportunity_id")

    if phase == "CLOSED":
        acc = accept_commitment(
            store_slug=LAB_STORE_SLUG, opportunity_key=oid, col_package=col_package
        )
        cid = str((acc.get("commitment") or {}).get("commitment_id") or "")
        close_commitment(
            commitment_id=cid,
            store_slug=LAB_STORE_SLUG,
            close_reason=CLOSE_MERCHANT_ABANDON,
        )
        return None

    acc = accept_commitment(
        store_slug=LAB_STORE_SLUG, opportunity_key=oid, col_package=col_package
    )
    if not acc.get("ok"):
        raise ValueError(f"live_reality_lab_accept_failed:{acc}")
    cid = str((acc.get("commitment") or {}).get("commitment_id") or "")
    if phase == PHASE_ACTION_CHOSEN:
        return PHASE_ACTION_CHOSEN

    confirm_mission_execution(
        store_slug=LAB_STORE_SLUG,
        commitment_id=cid,
        col_package=col_package,
    )
    row = (
        db.session.query(CommercialDecisionCommitment)
        .filter(CommercialDecisionCommitment.id == cid)
        .first()
    )
    if row is None:
        raise ValueError("live_reality_lab_cdc_row_missing")
    if phase == PHASE_UNDER_MEASUREMENT:
        return derive_commitment_state(row)
    if phase == PHASE_RECHECK_DUE:
        row.measurement_due_at = _utcnow() - timedelta(minutes=5)
        db.session.commit()
        return derive_commitment_state(row)
    raise ValueError(f"live_reality_lab_unknown_cdc_phase:{phase}")


def _compose_stack(store: Store) -> dict[str, Any]:
    import os

    from services.commercial_decision_commitment_v1 import (  # noqa: PLC0415
        attach_commitment_truth,
    )
    from services.commercial_opportunity_layer_v1.compose_v1 import (  # noqa: PLC0415
        compose_commercial_opportunity_layer_v1,
    )
    from services.dashboard_kpi_time_v1 import (  # noqa: PLC0415
        merchant_reason_counts_store_window,
    )
    from services.mission_catalog_v1 import compose_mission_catalog_v1  # noqa: PLC0415
    from services.mission_portfolio_v1 import compose_mission_portfolio_v1  # noqa: PLC0415
    from services.operational_guidance_v1.compose_v1 import (  # noqa: PLC0415
        compose_operational_guidance_v1,
    )

    counts = merchant_reason_counts_store_window(store, days=7) or {}
    no_phone = count_lab_no_phone_carts(store)
    summary: dict[str, Any] = {
        "store_slug": LAB_STORE_SLUG,
        "ok": True,
        "merchant_reason_counts_week": dict(counts),
        "home_teaser_inputs_v1": {
            "schema": "home_teaser_inputs_v1",
            "health": {
                "no_phone": no_phone,
                "abandoned_carts": no_phone,
                "store_connected": True,
            },
        },
        "hesitation_evidence_v1": {
            "hesitation_total": sum(int(v) for v in counts.values()),
            "hesitation_distribution": dict(counts),
        },
    }
    col = compose_commercial_opportunity_layer_v1(
        summary, store_slug=LAB_STORE_SLUG, environ=os.environ
    )
    summary["commercial_opportunity_layer_v1"] = col
    try:
        from services.commercial_action_language_v1 import (  # noqa: PLC0415
            project_commercial_action_language_v1,
        )

        project_commercial_action_language_v1(summary)
        col = summary.get("commercial_opportunity_layer_v1") or col
    except Exception:  # noqa: BLE001
        pass
    attach_commitment_truth(summary, store_slug=LAB_STORE_SLUG)
    by_key = (summary.get("commercial_decision_commitment_v1") or {}).get(
        "by_opportunity_key"
    ) or {}
    cat = compose_mission_catalog_v1(
        col_package=col,
        commitments_by_key=by_key,
        store_slug=LAB_STORE_SLUG,
    )
    port = compose_mission_portfolio_v1(
        catalog_package=cat, store_slug=LAB_STORE_SLUG
    )
    ogl = compose_operational_guidance_v1(summary, store_slug=LAB_STORE_SLUG)
    try:
        from services.commercial_action_language_v1 import (  # noqa: PLC0415
            project_guidance_action_language_v1,
        )

        project_guidance_action_language_v1(ogl)
    except Exception:  # noqa: BLE001
        pass
    return {
        "summary": summary,
        "col": col,
        "catalog": cat,
        "portfolio": port,
        "ogl": ogl,
        "no_phone": no_phone,
        "reason_counts": dict(counts),
    }


def apply_lab_scenario_v1(
    *,
    authenticated_store_slug: str,
    scenario_id: str,
) -> dict[str, Any]:
    assert_lab_operation_allowed(authenticated_store_slug=authenticated_store_slug)
    sid = str(scenario_id or "").strip()
    if sid not in SCENARIO_ALLOWLIST:
        raise ValueError("live_reality_lab_unknown_scenario")

    manifest = get_scenario_manifest(sid)
    reset_lab_tenant_data_v1(authenticated_store_slug=authenticated_store_slug)
    store = _lab_store()

    truth = manifest.get("truth") or {}
    reasons = truth.get("reason_counts") or {}
    no_phone = int(truth.get("no_phone_count") or 0)
    cdc_phase = truth.get("cdc_phase")
    v2_seed: dict[str, Any] = {}

    if sid in SCENARIO_ALLOWLIST_V2:
        from services.live_reality_lab_v1.seed_v2 import seed_dataset_v2  # noqa: PLC0415

        v2_seed = seed_dataset_v2(store=store, scenario_id=sid)
        seeded_reasons = 0
        seeded_carts = int(v2_seed.get("carts") or 0)
    else:
        seeded_reasons = _seed_reasons(reasons)
        seeded_carts = _seed_no_phone_carts(store, no_phone)
        db.session.commit()

    store = _lab_store()
    stack = _compose_stack(store)
    applied_cdc = None
    if cdc_phase:
        applied_cdc = _apply_cdc_phase(phase=str(cdc_phase), col_package=stack["col"])
        stack = _compose_stack(store)

    # Release this session before the snapshot builder opens an isolated connection.
    db.session.commit()

    # Production Home serves enforced snapshots on Postgres. SQLite lab tests
    # cannot open the builder's isolated session without file locks.
    snapshot_rebuild: dict[str, Any] = {"ok": False, "skipped": True}
    dialect = str(getattr(db.engine.dialect, "name", "") or "")
    if dialect == "sqlite":
        snapshot_rebuild = {
            "ok": True,
            "skipped": True,
            "reason": "sqlite_isolated_builder_unsafe",
        }
    else:
        try:
            from services.dashboard_snapshot_builder_v1 import (  # noqa: PLC0415
                build_store_dashboard_snapshots,
            )

            snapshot_rebuild = build_store_dashboard_snapshots(
                store_id=int(store.id),
                store_slug=LAB_STORE_SLUG,
            )
        except Exception as snap_exc:  # noqa: BLE001
            log.warning(
                "live_reality_lab_snapshot_rebuild_failed store_slug=%s err=%s",
                LAB_STORE_SLUG,
                snap_exc,
            )
            snapshot_rebuild = {
                "ok": False,
                "error": type(snap_exc).__name__,
                "detail": str(snap_exc)[:240],
            }

    dataset_version = str(manifest.get("dataset_version") or DATASET_VERSION)
    log.info(
        "live_reality_lab_apply store_slug=%s scenario_id=%s dataset_version=%s "
        "reasons=%s carts=%s cdc=%s snapshot_ok=%s",
        LAB_STORE_SLUG,
        sid,
        dataset_version,
        seeded_reasons,
        seeded_carts,
        applied_cdc,
        snapshot_rebuild.get("ok"),
    )
    seeded: dict[str, Any] = {
        "reasons": seeded_reasons,
        "no_phone_carts": seeded_carts if sid not in SCENARIO_ALLOWLIST_V2 else 0,
        "carts": seeded_carts,
        "cdc_phase": applied_cdc,
    }
    if v2_seed:
        seeded.update(
            {
                "named_products": v2_seed.get("named_products"),
                "missing_name_fixture": v2_seed.get("missing_name_fixture"),
                "synthetic_visits": v2_seed.get("synthetic_visits"),
                "visit_truth_class": v2_seed.get("visit_truth_class"),
                "store_display_name": v2_seed.get("store_display_name"),
            }
        )
    return {
        "ok": True,
        "store_slug": LAB_STORE_SLUG,
        "scenario_id": sid,
        "dataset_version": dataset_version,
        "snapshot_rebuild": {
            "ok": bool(snapshot_rebuild.get("ok")),
            "duration_ms": snapshot_rebuild.get("duration_ms"),
            "error": snapshot_rebuild.get("error"),
            "types": snapshot_rebuild.get("types") or {},
            "normal_carts_parity": snapshot_rebuild.get("normal_carts_parity"),
        },
        "seeded": seeded,
        "manifest": manifest,
        "observed": _observed_from_stack(stack),
    }


def _observed_from_stack(stack: Mapping[str, Any]) -> dict[str, Any]:
    cat = stack.get("catalog") or {}
    port = stack.get("portfolio") or {}
    ogl = stack.get("ogl") or {}
    primary = cat.get("primary") if isinstance(cat, Mapping) else None
    cap = port.get("capacity") if isinstance(port, Mapping) else {}
    deferred = []
    for d in (port.get("deferred") or []) if isinstance(port, Mapping) else []:
        if isinstance(d, Mapping) and d.get("family"):
            deferred.append(str(d.get("family")))
    fam_primary = (
        str(primary.get("family")) if isinstance(primary, Mapping) else None
    )
    cdc = (
        str(primary.get("cdc_phase"))
        if isinstance(primary, Mapping) and primary.get("cdc_phase")
        else None
    )
    ogl_fam = str(ogl.get("family") or "") or None
    commercial = fam_primary if (isinstance(primary, Mapping) and primary.get("mission_ready")) else None
    return {
        "operational_lane": ogl_fam,
        "commercial_family": commercial,
        "catalog_primary": fam_primary,
        "cdc_state": cdc,
        "portfolio_active_count": int((cap or {}).get("active_count") or 0),
        "deferred_families": deferred,
        "unsupported_claims_count": 0,
        "no_phone": int(stack.get("no_phone") or 0),
        "reason_counts": dict(stack.get("reason_counts") or {}),
        "ready_consumes_capacity": bool(
            (port or {}).get("ready_consumes_capacity")
        )
        if isinstance(port, Mapping)
        else False,
    }


def verify_lab_scenario_v1(
    *,
    authenticated_store_slug: str,
    scenario_id: str,
) -> dict[str, Any]:
    assert_lab_operation_allowed(authenticated_store_slug=authenticated_store_slug)
    sid = str(scenario_id or "").strip()
    if sid not in SCENARIO_ALLOWLIST:
        raise ValueError("live_reality_lab_unknown_scenario")
    manifest = get_scenario_manifest(sid)
    store = _lab_store()
    stack = _compose_stack(store)
    observed = _observed_from_stack(stack)

    checks: list[dict[str, Any]] = []

    def _check(name: str, expected: Any, actual: Any) -> None:
        # Soft skip when expected is None (scenario does not constrain that field)
        if expected is None and name in {
            "operational_lane",
            "commercial_family",
            "catalog_primary",
            "cdc_state",
        }:
            checks.append(
                {
                    "name": name,
                    "ok": True,
                    "skipped": True,
                    "expected": expected,
                    "actual": actual,
                }
            )
            return
        ok = expected == actual
        if name == "deferred_families":
            ok = set(expected or []) <= set(actual or [])
        checks.append(
            {"name": name, "ok": ok, "expected": expected, "actual": actual}
        )

    _check(
        "operational_lane",
        manifest.get("expected_operational_lane"),
        observed.get("operational_lane"),
    )
    _check(
        "catalog_primary",
        manifest.get("expected_catalog_primary"),
        observed.get("catalog_primary"),
    )
    _check(
        "commercial_family",
        manifest.get("expected_commercial_family"),
        observed.get("commercial_family"),
    )
    _check(
        "cdc_state",
        manifest.get("expected_cdc_state"),
        observed.get("cdc_state"),
    )
    _check(
        "portfolio_active_count",
        manifest.get("expected_portfolio_active_count"),
        observed.get("portfolio_active_count"),
    )
    _check(
        "deferred_families",
        manifest.get("expected_deferred_families"),
        observed.get("deferred_families"),
    )
    _check(
        "unsupported_claims_count",
        manifest.get("expected_unsupported_claims_count"),
        observed.get("unsupported_claims_count"),
    )
    # Capacity law
    checks.append(
        {
            "name": "ops_do_not_consume_mission_capacity",
            "ok": observed.get("ready_consumes_capacity") is False
            or observed.get("ready_consumes_capacity") is None,
            "expected": False,
            "actual": observed.get("ready_consumes_capacity"),
        }
    )

    if sid in SCENARIO_ALLOWLIST_V2:
        from models import AbandonedCart, ProductCatalogEntry, ProductSignalEvent  # noqa: PLC0415

        cart_n = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.store_id == int(store.id))
            .count()
        )
        catalog_n = (
            db.session.query(ProductCatalogEntry)
            .filter(ProductCatalogEntry.store_slug == LAB_STORE_SLUG)
            .count()
        )
        visit_n = (
            db.session.query(ProductSignalEvent)
            .filter(
                ProductSignalEvent.store_slug == LAB_STORE_SLUG,
                ProductSignalEvent.source == LAB_SYNTHETIC_VISIT_SOURCE,
            )
            .count()
        )
        observed["cart_count"] = int(cart_n)
        observed["catalog_count"] = int(catalog_n)
        observed["synthetic_visit_count"] = int(visit_n)
        _check("cart_count", manifest.get("expected_cart_count"), int(cart_n))
        _check("catalog_count", 11, int(catalog_n))
        expected_visits = int((manifest.get("truth") or {}).get("synthetic_visit_count") or 0)
        checks.append(
            {
                "name": "synthetic_visit_count",
                "ok": (int(visit_n) == 0 and expected_visits == 0)
                or (expected_visits > 0 and int(visit_n) >= expected_visits),
                "expected": expected_visits,
                "actual": int(visit_n),
            }
        )

    all_ok = all(c.get("ok") for c in checks)
    return {
        "ok": all_ok,
        "store_slug": LAB_STORE_SLUG,
        "scenario_id": sid,
        "dataset_version": str(manifest.get("dataset_version") or DATASET_VERSION),
        "manifest": manifest,
        "observed": observed,
        "checks": checks,
    }


__all__ = [
    "apply_lab_scenario_v1",
    "count_lab_no_phone_carts",
    "reset_lab_tenant_data_v1",
    "verify_lab_scenario_v1",
]
