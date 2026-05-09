# -*- coding: utf-8 -*-
"""
Read-only admin / operational aggregates for CartFlow.

Consumes existing runtime health, onboarding evaluation, duplicate guard, lifecycle,
session consistency, and in-process anomaly buffers — no parallel business logic.

Does not change recovery, WhatsApp sends, merchant dashboard UX, or core health
recording behavior; only reads public diagnostic helpers.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import exists
from sqlalchemy.exc import SQLAlchemyError

_MAX_STORES_TO_SCORE = 400

# Thresholds (deterministic; tune in one place)
_ANOMALY_DUP_ATTEMPT_WARN = 4
_PROVIDER_FAIL_WARN = 3
_LIFECYCLE_CONFLICT_WARN = 2
_DASHBOARD_CONFLICT_WARN = 3
_STORES_PHONE_GAP_WARN_RATIO = 0.35
_ONBOARDING_BLOCK_RATIO_WARN = 0.45

ADMIN_PLATFORM_CATEGORY_HEALTHY = "healthy"
ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED = "onboarding_blocked"
ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION = "provider_attention_needed"
ADMIN_PLATFORM_CATEGORY_RUNTIME_WARNING = "runtime_warning"
ADMIN_PLATFORM_CATEGORY_OPERATIONAL_ATTENTION = "operational_attention_needed"
ADMIN_PLATFORM_CATEGORY_DEGRADED = "degraded"
ADMIN_PLATFORM_CATEGORY_SANDBOX_ONLY = "sandbox_only"

TRUST_READY = "operationally_ready"
TRUST_PARTIAL = "partially_ready"
TRUST_DEGRADED = "degraded"
TRUST_UNSTABLE = "unstable"


def map_platform_admin_category(
    *,
    trust_signals: dict[str, Any],
    health_snapshot: dict[str, Any],
    aggregate_onboarding: dict[str, Any],
) -> str:
    """Single coarse admin category from existing trust + snapshot + aggregated onboarding."""
    ts = trust_signals if isinstance(trust_signals, dict) else {}
    snap = health_snapshot if isinstance(health_snapshot, dict) else {}
    agg = aggregate_onboarding if isinstance(aggregate_onboarding, dict) else {}

    if bool(ts.get("runtime_degraded")):
        return ADMIN_PLATFORM_CATEGORY_DEGRADED

    ob_single = snap.get("onboarding_runtime") if isinstance(snap.get("onboarding_runtime"), dict) else {}
    pr = snap.get("provider_runtime") if isinstance(snap.get("provider_runtime"), dict) else {}
    sandbox_latest = bool(ob_single.get("sandbox_mode_active", False))

    blocked_ratio = float(agg.get("onboarding_blocked_ratio") or 0.0)
    if blocked_ratio >= 0.5 and not float(agg.get("sandbox_store_ratio") or 0.0) >= 0.9:
        return ADMIN_PLATFORM_CATEGORY_ONBOARDING_BLOCKED

    if (
        not bool(pr.get("provider_readiness_ready", False))
        and not sandbox_latest
        and not float(agg.get("sandbox_store_ratio") or 0.0) >= 0.85
    ):
        return ADMIN_PLATFORM_CATEGORY_PROVIDER_ATTENTION

    if bool(ts.get("runtime_warning")):
        if bool(ts.get("stale_state_detected")) or not bool(ts.get("session_runtime_consistent", True)):
            return ADMIN_PLATFORM_CATEGORY_OPERATIONAL_ATTENTION
        return ADMIN_PLATFORM_CATEGORY_RUNTIME_WARNING

    if float(agg.get("sandbox_store_ratio") or 0.0) >= 0.85 and agg.get("total_stores_scanned", 0) >= 1:
        return ADMIN_PLATFORM_CATEGORY_SANDBOX_ONLY

    return ADMIN_PLATFORM_CATEGORY_HEALTHY


def _store_trust_score_and_bucket(
    *,
    onboarding_eval: dict[str, Any],
    provider_ready_globally: bool,
    need_real_whatsapp: bool,
    lifecycle_ok: bool,
    dup_ok: bool,
    session_ok: bool,
) -> tuple[str, int]:
    """Explainable bucket + 0–100 score; deterministic."""
    ev = onboarding_eval if isinstance(onboarding_eval, dict) else {}
    base = int(ev.get("completion_percent") or 0)
    score = base

    if not bool(ev.get("ready", False)):
        score = min(score, 62)
    if need_real_whatsapp and not provider_ready_globally:
        score = min(score, 48)
    if not lifecycle_ok:
        score = min(score, 55)
    if not dup_ok:
        score = min(score, 50)
    if not session_ok:
        score = min(score, 58)

    score = max(0, min(100, score))

    if score >= 82:
        return TRUST_READY, score
    if score >= 58:
        return TRUST_PARTIAL, score
    if score >= 36:
        return TRUST_DEGRADED, score
    return TRUST_UNSTABLE, score


def _count_stores_phone_dependency_gap() -> tuple[int, int]:
    """Stores with ≥1 abandoned cart but no cart carrying a non-empty phone (read-only)."""
    try:
        from extensions import db  # noqa: PLC0415
        from models import AbandonedCart, Store  # noqa: PLC0415

        db.create_all()
        total = int(db.session.query(Store.id).count() or 0)
        if total == 0:
            return 0, 0
        gap_q = (
            db.session.query(Store.id)
            .filter(
                exists().where(AbandonedCart.store_id == Store.id),
                ~exists().where(
                    AbandonedCart.store_id == Store.id,
                    AbandonedCart.customer_phone.isnot(None),
                    AbandonedCart.customer_phone != "",
                ),
            )
            .distinct()
        )
        gap_n = gap_q.count()
        return int(gap_n or 0), total
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        try:
            from extensions import db as _db  # noqa: PLC0415

            _db.session.rollback()
        except Exception:
            pass
        return 0, 0


def build_admin_operational_summary_readonly() -> dict[str, Any]:
    """
    Safe JSON-style aggregate for admin / support tooling.
    No stack traces, secrets, or heavy joins beyond capped store scan.
    """
    from services.cartflow_onboarding_readiness import (  # noqa: PLC0415
        evaluate_onboarding_readiness,
    )
    from services.cartflow_runtime_health import (  # noqa: PLC0415
        build_admin_runtime_summary,
        build_runtime_health_snapshot,
        derive_runtime_trust_signals,
        recent_anomaly_type_counts,
    )
    from services.whatsapp_send import recovery_uses_real_whatsapp  # noqa: PLC0415

    snap = build_runtime_health_snapshot()
    admin_base = build_admin_runtime_summary()
    buf_n = int(admin_base.get("recent_anomaly_count") or 0)
    trust = derive_runtime_trust_signals(snap, recent_anomaly_count=buf_n)

    need_real = bool(recovery_uses_real_whatsapp())
    pr = snap.get("provider_runtime") if isinstance(snap.get("provider_runtime"), dict) else {}
    provider_ready_glob = bool(pr.get("provider_readiness_ready", False))

    lc = snap.get("lifecycle_consistency_runtime") if isinstance(snap.get("lifecycle_consistency_runtime"), dict) else {}
    dup_rt = (
        snap.get("duplicate_protection_runtime")
        if isinstance(snap.get("duplicate_protection_runtime"), dict)
        else {}
    )
    sess = snap.get("session_consistency_runtime") if isinstance(snap.get("session_consistency_runtime"), dict) else {}

    lifecycle_ok = bool(lc.get("lifecycle_runtime_ok", True))
    dup_ok = bool(dup_rt.get("duplicate_prevention_runtime_ok", True))
    session_ok = bool(sess.get("session_runtime_consistent", True))

    dup_diag: dict[str, Any] = {}
    try:
        from services.cartflow_duplicate_guard import (  # noqa: PLC0415
            get_duplicate_guard_diagnostics_readonly,
        )

        dup_diag = get_duplicate_guard_diagnostics_readonly()
    except Exception:
        dup_diag = {}

    store_rows: list[Any] = []
    try:
        from extensions import db  # noqa: PLC0415
        from models import Store  # noqa: PLC0415

        db.create_all()
        store_rows = (
            db.session.query(Store)
            .order_by(Store.id.desc())
            .limit(_MAX_STORES_TO_SCORE)
            .all()
        )
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        try:
            from extensions import db as _db  # noqa: PLC0415

            _db.session.rollback()
        except Exception:
            pass
        store_rows = []

    scanned = len(store_rows)
    onboarding_ready_n = 0
    onboarding_blocked_n = 0
    sandbox_n = 0
    trust_buckets: Counter[str] = Counter()
    store_operational_rows: list[dict[str, Any]] = []
    for row in store_rows:
        ev = evaluate_onboarding_readiness(row)
        if bool(ev.get("ready")):
            onboarding_ready_n += 1
        if ev.get("blocking_steps"):
            onboarding_blocked_n += 1
        if bool(ev.get("sandbox_mode_active")):
            sandbox_n += 1
        bucket, _sc = _store_trust_score_and_bucket(
            onboarding_eval=ev,
            provider_ready_globally=provider_ready_glob,
            need_real_whatsapp=need_real,
            lifecycle_ok=lifecycle_ok,
            dup_ok=dup_ok,
            session_ok=session_ok,
        )
        trust_buckets[bucket] += 1
        sid = (getattr(row, "zid_store_id", None) or "").strip()
        store_operational_rows.append(
            {
                "display_name": (getattr(row, "widget_name", None) or "").strip()
                or (sid[:64] if sid else "متجر"),
                "store_ref": sid[:128] if sid else "",
                "trust_bucket": bucket,
                "trust_score": int(_sc),
                "onboarding_ready": bool(ev.get("ready")),
                "onboarding_completion_percent": int(ev.get("completion_percent") or 0),
                "provider_ready_platform": bool(provider_ready_glob),
                "sandbox_mode_active": bool(ev.get("sandbox_mode_active")),
                "blocking_steps_count": len(ev.get("blocking_steps") or []),
            }
        )

    agg_ob = {
        "total_stores_scanned": scanned,
        "onboarding_ready_stores": onboarding_ready_n,
        "onboarding_blocked_stores": onboarding_blocked_n,
        "sandbox_mode_stores": sandbox_n,
        "onboarding_blocked_ratio": (onboarding_blocked_n / scanned) if scanned else 0.0,
        "sandbox_store_ratio": (sandbox_n / scanned) if scanned else 0.0,
        "trust_bucket_counts": dict(trust_buckets),
    }

    phone_gap_n, store_total_db = _count_stores_phone_dependency_gap()
    phone_gap_ratio = (phone_gap_n / store_total_db) if store_total_db else 0.0

    ano = recent_anomaly_type_counts(limit=200)
    try:
        from services.cartflow_runtime_health import (  # noqa: PLC0415
            ANOMALY_PROVIDER_SEND_FAILURE,
            ANOMALY_DUPLICATE_SEND_ATTEMPT,
            ANOMALY_DASHBOARD_PAYLOAD_CONFLICT,
            ANOMALY_IMPOSSIBLE_STATE_TRANSITION,
        )
    except Exception:
        ANOMALY_PROVIDER_SEND_FAILURE = "provider_send_failure"
        ANOMALY_DUPLICATE_SEND_ATTEMPT = "duplicate_send_attempt"
        ANOMALY_DASHBOARD_PAYLOAD_CONFLICT = "dashboard_payload_conflict"
        ANOMALY_IMPOSSIBLE_STATE_TRANSITION = "impossible_state_transition"

    dup_attempts = int(ano.get(ANOMALY_DUPLICATE_SEND_ATTEMPT, 0))
    prov_fails = int(ano.get(ANOMALY_PROVIDER_SEND_FAILURE, 0))
    dash_conf = int(ano.get(ANOMALY_DASHBOARD_PAYLOAD_CONFLICT, 0))
    impossible = int(ano.get(ANOMALY_IMPOSSIBLE_STATE_TRANSITION, 0))

    lc_conf_events = int(lc.get("lifecycle_conflict_events_recent", 0) or 0)

    degradation = {
        "high_recent_duplicate_anomalies": bool(dup_attempts >= _ANOMALY_DUP_ATTEMPT_WARN),
        "repeated_provider_failures": bool(prov_fails >= _PROVIDER_FAIL_WARN),
        "repeated_lifecycle_pressure": bool(
            not bool(lc.get("lifecycle_runtime_ok", True)) or lc_conf_events >= _LIFECYCLE_CONFLICT_WARN
        ),
        "dashboard_payload_pressure": bool(dash_conf >= _DASHBOARD_CONFLICT_WARN),
        "impossible_transition_pressure": bool(impossible >= 2),
        "stale_session_signals": bool(not session_ok),
        "onboarding_pressure": bool(agg_ob["onboarding_blocked_ratio"] >= _ONBOARDING_BLOCK_RATIO_WARN),
        "duplicate_guard_pressure": bool(dup_diag.get("duplicate_send_blocked_recently") is True),
    }

    platform_category = map_platform_admin_category(
        trust_signals=trust,
        health_snapshot=snap,
        aggregate_onboarding=agg_ob,
    )

    hints_ar = _build_admin_operational_hints_ar(
        agg_ob=agg_ob,
        phone_gap_n=phone_gap_n,
        phone_gap_ratio=phone_gap_ratio,
        degradation=degradation,
        ano=ano,
        dup_diag=dup_diag,
        trust=trust,
    )

    ano_notes = [
        lbl
        for cond, lbl in (
            (degradation.get("repeated_provider_failures"), "مزود"),
            (degradation.get("high_recent_duplicate_anomalies"), "تكرار"),
            (degradation.get("repeated_lifecycle_pressure"), "دورة_حياة"),
            (degradation.get("dashboard_payload_pressure"), "لوحة"),
            (degradation.get("stale_session_signals"), "جلسة"),
            (degradation.get("duplicate_guard_pressure"), "منع_تكرار"),
            (degradation.get("onboarding_pressure"), "إعداد"),
        )
        if cond
    ]
    for srow in store_operational_rows:
        srow["anomaly_notes"] = list(ano_notes[:4])

    anomaly_visibility = {
        "recent_type_counts": {k: int(v) for k, v in ano.items() if int(v) > 0},
        "duplicate_guard_counters": dup_diag.get("counters", {}),
        "lifecycle_counters": lc.get("lifecycle_counters", {}),
        "session_consistency_counters": sess.get("counters", {}),
        "buffered_event_total": buf_n,
    }

    return {
        "generated_from": "cartflow_admin_operational_summary_v1",
        "platform_admin_category": platform_category,
        "runtime_health_reused": True,
        "active_stores_db_total": store_total_db,
        "stores_scanned_for_trust": scanned,
        "aggregate_onboarding": agg_ob,
        "stores_missing_phone_coverage_estimate": phone_gap_n,
        "phone_coverage_gap_ratio": round(phone_gap_ratio, 4),
        "recovery_runtime_globally_active": bool(
            (snap.get("recovery_runtime") or {}).get("runtime_active")
            if isinstance(snap.get("recovery_runtime"), dict)
            else False
        ),
        "trust_signals_summary": {
            "runtime_stable": bool(trust.get("runtime_stable")),
            "runtime_degraded": bool(trust.get("runtime_degraded")),
            "runtime_warning": bool(trust.get("runtime_warning")),
            "runtime_trust_label_ar": trust.get("runtime_trust_label_ar"),
            "onboarding_ready": bool(trust.get("onboarding_ready", True)),
            "onboarding_completion_percent": int(trust.get("onboarding_completion_percent") or 0),
        },
        "degradation_flags": degradation,
        "anomaly_visibility": anomaly_visibility,
        "admin_operational_hints_ar": hints_ar,
        "store_operational_rows": store_operational_rows,
        "admin_runtime_summary_reuse": {
            "recovery_runtime_ok": admin_base.get("recovery_runtime_ok"),
            "provider_runtime_ok": admin_base.get("provider_runtime_ok"),
            "identity_runtime_ok": admin_base.get("identity_runtime_ok"),
            "dashboard_runtime_ok": admin_base.get("dashboard_runtime_ok"),
        },
    }


def _build_admin_operational_hints_ar(
    *,
    agg_ob: dict[str, Any],
    phone_gap_n: int,
    phone_gap_ratio: float,
    degradation: dict[str, Any],
    ano: dict[str, int],
    dup_diag: dict[str, Any],
    trust: dict[str, Any],
) -> list[str]:
    hints: list[str] = []
    if phone_gap_n >= 3 or phone_gap_ratio >= _STORES_PHONE_GAP_WARN_RATIO:
        hints.append("عدد كبير من السلال أو المتاجر بلا تغطية موثوقة لأرقام العملاء — راجع التكامل.")
    if float(agg_ob.get("sandbox_store_ratio") or 0.0) >= 0.4 and int(agg_ob.get("total_stores_scanned") or 0) >= 2:
        hints.append("عدة متاجر ما زالت في وضع التجربة — تأكد من خطة الإنتاج.")
    if degradation.get("high_recent_duplicate_anomalies") or dup_diag.get("duplicate_send_blocked_recently"):
        hints.append("ارتفاع محاولات منع الإرسال المكرر — راجع سجل الأتمتة.")
    if degradation.get("repeated_provider_failures"):
        hints.append("توجد مشاكل جاهزية واتساب في نافذة الرصد الأخيرة.")
    if degradation.get("repeated_lifecycle_pressure"):
        hints.append("ضغط على اتساق دورة حياة الاسترجاع — راجع التوقيت والقوالب.")
    if degradation.get("dashboard_payload_pressure") or degradation.get("stale_session_signals"):
        hints.append("إشارات اتساق لوحة/جلسة تحتاج مراجعة تشغيلية.")
    if bool(trust.get("runtime_degraded")):
        hints.append("تدهور عام في ثقة التشغيل — راجع الجاهزية والهوية والمزود.")
    return hints[:8]


def reset_admin_operational_summary_for_tests() -> None:
    """Placeholder for symmetry (no module-local mutable aggregates)."""
    return None
