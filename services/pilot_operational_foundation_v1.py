# -*- coding: utf-8 -*-
"""
Pilot Operational Visibility Foundation v1 — read-only composer.

Answers: «أي متجر يحتاج انتباهي الآن؟»
Composes existing admin operational truths only; no detection or writes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.pilot_operational_foundation_mapping_v1 import (
    FOUNDATION_VERSION,
    HEALTHY_PROBLEM_AR,
    PRIMARY_REASON_LABEL_AR,
    PRIORITY_SORT_RANK,
    READINESS_NOT_READY,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_SORT_RANK,
    STATUS_WARNING,
    WAITING_ONLY_ISSUE_KINDS,
    classify_action_required,
    compose_last_activity_fields,
    issue_title_ar,
    map_onboarding_state_to_readiness_key,
    parse_foundation_timestamp,
    priority_from_ops_row,
    readiness_from_onboarding_state,
    resolve_pilot_owner,
    status_from_severity,
)

_RECOVERY_ALERT_KINDS = frozenset({"stale_recovery", "failed_recovery"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_str(value: Any, limit: int = 256) -> str:
    return str(value or "").strip()[:limit]


def _load_store_orm_by_id(store_rows: list[dict[str, Any]]) -> dict[int, Any]:
    ids = []
    for row in store_rows or []:
        if not isinstance(row, dict):
            continue
        try:
            sid = int(row.get("store_id") or 0)
        except (TypeError, ValueError):
            sid = 0
        if sid > 0:
            ids.append(sid)
    if not ids:
        return {}
    try:
        from extensions import db  # noqa: PLC0415
        from models import Store  # noqa: PLC0415

        db.create_all()
        rows = db.session.query(Store).filter(Store.id.in_(ids)).all()
        return {int(getattr(s, "id", 0) or 0): s for s in rows if getattr(s, "id", None)}
    except Exception:  # noqa: BLE001
        try:
            from extensions import db as _db  # noqa: PLC0415

            _db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return {}


def _provider_readiness_snapshot() -> dict[str, Any]:
    try:
        from services.cartflow_provider_readiness import get_whatsapp_provider_readiness

        return get_whatsapp_provider_readiness()
    except Exception:  # noqa: BLE001
        return {}


def _business_copy_for_kind(kind: str) -> dict[str, str]:
    from services.admin_operations_center_v1 import _BUSINESS_ISSUE_COPY_AR  # noqa: PLC0415

    row = _BUSINESS_ISSUE_COPY_AR.get((kind or "").strip())
    return dict(row) if isinstance(row, dict) else {}


def _last_recovery_at_by_slug(alerts: list[dict[str, Any]]) -> dict[str, datetime]:
    out: dict[str, datetime] = {}
    for alert in alerts or []:
        if not isinstance(alert, dict):
            continue
        kind = _safe_str(alert.get("kind"), 64)
        if kind not in _RECOVERY_ALERT_KINDS:
            continue
        for rec in alert.get("records") or []:
            if not isinstance(rec, dict):
                continue
            slug = _safe_str(rec.get("store_slug"), 128)
            if not slug:
                continue
            dt = parse_foundation_timestamp(rec.get("updated_at"))
            if dt is None:
                continue
            prev = out.get(slug)
            if prev is None or dt > prev:
                out[slug] = dt
    return out


def _pick_primary_issue(ops_row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    issue = ops_row.get("primary_issue")
    if isinstance(issue, dict) and issue.get("kind"):
        return _safe_str(issue.get("kind"), 64), issue
    root = ops_row.get("primary_root_cause")
    if isinstance(root, dict):
        kinds = list(root.get("symptom_kinds") or [])
        if kinds:
            code = _safe_str(kinds[0], 64)
            return code, {"kind": code, "severity": root.get("severity")}
    issues = list(ops_row.get("issues") or [])
    if issues and isinstance(issues[0], dict):
        return _safe_str(issues[0].get("kind"), 64), issues[0]
    return "", {}


def _recommended_action_ar(issue_code: str, business_copy: dict[str, str]) -> str:
    if business_copy.get("action_ar"):
        return str(business_copy["action_ar"]).strip()
    if issue_code in WAITING_ONLY_ISSUE_KINDS:
        return "انتظار اعتماد القالب من ميتا."
    if issue_code == "whatsapp_missing":
        return "اطلب من التاجر ربط واتساب."
    if issue_code == "no_cart_events":
        return "تحقق من تركيب الودجيت واختبر إضافة منتج للسلة."
    if issue_code == "store_needs_setup":
        return "ساعد المتجر على إكمال خطوات الإعداد الأساسية."
    return "راجع حالة المتجر في لوحة العمليات."


def _compose_store_row(
    *,
    ops_row: dict[str, Any],
    store_meta: dict[str, Any],
    store_orm: Any,
    last_recovery_map: dict[str, datetime],
    provider_readiness: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    slug = _safe_str(ops_row.get("store_slug") or store_meta.get("store_slug"), 128)
    name = _safe_str(
        ops_row.get("store_name") or store_meta.get("display_name") or slug,
        128,
    ) or slug or "متجر"
    has_issues = bool(ops_row.get("has_issues"))

    status = status_from_severity(
        _safe_str(ops_row.get("highest_severity"), 32),
        has_issues=has_issues,
    )

    issue_code, _primary_issue = _pick_primary_issue(ops_row)
    business_copy = _business_copy_for_kind(issue_code) if issue_code else {}

    if status["key"] == STATUS_HEALTHY:
        problem_ar = HEALTHY_PROBLEM_AR
        issue_code = issue_code or "healthy"
        recommended_action_ar = "لا يلزم إجراء الآن."
        owner = resolve_pilot_owner("", provider_readiness=provider_readiness)
    else:
        problem_ar = issue_title_ar(issue_code, business_copy)
        recommended_action_ar = _recommended_action_ar(issue_code, business_copy)
        integration_source = ""
        if store_orm is not None:
            integration_source = _safe_str(getattr(store_orm, "integration_source", None), 64)
        owner = resolve_pilot_owner(
            issue_code,
            integration_source=integration_source,
            provider_readiness=provider_readiness,
        )

    primary_reason = {
        "label_ar": PRIMARY_REASON_LABEL_AR,
        "problem_ar": problem_ar,
        "issue_code": issue_code,
        "source": "admin_operations_center_v1.alert",
    }
    if business_copy.get("impact_ar"):
        primary_reason["impact_ar"] = business_copy["impact_ar"]

    priority = priority_from_ops_row(ops_row)
    action_required = classify_action_required(
        status_key=status["key"],
        owner_key=owner["key"],
        issue_code=issue_code,
        recommended_action_ar=recommended_action_ar,
    )

    recovery_dt = last_recovery_map.get(slug)
    recovery_raw = recovery_dt.isoformat() + "Z" if recovery_dt else None
    activity = compose_last_activity_fields(
        last_cart_event_at=store_meta.get("last_cart_event_at"),
        last_recovery_at=recovery_raw,
        widget_last_seen_at=store_meta.get("widget_last_seen_at"),
        now=now,
    )

    readiness_key = READINESS_NOT_READY
    readiness = readiness_from_onboarding_state("not_started", has_blocking=True)
    if store_orm is not None:
        try:
            from services.merchant_onboarding_reality_v1 import (  # noqa: PLC0415
                evaluate_merchant_onboarding_reality,
            )

            reality = evaluate_merchant_onboarding_reality(store_orm, emit_log=False)
            blocking = list(getattr(reality, "missing", None) or [])
            readiness_key = map_onboarding_state_to_readiness_key(
                str(getattr(reality, "onboarding_state", "") or ""),
                blocking_steps=blocking,
            )
            readiness = readiness_from_onboarding_state(
                str(getattr(reality, "onboarding_state", "") or ""),
                has_blocking=bool(blocking),
            )
        except Exception:  # noqa: BLE001
            blocking = list(store_meta.get("blocking_steps") or [])
            readiness_key = map_onboarding_state_to_readiness_key(
                "partial" if store_meta.get("ready") else "not_started",
                blocking_steps=blocking,
            )
            readiness = readiness_from_onboarding_state(
                "partial" if store_meta.get("ready") else "not_started",
                has_blocking=bool(blocking),
            )
    else:
        blocking = list(store_meta.get("blocking_steps") or [])
        readiness_key = map_onboarding_state_to_readiness_key(
            "partial" if store_meta.get("ready") else "not_started",
            blocking_steps=blocking,
        )
        readiness = readiness_from_onboarding_state(
            "partial" if store_meta.get("ready") else "not_started",
            has_blocking=bool(blocking),
        )

    return {
        "store_slug": slug,
        "store_name_ar": name,
        "status": status,
        "readiness": readiness,
        "readiness_key": readiness_key,
        "primary_reason": primary_reason,
        "priority": priority,
        "owner": owner,
        "recommended_action_ar": recommended_action_ar,
        "action_required": action_required,
        **activity,
        "_priority_rank": int(ops_row.get("priority_rank") if has_issues else 99),
        "_store_slug_sort": slug,
    }


def _sort_attention_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _key(row: dict[str, Any]) -> tuple[int, int, int, str]:
        status = row.get("status") if isinstance(row.get("status"), dict) else {}
        priority = row.get("priority") if isinstance(row.get("priority"), dict) else {}
        return (
            STATUS_SORT_RANK.get(str(status.get("key") or STATUS_HEALTHY), 99),
            PRIORITY_SORT_RANK.get(str(priority.get("key") or "low"), 99),
            int(row.get("_priority_rank") or 99),
            str(row.get("_store_slug_sort") or ""),
        )

    return sorted(rows, key=_key)


def _public_store_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out.pop("_priority_rank", None)
    out.pop("_store_slug_sort", None)
    out.pop("readiness_key", None)
    return out


def _build_pilot_health_overview(production_rows: list[dict[str, Any]]) -> dict[str, Any]:
    healthy = warning = critical = launch_ready = not_ready = 0
    for row in production_rows:
        status = row.get("status") if isinstance(row.get("status"), dict) else {}
        readiness = row.get("readiness") if isinstance(row.get("readiness"), dict) else {}
        sk = str(status.get("key") or "")
        rk = str(readiness.get("key") or row.get("readiness_key") or "")
        if sk == STATUS_HEALTHY:
            healthy += 1
        elif sk == STATUS_CRITICAL:
            critical += 1
        elif sk == STATUS_WARNING:
            warning += 1
        if rk == "launch_ready":
            launch_ready += 1
        if rk == "not_ready":
            not_ready += 1
    return {
        "title_ar": "نظرة عامة على صحة التشغيل",
        "total_stores": len(production_rows),
        "healthy_stores": healthy,
        "warning_stores": warning,
        "critical_stores": critical,
        "launch_ready_stores": launch_ready,
        "not_ready_stores": not_ready,
    }


def _build_top_operational_issues(production_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from collections import Counter

    counts: Counter[str] = Counter()
    severity_by_code: dict[str, str] = {}
    title_by_code: dict[str, str] = {}
    for row in production_rows:
        status = row.get("status") if isinstance(row.get("status"), dict) else {}
        if str(status.get("key") or "") == STATUS_HEALTHY:
            continue
        primary = row.get("primary_reason") if isinstance(row.get("primary_reason"), dict) else {}
        code = _safe_str(primary.get("issue_code"), 64)
        if not code or code == "healthy":
            continue
        counts[code] += 1
        severity_by_code[code] = str(status.get("key") or STATUS_WARNING)
        title_by_code[code] = _safe_str(primary.get("problem_ar"), 200) or issue_title_ar(code)

    items: list[dict[str, Any]] = []
    for code, count in counts.most_common():
        sev_key = severity_by_code.get(code, STATUS_WARNING)
        items.append(
            {
                "problem_ar": title_by_code.get(code) or issue_title_ar(code),
                "issue_code": code,
                "store_count": int(count),
                "severity": {
                    "key": sev_key,
                    "label_ar": {
                        STATUS_HEALTHY: "سليم",
                        STATUS_WARNING: "يحتاج متابعة",
                        STATUS_CRITICAL: "حرج",
                    }.get(sev_key, "يحتاج متابعة"),
                },
            }
        )
    return items


def build_pilot_operational_foundation_readonly(
    *,
    include_demo: bool = False,
) -> dict[str, Any]:
    """Build canonical pilot operational foundation JSON."""
    generated_at = _utc_now_iso()
    try:
        from services.admin_operations_center_v1 import _build_ops_shared_context  # noqa: PLC0415
        from services.admin_operations_store_action_center_v1 import (  # noqa: PLC0415
            build_store_action_center_readonly,
        )

        ctx = _build_ops_shared_context()
        store_rows = list(ctx.get("store_rows") or [])
        alerts = list(ctx.get("alerts") or [])
        sac = build_store_action_center_readonly(store_rows=store_rows, alerts=alerts)
    except Exception as exc:  # noqa: BLE001
        return {
            "version": FOUNDATION_VERSION,
            "generated_at": generated_at,
            "ok": False,
            "error": str(exc)[:200],
            "pilot_health_overview": None,
            "attention_queue": [],
            "top_operational_issues": [],
            "stores": [],
            "meta": {
                "production_only": not include_demo,
                "stores_scanned": 0,
                "sources": [],
            },
        }

    store_meta_by_slug = {
        _safe_str(row.get("store_slug"), 128): row
        for row in store_rows
        if isinstance(row, dict) and _safe_str(row.get("store_slug"), 128)
    }
    store_orm_by_id = _load_store_orm_by_id(store_rows)
    provider_readiness = _provider_readiness_snapshot()
    last_recovery_map = _last_recovery_at_by_slug(alerts)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    production_queue = list(sac.get("production_queue") or [])
    demo_queue = list(sac.get("demo_test_queue") or [])

    def _build_rows(queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
        built: list[dict[str, Any]] = []
        for ops_row in queue:
            if not isinstance(ops_row, dict):
                continue
            slug = _safe_str(ops_row.get("store_slug"), 128)
            meta = store_meta_by_slug.get(slug, {})
            store_id = 0
            try:
                store_id = int(meta.get("store_id") or 0)
            except (TypeError, ValueError):
                store_id = 0
            store_orm = store_orm_by_id.get(store_id)
            built.append(
                _compose_store_row(
                    ops_row=ops_row,
                    store_meta=meta,
                    store_orm=store_orm,
                    last_recovery_map=last_recovery_map,
                    provider_readiness=provider_readiness,
                    now=now,
                )
            )
        return built

    production_rows = _build_rows(production_queue)
    demo_rows = _build_rows(demo_queue) if include_demo else []

    attention_queue = [
        _public_store_row(r) for r in _sort_attention_queue(list(production_rows))
    ]
    stores = [_public_store_row(r) for r in production_rows]

    payload: dict[str, Any] = {
        "version": FOUNDATION_VERSION,
        "generated_at": generated_at,
        "ok": True,
        "pilot_health_overview": _build_pilot_health_overview(production_rows),
        "attention_queue": attention_queue,
        "top_operational_issues": _build_top_operational_issues(production_rows),
        "stores": stores,
        "meta": {
            "production_only": True,
            "stores_scanned": len(production_rows),
            "sources": [
                "admin_operations_center_v2_5",
                "store_action_center",
                "merchant_onboarding_reality_v1",
            ],
        },
    }
    if include_demo:
        payload["demo_stores"] = [_public_store_row(r) for r in demo_rows]
        payload["meta"]["demo_stores_scanned"] = len(demo_rows)
        payload["meta"]["production_only"] = False
    return payload


__all__ = ["build_pilot_operational_foundation_readonly"]
