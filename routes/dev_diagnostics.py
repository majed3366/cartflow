# -*- coding: utf-8 -*-
"""Read-only dev diagnostic routes (Phase 1D/1E-A extraction)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Optional

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from json_response import j
from models import AbandonedCart, CartRecoveryLog, CartRecoveryReason, RecoverySchedule, Store
from services.ai_message_builder import build_abandoned_cart_message
from services.whatsapp_recovery import build_whatsapp_recovery_message
from services.whatsapp_send import should_send_whatsapp
from services.merchant_vip_settings import merchant_vip_notify_enabled
from services.vip_cart import abandoned_cart_in_vip_operational_lane
from services.vip_merchant_alert import (
    VIP_MERCHANT_ALERT_REASON_TAG,
    resolve_vip_alert_destination,
)
from services.vip_operational_truth_v1 import vip_alert_delivery_summary

log = logging.getLogger("cartflow")

router = APIRouter(tags=["dev-diagnostics"])


@router.get("/dev/routes")
def list_routes():
    from main import app as _main_app  # noqa: PLC0415
    return [route.path for route in _main_app.routes]


@router.get("/dev/config-system-verify")
def config_system_verify():
    import main as _main  # noqa: PLC0415
    from config_system import get_cartflow_config

    config = get_cartflow_config(store_slug="demo")

    return {
        "ok": True,
        "config_loaded": True,
    }


@router.get("/dev/admin-operational-summary")
def dev_admin_operational_summary():
    import main as _main  # noqa: PLC0415
    """ملخص تشغيلي للمشرف — قراءة فقط؛ يعمل مع ‎ENV=development‎ فقط."""
    if not _main._is_development_mode():
        return PlainTextResponse("Not found", status_code=404)
    from services.cartflow_admin_operational_summary import (
        build_admin_operational_summary_readonly,
    )

    return j(build_admin_operational_summary_readonly())


@router.get("/dev/production-readiness")
def dev_production_readiness():
    import main as _main  # noqa: PLC0415
    """تقرير جاهزية الإنتاج — قراءة فقط، بدون قيم أسرار؛ ‎ENV=development‎ فقط."""
    if not _main._is_development_mode():
        return PlainTextResponse("Not found", status_code=404)
    from services.cartflow_production_readiness import (
        build_cartflow_production_readiness_report,
    )

    return j(build_cartflow_production_readiness_report())


@router.get("/dev/widget-runtime-config-verify")
def dev_widget_runtime_config_verify(
    store_slug: str = Query("demo", min_length=1, max_length=255),
):
    import main as _main  # noqa: PLC0415
    """
    مقارنة سريعة: إعدادات الودجيت من ‎Store‎ نفسها مقابل حزمة لوحة التاجر و‎widget_trigger_config‎.
    """
    try:
        _main._ensure_store_widget_schema()
        db.create_all()
        _main._ensure_default_store_for_recovery()
        from services.cartflow_widget_public_store import store_row_for_widget_public_api
        from services.cartflow_widget_trigger_settings import (
            widget_trigger_config_from_store_row,
        )
        from services.merchant_widget_panel import (
            merchant_reason_panel_rows_for_widget_settings,
            merchant_visible_reason_keys_for_runtime,
            merchant_widget_panel_bundle,
        )
        from services.store_reason_templates import parse_reason_templates_column

        row = store_row_for_widget_public_api(store_slug)
        if row is None:
            return j(
                {"ok": False, "error": "no_store", "store_slug": store_slug},
                404,
            )
        try:
            latest = db.session.query(Store).order_by(Store.id.desc()).first()
        except (SQLAlchemyError, OSError):
            db.session.rollback()
            latest = None
        same_row_as_dashboard_latest = bool(
            latest is not None and row is not None and int(latest.id) == int(row.id)
        )
        pub_trig = widget_trigger_config_from_store_row(row)
        pub_rt = parse_reason_templates_column(getattr(row, "reason_templates_json", None))
        dash = merchant_widget_panel_bundle(row)
        dash_trig = dash.get("trigger") or {}
        reason_rows_dash = merchant_reason_panel_rows_for_widget_settings(row)
        visible_keys = merchant_visible_reason_keys_for_runtime(row)
        trigger_match = pub_trig == dash_trig
        phone_match = pub_trig.get("widget_phone_capture_mode") == dash_trig.get(
            "widget_phone_capture_mode"
        )
        exit_match = pub_trig.get("exit_intent_enabled") == dash_trig.get(
            "exit_intent_enabled"
        )
        reasons_match = pub_rt == parse_reason_templates_column(
            getattr(row, "reason_templates_json", None)
        )
        runtime_keys = sorted(
            set(pub_trig.keys())
            | {
                "reason_templates",
                "cartflow_widget_enabled",
                "widget_name",
                "widget_primary_color",
                "widget_style",
            }
        )
        zid_resolved = getattr(row, "zid_store_id", None)
        zid_resolved_s = zid_resolved.strip() if isinstance(zid_resolved, str) else None
        return j(
            {
                "ok": True,
                "store_slug": store_slug,
                "dashboard_settings_loaded": True,
                "public_config_matches_dashboard": bool(
                    trigger_match and phone_match and exit_match and reasons_match
                ),
                "runtime_keys_present": runtime_keys,
                "widget_trigger_keys": sorted(pub_trig.keys()),
                "resolved_store_row_id": int(row.id),
                "resolved_zid_store_id": zid_resolved_s,
                "dashboard_latest_store_row_id": int(latest.id) if latest is not None else None,
                "dashboard_latest_zid_store_id": (
                    str(latest.zid_store_id).strip()
                    if latest is not None
                    and isinstance(getattr(latest, "zid_store_id", None), str)
                    and str(latest.zid_store_id).strip()
                    else None
                ),
                "same_row_as_dashboard_latest": same_row_as_dashboard_latest,
                "reason_templates_public_config": pub_rt,
                "reason_rows_dashboard_panel": reason_rows_dash,
                "visible_reason_keys_from_config": visible_keys,
            }
        )
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e), "store_slug": store_slug}, 500)


@router.get("/dev/store-template-debug")
def dev_store_template_debug(
    store_slug: str = Query("demo", min_length=1, max_length=255),
    reason: str = Query("other", min_length=1, max_length=64),
) -> Any:
    import main as _main  # noqa: PLC0415
    """
    Read-only: compare dashboard trigger-template Store row vs runtime recovery Store row.
    Does not change delays, templates, or recovery behavior.
    """
    from services.store_template_source_debug import build_store_template_debug_report

    try:
        _main._ensure_cartflow_api_db_warmed()
        return j(build_store_template_debug_report(store_slug=store_slug, reason=reason))
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/template-truth")
def dev_template_truth(
    store_slug: str = Query("demo", min_length=1, max_length=255),
    reason: str = Query("other", min_length=1, max_length=64),
) -> Any:
    import main as _main  # noqa: PLC0415
    """Read-only: prove dashboard template storage vs runtime resolver lookup."""
    from services.template_truth_debug import build_template_truth_report

    try:
        _main._ensure_cartflow_api_db_warmed()
        return j(build_template_truth_report(store_slug=store_slug, reason=reason))
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/store-identity-runtime-truth")
def dev_store_identity_runtime_truth(
    storefront_slug: str = Query("", min_length=0, max_length=255),
    store_slug: str = Query("", min_length=0, max_length=255),
) -> Any:
    import main as _main  # noqa: PLC0415
    """Verify dashboard vs public-config vs visible storefront DOM (latest beacon)."""
    from services.store_identity_runtime_truth_v1 import (
        build_store_identity_runtime_truth_report,
    )
    from services.storefront_runtime_truth_gate_v1 import (
        merge_dom_truth_into_identity_report,
    )

    sf = (storefront_slug or store_slug or "").strip()
    if not sf:
        return j({"ok": False, "error": "storefront_slug_required"}, 400)
    try:
        _main._ensure_cartflow_api_db_warmed()
        dash_row = _main._dashboard_recovery_store_row()
        report = build_store_identity_runtime_truth_report(
            storefront_slug=sf,
            dashboard_store_row=dash_row,
        )
        if dash_row is not None:
            report = merge_dom_truth_into_identity_report(
                report,
                dashboard_store_row=dash_row,
                storefront_slug=sf,
            )
        return j(report)
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/widget-runtime-truth")
def dev_widget_runtime_truth(
    storefront_slug: str = Query("", min_length=0, max_length=255),
    store_slug: str = Query("", min_length=0, max_length=255),
) -> Any:
    import main as _main  # noqa: PLC0415
    """Verify widget enable/exit/hesitation/delay/frequency: dashboard vs public-config vs runtime."""
    from services.widget_settings_runtime_truth_v1 import (
        evaluate_widget_settings_runtime_truth,
    )

    sf = (storefront_slug or store_slug or "").strip()
    if not sf:
        return j({"ok": False, "error": "storefront_slug_required"}, 400)
    try:
        _main._ensure_cartflow_api_db_warmed()
        dash_row = _main._dashboard_recovery_store_row()
        report = evaluate_widget_settings_runtime_truth(
            dash_row,
            storefront_slug=sf,
        )
        return j(report)
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/recovery-truth")
def dev_recovery_truth(recovery_key: str = Query("", max_length=512)) -> Any:
    import main as _main  # noqa: PLC0415
    """
    Ordered proven transitions for one recovery_key (read-only debug).
    """
    rk = (recovery_key or "").strip()
    if not rk:
        return j({"ok": False, "error": "recovery_key_required"}, 400)
    try:
        _main._ensure_cartflow_api_db_warmed()
        from services.recovery_truth_timeline_v1 import (
            diagnose_timeline_persistence,
            get_recovery_truth_timeline,
        )

        timeline = get_recovery_truth_timeline(rk)
        persistence = diagnose_timeline_persistence(rk)
        return j(
            {
                "ok": True,
                "recovery_key": rk,
                "timeline": timeline,
                "persistence": persistence,
            }
        )
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/data-growth-measurement")
def dev_data_growth_measurement() -> Any:
    import main as _main  # noqa: PLC0415

    """
    Read-only platform data growth measurement (dev/admin diagnostic).

    Count metadata only — no snapshot payloads, no PII.
    """
    try:
        _main._ensure_cartflow_api_db_warmed()
        from services.data_growth_measurement_v1 import (  # noqa: PLC0415
            MEASUREMENT_WALL_BUDGET_MS,
            build_data_growth_measurement_report,
        )

        report = build_data_growth_measurement_report(db.session)
        return j(
            {
                "endpoint": "/dev/data-growth-measurement",
                "read_only": True,
                "wall_budget_ms": MEASUREMENT_WALL_BUDGET_MS,
                **report,
            }
        )
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/dashboard-snapshot-archive")
def dev_dashboard_snapshot_archive(
    run_tick: int = Query(0, ge=0, le=1),
) -> Any:
    import main as _main  # noqa: PLC0415

    """
    Dashboard snapshot archive diagnostics (Data Growth Governance Phase 3).

    ``run_tick=1`` executes one bounded archive tick when archive env is enabled.
    """
    try:
        _main._ensure_cartflow_api_db_warmed()
        from services.dashboard_snapshot_archive_v1 import (  # noqa: PLC0415
            assess_dashboard_snapshot_archive_status,
            run_dashboard_snapshot_archive_tick,
        )

        tick_result = None
        if run_tick == 1:
            tick_result = run_dashboard_snapshot_archive_tick()
        status = assess_dashboard_snapshot_archive_status(db.session)
        return j(
            {
                "endpoint": "/dev/dashboard-snapshot-archive",
                "read_only": run_tick != 1,
                **status,
                "tick_result": tick_result,
            }
        )
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/customer-movement-snapshot")
def dev_customer_movement_snapshot(
    recovery_key: str = Query("", max_length=512),
) -> Any:
    import main as _main  # noqa: PLC0415

    """Read-only movement snapshot for one recovery_key (shadow Phase 1)."""
    rk = (recovery_key or "").strip()
    if not rk:
        return j({"ok": False, "error": "recovery_key_required"}, 400)
    try:
        _main._ensure_cartflow_api_db_warmed()
        from services.customer_movement_snapshot_v1 import diagnose_movement_snapshot

        diag = diagnose_movement_snapshot(rk)
        return j({"ok": True, **diag})
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/attempt-2-trace")
def dev_attempt2_trace(recovery_key: str = Query("", max_length=512)) -> Any:
    import main as _main  # noqa: PLC0415
    """Durable attempt-2 schedule/dispatch snapshot for one recovery_key."""
    rk = (recovery_key or "").strip()
    if not rk:
        return j({"ok": False, "error": "recovery_key_required"}, 400)
    try:
        _main._ensure_cartflow_api_db_warmed()
        from services.recovery_attempt2_trace_v1 import (  # noqa: PLC0415
            build_attempt2_trace,
            emit_attempt2_trace_log,
        )

        trace = build_attempt2_trace(rk)
        emit_attempt2_trace_log(trace, path="dev_endpoint")
        return j({"ok": True, "trace": trace})
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/recovery-operational-truth")
def dev_recovery_operational_truth(recovery_key: str = Query("", max_length=512)) -> Any:
    import main as _main  # noqa: PLC0415
    """Unified runtime/dashboard operational truth from durable schedules."""
    rk = (recovery_key or "").strip()
    if not rk:
        return j({"ok": False, "error": "recovery_key_required"}, 400)
    try:
        _main._ensure_cartflow_api_db_warmed()
        from services.cartflow_session_truth import parse_recovery_key  # noqa: PLC0415
        from services.recovery_multi_message import (  # noqa: PLC0415
            diagnose_multi_message_config,
            resolve_configured_message_count,
        )
        from services.recovery_restart_survival import load_context  # noqa: PLC0415

        store_slug, session_part = parse_recovery_key(rk)
        store_slug = (store_slug or "").strip()[:255]
        session_part = (session_part or "").strip()[:512]
        if not store_slug or not session_part:
            return j({"ok": False, "error": "invalid_recovery_key"}, 400)

        session_id = session_part
        try:
            from services.journey_identity_resolver_v1 import has_stable_cart_id

            if has_stable_cart_id(session_part):
                ac_by_cart = (
                    db.session.query(AbandonedCart)
                    .filter(AbandonedCart.zid_cart_id == session_part)
                    .order_by(AbandonedCart.id.desc())
                    .first()
                )
                if ac_by_cart is not None:
                    sid_from_ac = (
                        getattr(ac_by_cart, "recovery_session_id", None) or ""
                    ).strip()[:512]
                    if sid_from_ac:
                        session_id = sid_from_ac
        except Exception:  # noqa: BLE001
            db.session.rollback()

        store_row = _main._fresh_store_row_for_recovery_templates(store_slug) or _main._load_store_row_for_recovery(
            store_slug
        )
        reason_tag = _main._reason_tag_for_session(store_slug, session_id)
        if not reason_tag:
            rr_any = _main._cart_recovery_reason_latest_row_any_store(session_id)
            reason_tag = (rr_any.reason or "").strip() if rr_any is not None else None
        reason_tag = (reason_tag or "").strip() or None

        ac_row = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.recovery_session_id == session_id)
            .order_by(AbandonedCart.id.desc())
            .first()
        )
        cart_id = (getattr(ac_row, "zid_cart_id", None) or "").strip() if ac_row else ""
        conds: list[Any] = [RecoverySchedule.store_slug == store_slug]
        if cart_id:
            conds.append(
                or_(
                    RecoverySchedule.session_id == session_id,
                    RecoverySchedule.cart_id == cart_id,
                )
            )
        else:
            conds.append(RecoverySchedule.session_id == session_id)
        sched_rows = (
            db.session.query(RecoverySchedule)
            .filter(*conds)
            .order_by(RecoverySchedule.step.asc(), RecoverySchedule.id.asc())
            .all()
        )
        rc_ctx: Optional[dict[str, Any]] = None
        if sched_rows:
            ctx0 = load_context(sched_rows[-1]).get("recovery_context")
            if isinstance(ctx0, dict):
                rc_ctx = dict(ctx0)
        configured_count, configured_source = resolve_configured_message_count(
            reason_tag,
            store_row,
            recovery_context=rc_ctx,
        )
        sent_count = _main._normal_recovery_gate_sent_count(rk, session_id, cart_id or None)
        next_due: Optional[datetime] = None
        schedule_rows_out: list[dict[str, Any]] = []
        blocked_by = "-"
        for sr in sched_rows:
            st = (getattr(sr, "status", None) or "").strip().lower()
            due = getattr(sr, "due_at", None)
            if due is not None:
                if due.tzinfo is None:
                    due = due.replace(tzinfo=timezone.utc)
                else:
                    due = due.astimezone(timezone.utc)
            if st in ("scheduled", "running") and due is not None:
                if next_due is None or due < next_due:
                    next_due = due
            schedule_rows_out.append(
                {
                    "id": int(getattr(sr, "id", 0) or 0),
                    "status": st,
                    "step": int(getattr(sr, "step", 1) or 1),
                    "sequential_attempt_index": getattr(sr, "sequential_attempt_index", None),
                    "multi_slot_index": getattr(sr, "multi_slot_index", None),
                    "due_at": due.isoformat() if due else None,
                    "created_at": (
                        sr.created_at.isoformat() if getattr(sr, "created_at", None) else None
                    ),
                }
            )
        dash_store = _main._dashboard_recovery_store_row()
        rows_dash, _ = _main._normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=200,
            page_offset=0,
            nr_session=session_id,
            nr_cart=cart_id or None,
            lifecycle="all",
            dash_store=dash_store,
        )
        dash_row = None
        for rr in rows_dash:
            if str(rr.get("recovery_key") or "").strip() == rk:
                dash_row = rr
                break
        dashboard_visible = dash_row is not None
        dashboard_bucket = (
            str(
                dash_row.get("merchant_cart_bucket")
                or dash_row.get("merchant_cart_primary_bucket")
                or dash_row.get("merchant_coarse_status")
                or ""
            )
            if dash_row
            else ""
        )
        from services.recovery_dashboard_inclusion_truth import (  # noqa: PLC0415
            build_recovery_dashboard_inclusion_truth,
        )

        inclusion = build_recovery_dashboard_inclusion_truth(
            recovery_key=rk,
            dash_store=dash_store,
            lifecycle="active",
        )
        td = diagnose_multi_message_config(reason_tag, store_row)
        if td.get("miss_reason"):
            blocked_by = str(td.get("miss_reason"))
        elif next_due is None and int(configured_count) > int(sent_count):
            blocked_by = "next_schedule_missing"
        decision = (
            "schedule_next"
            if int(configured_count) > int(sent_count)
            else "stop_sequence"
        )
        out = {
            "ok": True,
            "recovery_key": rk,
            "abandoned_cart_exists": ac_row is not None,
            "reason_tag": reason_tag,
            "configured_count": int(configured_count),
            "configured_count_source": configured_source,
            "sent_count": int(sent_count),
            "schedule_rows": schedule_rows_out,
            "dashboard_visible": dashboard_visible,
            "dashboard_bucket": dashboard_bucket,
            "dashboard_exclusion_reason": inclusion.get("dashboard_exclusion_reason"),
            "abandoned_cart_id": inclusion.get("abandoned_cart_id"),
            "store_id": inclusion.get("store_id"),
            "row_scope_match": inclusion.get("row_scope_match"),
            "excluded_by_filter": inclusion.get("excluded_by_filter"),
            "excluded_by_archive": inclusion.get("excluded_by_archive"),
            "excluded_by_tab": inclusion.get("excluded_by_tab"),
            "excluded_by_group_merge": inclusion.get("excluded_by_group_merge"),
            "selected_dashboard_row_id": inclusion.get("selected_dashboard_row_id"),
            "cart_recovery_reason_exists": inclusion.get("cart_recovery_reason_exists"),
            "recovery_schedule_row_count": inclusion.get("recovery_schedule_row_count"),
            "cart_recovery_log_sent_count": inclusion.get("cart_recovery_log_sent_count"),
            "next_attempt_due_at": next_due.isoformat() if next_due else None,
            "blocked_by": blocked_by,
            "decision": decision,
            "template_diagnosis": td,
        }
        return j(out)
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/snapshot-truth-diagnostics")
def dev_snapshot_truth_diagnostics(
    store_slug: str = Query("", max_length=255),
    cart_id: str = Query("", max_length=255),
    recovery_key: str = Query("", max_length=512),
    lifecycle: str = Query("active", max_length=32),
) -> Any:
    import main as _main  # noqa: PLC0415
    """Snapshot vs live-builder vs merchant dashboard truth for one cart."""
    ss = (store_slug or "").strip()[:255]
    cid = (cart_id or "").strip()[:255]
    rk = (recovery_key or "").strip()[:512]
    if not ss and not cid and not rk:
        return j(
            {"ok": False, "error": "store_slug_or_cart_id_or_recovery_key_required"},
            400,
        )
    try:
        _main._ensure_cartflow_api_db_warmed()
        from services.snapshot_truth_diagnostics_v1 import (  # noqa: PLC0415
            build_snapshot_truth_diagnostics,
        )

        return j(
            build_snapshot_truth_diagnostics(
                store_slug=ss,
                cart_id=cid,
                recovery_key=rk,
                lifecycle=(lifecycle or "active").strip()[:32],
            )
        )
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/dashboard-builder-parity")
def dev_dashboard_builder_parity(
    store_slug: str = Query("", max_length=255),
    cart_id: str = Query("", max_length=255),
    recovery_key: str = Query("", max_length=512),
    abandoned_cart_id: int = Query(0),
    lifecycle: str = Query("active", max_length=32),
    repair: bool = Query(False),
    measure_sizes: bool = Query(False),
) -> Any:
    """Live vs snapshot builder parity chain for one cart (governance diagnostic)."""
    import main as _main  # noqa: PLC0415

    ss = (store_slug or "").strip()[:255]
    cid = (cart_id or "").strip()[:255]
    rk = (recovery_key or "").strip()[:512]
    if not ss and not cid and not rk:
        return j(
            {"ok": False, "error": "store_slug_or_cart_id_or_recovery_key_required"},
            400,
        )
    try:
        _main._ensure_cartflow_api_db_warmed()
        from services.dashboard_builder_parity_v1 import build_dashboard_builder_parity  # noqa: PLC0415

        return j(
            build_dashboard_builder_parity(
                store_slug=ss,
                cart_id=cid,
                recovery_key=rk,
                abandoned_cart_id=int(abandoned_cart_id or 0) or None,
                lifecycle=(lifecycle or "active").strip()[:32],
                repair=bool(repair),
                measure_sizes=bool(measure_sizes),
            )
        )
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/normal-carts-payload-sizes")
def dev_normal_carts_payload_sizes(
    store_slug: str = Query("", max_length=255),
) -> Any:
    """Read-only live vs slim normal-carts payload byte sizes for one store."""
    import main as _main  # noqa: PLC0415

    ss = (store_slug or "").strip()[:255]
    if not ss:
        return j({"ok": False, "error": "store_slug_required"}, 400)
    try:
        _main._ensure_cartflow_api_db_warmed()
        from models import Store  # noqa: PLC0415
        from services.dashboard_snapshot_normal_carts_parity_v1 import (  # noqa: PLC0415
            build_canonical_normal_carts_payload,
        )
        from services.dashboard_snapshot_normal_carts_size_measure_v1 import (  # noqa: PLC0415
            measure_normal_carts_payload_sizes,
        )
        from services.dashboard_snapshot_v1 import canonical_snapshot_store_slug  # noqa: PLC0415

        slug = canonical_snapshot_store_slug(store_slug=ss)
        store = (
            db.session.query(Store)
            .filter(Store.zid_store_id == slug)
            .order_by(Store.id.desc())
            .first()
        )
        if store is None:
            return j({"ok": False, "error": "store_not_found", "store_slug": slug}, 404)
        body, _prof, perf = build_canonical_normal_carts_payload(store)
        report = measure_normal_carts_payload_sizes(body, store_slug=slug)
        report["ok"] = True
        report["visible_rows_built"] = int(getattr(perf, "visible_rows", 0) or 0)
        return j(report)
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/vip-merchant-alert-operational-truth")
def dev_vip_merchant_alert_operational_truth(
    cart_id: str = Query("", max_length=255),
    store_slug: str = Query("", max_length=255),
) -> Any:
    import main as _main  # noqa: PLC0415
    """Read-only VIP merchant alert delivery chain for one abandoned cart."""
    cid = (cart_id or "").strip()[:255]
    ss = (store_slug or "").strip()[:255]
    if not cid:
        return j({"ok": False, "error": "cart_id_required"}, 400)
    try:
        _main._ensure_cartflow_api_db_warmed()
        ac = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.zid_cart_id == cid)
            .order_by(AbandonedCart.id.desc())
            .first()
        )
        if ac is None:
            return j({"ok": False, "error": "abandoned_cart_not_found", "cart_id": cid}, 404)
        store_alert = _main._resolve_store_for_vip_merchant_alert(ac)
        ss_eff = ss or (
            str(getattr(store_alert, "zid_store_id", None) or "").strip()[:255]
            if store_alert is not None
            else ""
        )
        sid = (getattr(ac, "recovery_session_id", None) or "").strip()[:512]
        phone, phone_src, normalized_phone = resolve_vip_alert_destination(store_alert)
        notify_on = merchant_vip_notify_enabled(store_alert)
        in_lane = abandoned_cart_in_vip_operational_lane(ac, store_alert)
        alert_logs = (
            db.session.query(CartRecoveryLog)
            .filter(
                CartRecoveryLog.cart_id == cid,
                CartRecoveryLog.reason_tag == VIP_MERCHANT_ALERT_REASON_TAG,
            )
            .order_by(CartRecoveryLog.id.desc())
            .limit(5)
            .all()
        )
        logs_out = [
            {
                "id": int(getattr(lg, "id", 0) or 0),
                "status": str(getattr(lg, "status", "") or ""),
                "phone": str(getattr(lg, "phone", "") or ""),
                "message_preview": (str(getattr(lg, "message", "") or ""))[:200],
                "sent_at": (
                    lg.sent_at.isoformat() if getattr(lg, "sent_at", None) else None
                ),
                "provider_message_sid": str(getattr(lg, "provider_message_sid", "") or ""),
            }
            for lg in alert_logs
        ]
        latest_sid = (
            str(logs_out[0].get("provider_message_sid") or "").strip()
            if logs_out
            else ""
        )
        delivery_truth_row = None
        if latest_sid:
            from services.whatsapp_delivery_truth_v1 import get_delivery_truth  # noqa: PLC0415

            delivery_truth_row = get_delivery_truth(latest_sid)
        delivery_summary = vip_alert_delivery_summary(delivery_truth_row)
        return j(
            {
                "ok": True,
                "cart_id": cid,
                "store_slug": ss_eff,
                "session_id": sid,
                "abandoned_cart_id": int(getattr(ac, "id", 0) or 0),
                "cart_value": float(getattr(ac, "cart_value", 0) or 0),
                "vip_mode": bool(getattr(ac, "vip_mode", False)),
                "vip_operational_lane": in_lane,
                "vip_threshold": getattr(store_alert, "vip_cart_threshold", None),
                "vip_notify_enabled": notify_on,
                "merchant_phone": phone,
                "merchant_phone_source": phone_src,
                "destination_type": phone_src,
                "normalized_destination_phone": normalized_phone,
                "store_id": getattr(store_alert, "id", None),
                "merchant_alert_log_rows": logs_out,
                "latest_alert_status": logs_out[0]["status"] if logs_out else None,
                "latest_provider_message_sid": latest_sid or None,
                "delivery_truth": delivery_summary,
                "delivered_to_device": delivery_summary.get("delivered_to_device"),
            }
        )
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/lifecycle-truth-check")
def dev_lifecycle_truth_check(recovery_key: str = Query("", max_length=512)) -> Any:
    import main as _main  # noqa: PLC0415
    rk = (recovery_key or "").strip()
    if not rk:
        return j({"ok": False, "error": "recovery_key_required"}, 400)
    try:
        _main._ensure_cartflow_api_db_warmed()
        from services.customer_lifecycle_states_v1 import (  # noqa: PLC0415
            lifecycle_state_to_filter_bucket,
            lifecycle_truth_consistency_for_row,
        )
        from services.recovery_truth_timeline_v1 import (  # noqa: PLC0415
            get_recovery_truth_timeline,
            timeline_status_set,
        )

        dash_store = _main._dashboard_recovery_store_row()
        rows, _prof = _main._normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=200,
            page_offset=0,
            lifecycle="all",
            dash_store=dash_store,
        )
        row = None
        for cand in rows:
            if str(cand.get("recovery_key") or "").strip() == rk:
                row = cand
                break
        timeline = get_recovery_truth_timeline(rk)
        timeline_statuses = sorted(timeline_status_set(rk))
        if row is None:
            return j(
                {
                    "ok": True,
                    "recovery_key": rk,
                    "timeline": timeline,
                    "customer_lifecycle_state": None,
                    "dashboard_tab": None,
                    "dashboard_chip": None,
                    "archive_state": None,
                    "count_bucket": None,
                    "consistent": False,
                    "reason": "recovery_key_not_present_in_dashboard_rows",
                }
            )
        state = str(row.get("customer_lifecycle_state") or "").strip().lower()
        tab = lifecycle_state_to_filter_bucket(state)
        chip = str(
            row.get("customer_lifecycle_label_ar")
            or row.get("merchant_status_label_ar")
            or ""
        ).strip()
        archive_state = (
            "archived" if bool(row.get("customer_lifecycle_is_archived_visual")) else "active"
        )
        bucket = str(row.get("merchant_cart_bucket") or "").strip().lower() or None
        consistent, reason = lifecycle_truth_consistency_for_row(row)
        return j(
            {
                "ok": True,
                "recovery_key": rk,
                "timeline": timeline,
                "timeline_statuses": timeline_statuses,
                "customer_lifecycle_state": state or None,
                "dashboard_tab": tab,
                "dashboard_chip": chip or None,
                "archive_state": archive_state,
                "count_bucket": bucket,
                "consistent": bool(consistent),
                "reason": reason,
            }
        )
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/merchant-truth-trace")
def dev_merchant_truth_trace(recovery_key: str = Query("", max_length=512)) -> Any:
    import main as _main  # noqa: PLC0415
    rk = (recovery_key or "").strip()
    if not rk:
        return j({"ok": False, "error": "recovery_key_required"}, 400)
    try:
        _main._ensure_cartflow_api_db_warmed()
        from services.recovery_truth_timeline_v1 import (  # noqa: PLC0415
            get_recovery_truth_timeline,
            timeline_status_set,
        )
        from services.recovery_truth_timeline_v1 import parse_recovery_key as _parse_rk  # noqa: PLC0415
        from services.customer_lifecycle_states_v1 import (  # noqa: PLC0415
            attach_customer_lifecycle_state_v1,
            lifecycle_state_to_filter_bucket,
        )
        from models import AbandonedCart, CartRecoveryReason, Store  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return j({"ok": False, "error": str(exc)}, 500)

    try:
        store_slug, session_id = _parse_rk(rk)
        store_slug = (store_slug or "").strip()[:255]
        session_id = (session_id or "").strip()[:512]

        dash_store = None
        if store_slug:
            dash_store = (
                db.session.query(Store)
                .filter(Store.zid_store_id == store_slug)
                .order_by(Store.id.desc())
                .first()
            )

        # AbandonedCart row probe (best-effort: latest row for this session in this store).
        ac_row = None
        if session_id:
            q = db.session.query(AbandonedCart).filter(
                AbandonedCart.recovery_session_id == session_id
            )
            if dash_store is not None and getattr(dash_store, "id", None) is not None:
                q = q.filter(AbandonedCart.store_id == int(dash_store.id))
            ac_row = q.order_by(AbandonedCart.id.desc()).first()

        ac_id = int(getattr(ac_row, "id", 0) or 0) or None
        ac_cart_id = (getattr(ac_row, "zid_cart_id", None) or "").strip()[:255] if ac_row else ""
        ac_cart_value = float(getattr(ac_row, "cart_value", 0.0) or 0.0) if ac_row else None
        ac_created_at = getattr(ac_row, "created_at", None) if ac_row else None
        ac_updated_at = getattr(ac_row, "updated_at", None) if ac_row else None
        ac_last_seen_at = getattr(ac_row, "last_seen_at", None) if ac_row else None
        ac_store_id = getattr(ac_row, "store_id", None) if ac_row else None

        raw_payload = {}
        try:
            raw_payload = getattr(ac_row, "raw_payload", None) if ac_row is not None else None
            raw_payload = raw_payload if isinstance(raw_payload, dict) else {}
        except Exception:  # noqa: BLE001
            raw_payload = {}
        payload_cart_total = None
        try:
            if "cart_total" in raw_payload and raw_payload.get("cart_total") is not None:
                payload_cart_total = float(raw_payload.get("cart_total"))
        except (TypeError, ValueError):
            payload_cart_total = None

        # Reason tag probe
        reason_tag = None
        try:
            rr = (
                db.session.query(CartRecoveryReason)
                .filter(
                    CartRecoveryReason.store_slug == store_slug,
                    CartRecoveryReason.session_id == session_id,
                )
                .order_by(CartRecoveryReason.updated_at.desc())
                .first()
            )
            reason_tag = (getattr(rr, "reason", None) or "").strip().lower()[:64] if rr else None
        except Exception:  # noqa: BLE001
            db.session.rollback()

        timeline = get_recovery_truth_timeline(rk)
        statuses = sorted(timeline_status_set(rk))

        # Dashboard row probe (use the same normal-carts builder, but scope store from recovery_key).
        dash_rows, _prof = _main._normal_recovery_merchant_lightweight_alert_list_for_api(
            page_limit=220,
            page_offset=0,
            lifecycle="all",
            dash_store=dash_store,
            nr_session=session_id or None,
        )
        dash_row = None
        for r in dash_rows:
            if str(r.get("recovery_key") or "").strip() == rk:
                dash_row = r
                break
        dash_cart_value = (
            float(dash_row.get("merchant_cart_value") or 0.0) if isinstance(dash_row, dict) else None
        )
        dash_bucket = (
            str(dash_row.get("merchant_cart_bucket") or "").strip().lower()
            if isinstance(dash_row, dict)
            else None
        )
        dash_row_id = (
            int(dash_row.get("merchant_case_row_id") or 0) or None
            if isinstance(dash_row, dict)
            else None
        )
        dash_archive_flag = (
            bool(dash_row.get("customer_lifecycle_is_archived_visual"))
            if isinstance(dash_row, dict)
            else False
        )

        lifecycle_state = None
        lifecycle_bucket = None
        if isinstance(dash_row, dict):
            lifecycle_state = str(dash_row.get("customer_lifecycle_state") or "").strip().lower() or None
            lifecycle_bucket = lifecycle_state_to_filter_bucket(lifecycle_state or "")
        else:
            # Fallback: compute lifecycle from evidence even if row missing.
            tmp: dict[str, Any] = {}
            attach_customer_lifecycle_state_v1(
                tmp,
                recovery_key=rk,
                phase_key="",
                coarse="",
                sent_count=0,
                log_statuses=None,
                behavioral=None,
                purchase_truth=False,
                cart_status="",
                merchant_archived=False,
                terminal_history_archived=False,
                is_vip_lane=False,
                has_phone=True,
            )
            lifecycle_state = str(tmp.get("customer_lifecycle_state") or "").strip().lower() or None
            lifecycle_bucket = lifecycle_state_to_filter_bucket(lifecycle_state or "")

        # Consistency checks (no behavior change; logs only)
        consistent = True
        reasons: list[str] = []
        if dash_row is None:
            consistent = False
            reasons.append("dashboard_row_missing_for_recovery_key")
        else:
            dash_rk = str(dash_row.get("recovery_key") or "").strip()
            if dash_rk != rk:
                consistent = False
                reasons.append("dashboard_recovery_key_mismatch")
            # Compare cart totals across layers (prefer payload cart_total if present, else AbandonedCart.cart_value).
            latest_total = payload_cart_total if payload_cart_total is not None else ac_cart_value
            if latest_total is not None and dash_cart_value is not None:
                if abs(float(dash_cart_value) - float(latest_total)) > 0.0001:
                    consistent = False
                    reasons.append("dashboard_cart_total_mismatch")
        # Enforce bucket equality (tab==bucket) when row exists.
        if dash_row is not None and lifecycle_bucket and dash_bucket and lifecycle_bucket != dash_bucket:
            consistent = False
            reasons.append("dashboard_bucket_mismatch_vs_lifecycle")

        try:
            msg = (
                "[MERCHANT TRUTH] "
                f"cart_total={dash_cart_value if dash_cart_value is not None else '-'} "
                f"cart_id={(ac_cart_id or '-')[:80]} "
                f"session_id={(session_id or '-')[:80]} "
                f"recovery_key={(rk or '-')[:200]} "
                f"dashboard_row={dash_row_id if dash_row_id is not None else '-'} "
                f"bucket={dash_bucket or '-'} "
                f"consistent={'true' if consistent else 'false'}"
            )
            print(msg, flush=True)
            log.info("%s", msg)
        except Exception:  # noqa: BLE001
            pass
        if not consistent:
            try:
                vmsg = "[MERCHANT TRUTH VIOLATION] " + " ".join(reasons)[:500]
                print(vmsg, flush=True)
                log.warning("%s", vmsg)
            except Exception:  # noqa: BLE001
                pass

        def _iso(dt: Any) -> Any:
            try:
                if dt is None:
                    return None
                return dt.isoformat()
            except Exception:
                return None

        return j(
            {
                "ok": True,
                "store_slug": store_slug or None,
                "session_id": session_id or None,
                "cart_id": ac_cart_id or None,
                "recovery_key": rk,
                "cart_total": payload_cart_total if payload_cart_total is not None else ac_cart_value,
                "cart_total_source": (
                    "abandoned_cart.raw_payload.cart_total"
                    if payload_cart_total is not None
                    else "abandoned_cart.cart_value"
                )
                if (payload_cart_total is not None or ac_cart_value is not None)
                else None,
                "reason_tag": reason_tag,
                "abandoned_cart_id": ac_id,
                "abandoned_cart_store_id": int(ac_store_id) if ac_store_id is not None else None,
                "timeline_statuses": statuses,
                "timeline": timeline,
                "customer_lifecycle_state": lifecycle_state,
                "dashboard_bucket": dash_bucket,
                "dashboard_row_id": dash_row_id,
                "archive_flag": bool(dash_archive_flag),
                "created_at": _iso(ac_created_at),
                "updated_at": _iso(ac_updated_at),
                "last_seen_at": _iso(ac_last_seen_at),
                "dashboard_cart_value": dash_cart_value,
                "dashboard_row_recovery_key": (
                    str(dash_row.get("recovery_key") or "").strip()
                    if isinstance(dash_row, dict)
                    else None
                ),
                "consistent": bool(consistent),
                "reason": ",".join(reasons) if reasons else "ok",
            }
        )
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(exc)}, 500)


@router.get("/dev/recovery-health")
def dev_recovery_health() -> Any:
    import main as _main  # noqa: PLC0415
    """
    Read-only recovery / worker health (v1). Allowed in production.
    No recovery behavior changes.
    """
    from services.recovery_health_v1 import build_recovery_health_snapshot

    try:
        _main._ensure_cartflow_api_db_warmed()
        return j(build_recovery_health_snapshot())
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "health": "warning", "error": str(exc)}, 500)


@router.get("/dev/recovery-delay-verify")
def dev_recovery_delay_verify():
    import main as _main  # noqa: PLC0415
    """
    استيثاق تأثير ‎recovery_delay‎: سكون ‎2‎ د مع حد ‎1‎ د ‎=‎ يُرسل، مع حد ‎5‎ د ‎=‎ لا.
    ‎Store‎ مُمثّل بـ ‎SimpleNamespace‎ (نفس حقول ‎Store.recovery_*‎).
    """
    now = datetime.now(timezone.utc)
    last = now - timedelta(minutes=2)
    store_fast = SimpleNamespace(
        recovery_delay=1,
        recovery_delay_unit="minutes",
        recovery_attempts=1,
    )
    store_slow = SimpleNamespace(
        recovery_delay=5,
        recovery_delay_unit="minutes",
        recovery_attempts=1,
    )
    return j(
        {
            "ok": True,
            "case_fast": {
                "should_send": should_send_whatsapp(
                    last,
                    user_returned_to_site=False,
                    now=now,
                    store=store_fast,
                )
            },
            "case_slow": {
                "should_send": should_send_whatsapp(
                    last,
                    user_returned_to_site=False,
                    now=now,
                    store=store_slow,
                )
            },
        }
    )


@router.get("/dev/recovery-attempts-verify")
def dev_recovery_attempts_verify():
    import main as _main  # noqa: PLC0415
    """
    سلة ثابتة: ‎sent_count=0‎ ثم ‎1‎ مع ‎recovery_attempts=1‎ — ‎should_send_whatsapp‎ فقط، بدون واتساب.
    """
    now = datetime.now(timezone.utc)
    last = now - timedelta(minutes=3)
    store = SimpleNamespace(
        recovery_delay=2,
        recovery_delay_unit="minutes",
        recovery_attempts=1,
    )
    return j(
        {
            "ok": True,
            "first_attempt": {
                "should_send": should_send_whatsapp(
                    last,
                    user_returned_to_site=False,
                    now=now,
                    store=store,
                    sent_count=0,
                )
            },
            "second_attempt": {
                "should_send": should_send_whatsapp(
                    last,
                    user_returned_to_site=False,
                    now=now,
                    store=store,
                    sent_count=1,
                )
            },
        }
    )


@router.get("/dev/recovery-unit-verify")
def dev_recovery_unit_verify():
    import main as _main  # noqa: PLC0415
    """
    تحويل ‎recovery_delay_unit‎ (دقائق / ساعات / أيام) عبر ‎should_send_whatsapp‎ — بدون واتساب.
    """
    now = datetime.now(timezone.utc)
    last_minutes = now - timedelta(minutes=2)
    last_hours = now - timedelta(minutes=30)
    last_days = now - timedelta(hours=2)
    st_m = SimpleNamespace(
        recovery_delay=1,
        recovery_delay_unit="minutes",
        recovery_attempts=1,
    )
    st_h = SimpleNamespace(
        recovery_delay=1,
        recovery_delay_unit="hours",
        recovery_attempts=1,
    )
    st_d = SimpleNamespace(
        recovery_delay=1,
        recovery_delay_unit="days",
        recovery_attempts=1,
    )
    return j(
        {
            "ok": True,
            "minutes_case": {
                "should_send": should_send_whatsapp(
                    last_minutes,
                    user_returned_to_site=False,
                    now=now,
                    store=st_m,
                    sent_count=0,
                )
            },
            "hours_case": {
                "should_send": should_send_whatsapp(
                    last_hours,
                    user_returned_to_site=False,
                    now=now,
                    store=st_h,
                    sent_count=0,
                )
            },
            "days_case": {
                "should_send": should_send_whatsapp(
                    last_days,
                    user_returned_to_site=False,
                    now=now,
                    store=st_d,
                    sent_count=0,
                )
            },
        }
    )


@router.get("/dev/recovery-dashboard-render-test")
def dev_recovery_dashboard_render_test():
    import main as _main  # noqa: PLC0415
    """
    يتحقق من مسار ‎/dashboard‎ (تطبيق التاجر) وأن الرد ‎HTML‎.
    """
    try:
        route_exists = _main._app_route_get_exists("/dashboard")
        tc = _main._app_test_client()
        resp = tc.get("/dashboard")
        head = (resp.content or b"")[:3000]
        head_l = head.lstrip().lower()
        ct = (resp.headers.get("Content-Type") or "").lower()
        returns_html = bool(
            resp.status_code == 200
            and "text/html" in ct
            and (
                head_l.startswith(b"<!doctype")
                or head_l.startswith(b"<html")
            )
        )
        ok = bool(
            route_exists
            and returns_html
            and b"data-cf-merchant-app" in head_l
        )
        return j(
            {
                "ok": ok,
                "route_exists": route_exists,
                "returns_html": returns_html,
            }
        )
    except Exception as e:  # noqa: BLE001
        return j(
            {
                "ok": False,
                "error": str(e),
                "route_exists": False,
                "returns_html": False,
            },
            500,
        )


@router.get("/dev/recovery-logs/{store_slug}")
def dev_recovery_logs(store_slug: str) -> Any:
    import main as _main  # noqa: PLC0415
    """آخر ‎20‎ سجل استرجاع لجلسة حسب ‎store_slug‎ (تجارب فقط، ‎ENV=development‎)."""
    try:
        db.create_all()
        slug = (store_slug or "").strip()
        rows = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.store_slug == slug)
            .order_by(CartRecoveryLog.created_at.desc())
            .limit(20)
            .all()
        )

        def _iso(dt: Optional[datetime]) -> Optional[str]:
            if dt is None:
                return None
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc).isoformat()
            return dt.isoformat()

        return j(
            {
                "ok": True,
                "store_slug": slug,
                "logs": [
                    {
                        "id": r.id,
                        "store_slug": r.store_slug,
                        "session_id": r.session_id,
                        "cart_id": r.cart_id,
                        "phone": r.phone,
                        "message": r.message,
                        "status": r.status,
                        "step": r.step,
                        "created_at": _iso(r.created_at),
                        "sent_at": _iso(r.sent_at),
                    }
                    for r in rows
                ],
            }
        )
    except Exception as e:  # noqa: BLE001
        db.session.rollback()
        return j({"ok": False, "error": str(e)}, 500)


@router.get("/dev/test-widget-identity-trace")
def dev_test_widget_identity_trace(
    store_slug: str = Query("", max_length=255),
    session_id: str = Query("", max_length=512),
    cart_id: str = Query("", max_length=255),
) -> Any:
    import main as _main  # noqa: PLC0415
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    cid = (cart_id or "").strip()[:255]
    if not ss or not sid:
        return j(
            {"ok": False, "error": "store_slug_and_session_id_required"},
            400,
        )
    rk = _main._recovery_key_from_store_and_session(ss, sid)
    flags = _main._test_widget_identity_truth_flags(
        store_slug=ss,
        session_id=sid,
        cart_id=cid,
        recovery_key=rk,
    )
    reusable, reason = _main._test_widget_identity_is_reusable(flags)
    return j(
        {
            "ok": True,
            "store_slug": ss,
            "session_id": sid,
            "cart_id": cid or None,
            "recovery_key": rk,
            "lifecycle_truth_flags": flags,
            "identity_reusable": reusable,
            "identity_reuse_reason": reason,
        }
    )


@router.get("/dev/run-flow")
def dev_run_flow():
    from routes.ops import get_mock_abandoned_cart

    cart = get_mock_abandoned_cart()
    message = build_abandoned_cart_message(cart)
    return j(
        {
            "cart": cart,
            "message": message,
        }
    )


@router.get("/dev/whatsapp-message-test")
def dev_whatsapp_message_test():
    import main as _main  # noqa: PLC0415

    c = _main._WHATSAPP_TEST_CART
    return j(
        {
            "new_price": build_whatsapp_recovery_message("new", "price", c),
            "new_quality": build_whatsapp_recovery_message("new", "quality", c),
            "returning_price": build_whatsapp_recovery_message("returning", "price", c),
            "returning_quality": build_whatsapp_recovery_message("returning", "quality", c),
        }
    )


@router.get("/dev/should-send-test")
def dev_should_send_test():
    # محاكاة: نشاط حديث (< دقيقتين) مقابل سكون ≥ دقيقتين
    now = datetime.now(timezone.utc)
    recent = should_send_whatsapp(now - timedelta(minutes=1), now=now)
    idle = should_send_whatsapp(now - timedelta(minutes=3), now=now)
    return j({"recent": recent, "idle": idle})


@router.get("/dev/recovery-timing-test")
def dev_recovery_timing_test():
    """
    أزمنة ‎should_send_whatsapp‎ فقط (بدون واتساب) — للتجارب.
    """
    now = datetime.now(timezone.utc)
    last_recent = now - timedelta(minutes=1)
    last_idle = now - timedelta(minutes=3)
    return j(
        {
            "ok": True,
            "cases": {
                "recent_activity": {
                    "should_send": should_send_whatsapp(
                        last_recent, user_returned_to_site=False, now=now
                    ),
                },
                "idle_activity": {
                    "should_send": should_send_whatsapp(
                        last_idle, user_returned_to_site=False, now=now
                    ),
                },
            },
        }
    )


@router.get("/dev/recovery-duplicate-test")
def dev_recovery_duplicate_test():
    """
    تكرار لنفس «السلة»: المحاولة الأولى — سكون ≥ دقيقتين يُسمح بالإرسال.
    بعدها نُمثّل تسجيل لمسة/إرسال (آخر نشاط = ‎now‎) فينخفض الإرسال لاحقاً بمنطق ‎should_send_whatsapp‎ فقط.
    """
    now = datetime.now(timezone.utc)
    first_last = now - timedelta(minutes=3)
    first = should_send_whatsapp(
        first_last, user_returned_to_site=False, now=now
    )
    # محاكاة: نفس السلة لكن بعد تسجيل الاسترجاع «آخر نشاط» = الآن (ضمن ‎2‎ د) → لا إرسال ثانٍ
    second = should_send_whatsapp(now, user_returned_to_site=False, now=now)
    return j(
        {
            "ok": True,
            "first_attempt": {
                "should_send": first,
            },
            "second_attempt": {
                "should_send": second,
            },
        }
    )

