# -*- coding: utf-8 -*-
"""Diagnostic: dashboard vs runtime Store row and reason_templates source (read-only)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import RecoverySchedule, Store
from services.reason_template_recovery import canonical_reason_template_key
from services.recovery_multi_message import resolve_recovery_schedule_timing
from services.recovery_store_lookup import CARTFLOW_DEFAULT_RECOVERY_STORE_ZID
from services.store_reason_templates import parse_reason_templates_column

WIDGET_SLUGS = ("demo", "demo2", "default", CARTFLOW_DEFAULT_RECOVERY_STORE_ZID)


def _dt_iso(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.isoformat() + "Z"
        return val.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(val)


def _store_row_summary(row: Optional[Any], *, reason: str) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    canon = canonical_reason_template_key(reason) or (reason or "").strip().lower()
    raw_rt = getattr(row, "reason_templates_json", None)
    has_json = isinstance(raw_rt, str) and bool(raw_rt.strip())
    other_mc: Optional[int] = None
    other_delay: Any = None
    other_unit: Optional[str] = None
    other_text: Optional[str] = None
    if has_json:
        try:
            parsed = parse_reason_templates_column(raw_rt)
            ent = parsed.get(canon) if canon else None
            if isinstance(ent, dict):
                other_mc = ent.get("message_count")
                msgs = ent.get("messages")
                if isinstance(msgs, list) and msgs and isinstance(msgs[0], dict):
                    other_delay = msgs[0].get("delay")
                    other_unit = msgs[0].get("unit")
                    txt = msgs[0].get("text")
                    if isinstance(txt, str):
                        other_text = txt[:200]
                elif ent.get("message"):
                    other_text = str(ent.get("message"))[:200]
        except Exception:  # noqa: BLE001
            pass
    return {
        "id": getattr(row, "id", None),
        "zid_store_id": (getattr(row, "zid_store_id", None) or "").strip() or None,
        "created_at": _dt_iso(getattr(row, "created_at", None)),
        "updated_at": _dt_iso(getattr(row, "updated_at", None)),
        "has_reason_templates_json": has_json,
        "reason_canon": canon,
        "other_message_count": other_mc,
        "other_delay": other_delay,
        "other_unit": other_unit,
        "other_text": other_text,
    }


def _collect_candidate_store_rows(store_slug: str) -> List[Store]:
    ss = (store_slug or "").strip()
    zids = set(WIDGET_SLUGS)
    if ss:
        zids.add(ss)
    try:
        latest = db.session.query(Store).order_by(Store.id.desc()).first()
        if latest is not None:
            z = (getattr(latest, "zid_store_id", None) or "").strip()
            if z:
                zids.add(z)
        filters: list[Any] = [Store.zid_store_id.in_(sorted(zids))]
        if ss:
            filters.append(Store.zid_store_id.ilike(f"{ss}%"))
        rows = (
            db.session.query(Store)
            .filter(or_(*filters))
            .order_by(Store.id.desc())
            .all()
        )
        if not rows and latest is not None:
            rows = [latest]
        return rows
    except SQLAlchemyError:
        db.session.rollback()
        return []


def _scoped_cache_state(store_slug: str) -> Dict[str, Any]:
    try:
        from services.cart_event_request_scope import (
            cart_event_scope_active,
            scoped_store_contains,
            scoped_store_get,
        )

        ck = f"zid:{(store_slug or '').strip()}"
        active = cart_event_scope_active()
        hit = active and scoped_store_contains(ck)
        cached = scoped_store_get(ck) if hit else None
        cached_zid = None
        cached_id = None
        if cached is not None:
            cached_zid = (getattr(cached, "zid_store_id", None) or "").strip() or None
            cached_id = getattr(cached, "id", None)
        return {
            "cart_event_scope_active": active,
            "cache_key": ck,
            "scoped_store_cache_hit": hit,
            "scoped_cached_store_id": cached_id,
            "scoped_cached_zid": cached_zid,
        }
    except Exception:  # noqa: BLE001
        return {
            "cart_event_scope_active": False,
            "cache_key": f"zid:{store_slug}",
            "scoped_store_cache_hit": False,
            "note": "scope_unavailable_outside_cart_event_request",
        }


def _explain_selection(
    *,
    store_slug: str,
    dashboard_id: Optional[int],
    dashboard_zid: Optional[str],
    runtime_id: Optional[int],
    runtime_zid: Optional[str],
    fresh_id: Optional[int],
    fresh_zid: Optional[str],
    rows_match: bool,
    fresh_matches_runtime: bool,
    fresh_matches_dashboard: bool,
    pending_schedules: int,
) -> str:
    parts: List[str] = []
    if dashboard_id is not None and runtime_id is not None and dashboard_id != runtime_id:
        parts.append(
            "A) dashboard and runtime resolve DIFFERENT Store rows "
            f"(dashboard id={dashboard_id} zid={dashboard_zid!r}; "
            f"runtime id={runtime_id} zid={runtime_zid!r})."
        )
    elif rows_match:
        parts.append(
            "A) dashboard and runtime resolve the SAME Store row "
            f"(id={runtime_id}, zid={runtime_zid!r})."
        )
    else:
        parts.append("A) could not compare dashboard vs runtime row ids.")

    if fresh_id is not None and runtime_id is not None and fresh_id == runtime_id:
        parts.append(
            "B) _fresh_store_row_for_recovery_templates matches runtime canonical lookup."
        )
    elif fresh_id is not None and runtime_id is not None and fresh_id != runtime_id:
        parts.append(
            "B) _fresh_store_row_for_recovery_templates differs from runtime row "
            f"(fresh id={fresh_id} vs runtime id={runtime_id}) — check scoped cache or race."
        )

    if dashboard_zid and store_slug and dashboard_zid.casefold() != store_slug.casefold():
        parts.append(
            "C) dashboard canonical Store zid does not match requested store_slug — "
            "check store_slug query/body on GET/POST trigger-templates."
        )
    elif dashboard_zid and store_slug and dashboard_zid.casefold() == store_slug.casefold():
        parts.append("C) dashboard canonical row zid matches requested store_slug.")

    if not fresh_matches_dashboard and dashboard_id and fresh_id and dashboard_id != fresh_id:
        parts.append(
            "D) provision/mirror path may have created a separate demo row; "
            "dashboard saves to latest id while recovery reads canonical zid row."
        )
    if pending_schedules > 0:
        parts.append(
            f"Note: {pending_schedules} recovery_schedules row(s) for this slug — "
            "resume uses context_json snapshot, not live DB."
        )
    if not parts:
        return "No divergence detected; compare other_* fields per candidate row."
    return " ".join(parts)


def build_store_template_debug_report(
    *,
    store_slug: str = "demo",
    reason: str = "other",
) -> Dict[str, Any]:
    """
    Read-only report: same fields dashboard GET /api/dashboard/trigger-templates
    vs runtime recovery template timing resolution.
    """
    ss = (store_slug or "demo").strip()[:255]
    rt = (reason or "other").strip()[:64]
    recovery_key = f"{ss}:template-debug"

    try:
        db.create_all()
        from main import (  # noqa: PLC0415
            _fresh_store_row_for_recovery_templates,
            _recovery_store_from_context,
        )
        from services.dashboard_store_context import dashboard_canonical_store_row
        from services.recovery_store_lookup import resolve_recovery_store_row_canonical

        dash_row = dashboard_canonical_store_row(ss, allow_schema_warm=True)
        runtime_row = resolve_recovery_store_row_canonical(ss, allow_schema_warm=True)
        fresh_row = _fresh_store_row_for_recovery_templates(ss)
        ctx_row = _recovery_store_from_context(
            {"recovery_key": recovery_key, "store_slug": ss},
            store_slug=ss,
            allow_schema_warm=True,
        )

        dash_id = getattr(dash_row, "id", None) if dash_row else None
        dash_zid = (getattr(dash_row, "zid_store_id", None) or "").strip() if dash_row else None
        run_id = getattr(runtime_row, "id", None) if runtime_row else None
        run_zid = (getattr(runtime_row, "zid_store_id", None) or "").strip() if runtime_row else None
        fresh_id = getattr(fresh_row, "id", None) if fresh_row else None
        fresh_zid = (getattr(fresh_row, "zid_store_id", None) or "").strip() if fresh_row else None
        ctx_id = getattr(ctx_row, "id", None) if ctx_row else None
        ctx_zid = (getattr(ctx_row, "zid_store_id", None) or "").strip() if ctx_row else None

        timing_runtime = None
        if runtime_row is not None:
            timing_runtime = resolve_recovery_schedule_timing(
                rt,
                runtime_row,
                stage_index=0,
                recovery_key=recovery_key,
                path="store_template_debug",
            )
        timing_fresh = None
        if fresh_row is not None and (fresh_id != run_id):
            timing_fresh = resolve_recovery_schedule_timing(
                rt,
                fresh_row,
                stage_index=0,
                recovery_key=recovery_key,
                path="store_template_debug_fresh",
            )
        timing_dashboard = None
        if dash_row is not None and dash_id != run_id:
            timing_dashboard = resolve_recovery_schedule_timing(
                rt,
                dash_row,
                stage_index=0,
                recovery_key=recovery_key,
                path="store_template_debug_dashboard",
            )

        candidates = _collect_candidate_store_rows(ss)
        candidate_summaries = [_store_row_summary(r, reason=rt) for r in candidates]

        pending_n = 0
        try:
            pending_n = (
                db.session.query(RecoverySchedule)
                .filter(
                    RecoverySchedule.store_slug == ss,
                    RecoverySchedule.status.in_(("scheduled", "running")),
                )
                .count()
            )
        except SQLAlchemyError:
            db.session.rollback()

        rows_match = (
            dash_id is not None
            and run_id is not None
            and int(dash_id) == int(run_id)
        )
        fresh_matches_runtime = (
            fresh_id is not None
            and run_id is not None
            and int(fresh_id) == int(run_id)
        )
        fresh_matches_dashboard = (
            fresh_id is not None
            and dash_id is not None
            and int(fresh_id) == int(dash_id)
        )

        explanation = _explain_selection(
            store_slug=ss,
            dashboard_id=dash_id,
            dashboard_zid=dash_zid,
            runtime_id=run_id,
            runtime_zid=run_zid,
            fresh_id=fresh_id,
            fresh_zid=fresh_zid,
            rows_match=rows_match,
            fresh_matches_runtime=fresh_matches_runtime,
            fresh_matches_dashboard=fresh_matches_dashboard,
            pending_schedules=pending_n,
        )

        return {
            "ok": True,
            "store_slug": ss,
            "reason": rt,
            "reason_canon": canonical_reason_template_key(rt) or rt,
            "recovery_key_probe": recovery_key,
            "dashboard_store_id": dash_id,
            "dashboard_store_zid": dash_zid,
            "dashboard_row": _store_row_summary(dash_row, reason=rt),
            "runtime_store_id": run_id,
            "runtime_store_zid": run_zid,
            "runtime_row": _store_row_summary(runtime_row, reason=rt),
            "runtime_context_store_id": ctx_id,
            "runtime_context_store_zid": ctx_zid,
            "fresh_recovery_templates_store_id": fresh_id,
            "fresh_recovery_templates_store_zid": fresh_zid,
            "fresh_row": _store_row_summary(fresh_row, reason=rt),
            "dashboard_equals_runtime_row": rows_match,
            "fresh_equals_runtime_row": fresh_matches_runtime,
            "fresh_equals_dashboard_row": fresh_matches_dashboard,
            "runtime_timing_resolution": timing_runtime,
            "fresh_timing_resolution": timing_fresh,
            "dashboard_timing_resolution": timing_dashboard,
            "cart_event_scoped_cache": _scoped_cache_state(ss),
            "candidate_store_rows": candidate_summaries,
            "pending_recovery_schedules": pending_n,
            "selected_source_explanation": explanation,
            "paths": {
                "dashboard": "GET/POST /api/dashboard/trigger-templates → dashboard_canonical_store_row(store_slug)",
                "runtime_canonical": "resolve_recovery_store_row_canonical(store_slug) — exact zid, else widget provision/mirror",
                "runtime_fresh": "_fresh_store_row_for_recovery_templates(store_slug) — used by delay_poll / schedule timing",
                "runtime_context": "_recovery_store_from_context(recovery_key, store_slug)",
            },
        }
    except SQLAlchemyError as exc:
        db.session.rollback()
        return {"ok": False, "error": str(exc), "store_slug": ss, "reason": rt}
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return {"ok": False, "error": str(exc), "store_slug": ss, "reason": rt}
