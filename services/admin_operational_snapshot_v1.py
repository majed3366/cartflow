# -*- coding: utf-8 -*-
"""
Admin operational snapshot export v1 — read-only JSON bundle for support/incidents.

No recovery, WhatsApp, onboarding, Purchase Truth, or lifecycle behavior changes.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CartRecoveryLog, RecoverySchedule, Store

_SNAPSHOT_VERSION = "admin_operational_snapshot_v1"
_MAX_RECENT_EVENTS = 25
_MAX_STORE_EVENTS = 12

# Substrings in key names that cause redaction (excluding exact-token keys; see allowlist).
_SENSITIVE_KEY_PARTS = frozenset(
    {
        "secret",
        "password",
        "oauth_code",
        "auth_code",
        "phone",
        "message",
        "body",
        "email",
        "auth_token",
        "api_key",
        "context_json",
    }
)

# Exact key names always dropped.
_SENSITIVE_KEY_EXACT = frozenset(
    {
        "access_token",
        "refresh_token",
        "token",
        "client_secret",
        "password",
        "password_hash",
        "authorization",
    }
)

# Keys allowed even if they contain a sensitive substring (e.g. status codes).
_SENSITIVE_KEY_ALLOWLIST = frozenset(
    {
        "status_code",
        "failure_class",
        "last_failure_type",
        "provider_message_sid",
        "has_oauth_access_token",
        "store_connected",
        "zid_platform_oauth_configured",
    }
)

_SKIPPED_RECOVERY_STATUSES = frozenset(
    {
        "cancelled",
        "skipped_duplicate",
        "skipped_no_phone",
        "skipped_no_reason",
        "skipped_resume",
        "skipped_resume_unsafe",
        "purchase_truth_stop",
    }
)

_FAILED_RECOVERY_STATUSES = frozenset(
    {
        "failed_resume",
        "failed_resume_stale",
        "whatsapp_failed",
    }
)

_STATUS_EVENT_KIND: dict[str, str] = {
    "scheduled": "recovery_scheduled",
    "running": "recovery_running",
    "completed": "recovery_completed",
    "whatsapp_failed": "recovery_failed",
    "failed_resume": "recovery_failed",
    "failed_resume_stale": "recovery_failed",
    "cancelled": "recovery_skipped",
    "skipped_duplicate": "recovery_skipped",
    "skipped_no_phone": "recovery_skipped",
    "skipped_no_reason": "recovery_skipped",
    "skipped_resume": "recovery_skipped",
    "skipped_resume_unsafe": "recovery_skipped",
    "purchase_truth_stop": "recovery_stopped_purchase",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_commit_sha() -> Optional[str]:
    for key in (
        "RAILWAY_GIT_COMMIT_SHA",
        "GIT_COMMIT",
        "SOURCE_VERSION",
        "COMMIT_SHA",
    ):
        val = (os.getenv(key) or "").strip()
        if val:
            return val[:64]
    return None


def _resolve_environment() -> str:
    env = (os.getenv("ENV") or "").strip().lower()
    if env:
        return env
    prod = (os.getenv("PRODUCTION_MODE") or "").strip().lower()
    if prod in ("1", "true", "yes", "on"):
        return "production"
    return "unknown"


def _is_sensitive_key(key: str) -> bool:
    k = (key or "").strip().lower()
    if k in _SENSITIVE_KEY_ALLOWLIST:
        return False
    if k in _SENSITIVE_KEY_EXACT:
        return True
    return any(part in k for part in _SENSITIVE_KEY_PARTS)


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return redact_operational_snapshot(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        # Mask E.164-ish phone fragments if they slip through unstructured fields.
        if re.search(r"\+?\d{10,15}", value):
            return "[REDACTED]"
        if "Bearer " in value or "whatsapp:" in value.lower():
            return "[REDACTED]"
    return value


def redact_operational_snapshot(payload: Any) -> Any:
    """Remove sensitive keys and mask phone-like strings — safe for external support."""
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, val in payload.items():
            if _is_sensitive_key(str(key)):
                continue
            out[str(key)] = _redact_value(val)
        return out
    if isinstance(payload, list):
        return [redact_operational_snapshot(item) for item in payload]
    return payload


def _resolve_store_by_slug(store_slug: str) -> Optional[Store]:
    ss = (store_slug or "").strip()[:255]
    if not ss:
        return None
    try:
        db.create_all()
        return (
            db.session.query(Store)
            .filter(Store.zid_store_id == ss)
            .first()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return None


def _section_metadata(
    *,
    store_slug: str,
    generated_by: str,
) -> dict[str, Any]:
    return {
        "snapshot_version": _SNAPSHOT_VERSION,
        "generated_at": _utc_now_iso(),
        "environment": _resolve_environment(),
        "commit_sha": _resolve_commit_sha(),
        "store_slug": (store_slug or "").strip()[:255] or None,
        "generated_by": (generated_by or "admin")[:64],
    }


def _section_runtime_health() -> dict[str, Any]:
    out: dict[str, Any] = {"available": True, "errors": []}

    try:
        from services.recovery_process_role_v1 import build_scheduler_health_snapshot

        out["scheduler"] = build_scheduler_health_snapshot()
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"scheduler:{str(exc)[:120]}")
        out["scheduler"] = {"ok": False}

    try:
        from services.db_due_scanner_health import build_db_due_scanner_health

        out["due_scanner"] = build_db_due_scanner_health()
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"due_scanner:{str(exc)[:120]}")
        out["due_scanner"] = {"status": "unavailable"}

    try:
        from services.cartflow_runtime_health import build_runtime_health_snapshot

        snap = build_runtime_health_snapshot()
        out["runtime_health"] = snap
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"runtime_health:{str(exc)[:120]}")
        out["runtime_health"] = {}

    try:
        from services.cartflow_provider_readiness import get_whatsapp_provider_readiness

        out["provider_readiness"] = get_whatsapp_provider_readiness()
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"provider_readiness:{str(exc)[:120]}")
        out["provider_readiness"] = {}

    try:
        from services.recovery_health_v1 import build_recovery_health_snapshot

        out["recovery_readiness"] = build_recovery_health_snapshot(emit_warn_log=False)
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"recovery_readiness:{str(exc)[:120]}")
        out["recovery_readiness"] = {}

    try:
        from services.operational_control_v1 import get_operational_control_state

        ctrl = get_operational_control_state()
        out["operational_control_flags"] = {
            k: ctrl.get(k)
            for k in (
                "platform_wa_paused",
                "platform_schedule_paused",
                "platform_continuation_paused",
                "provider_paused",
                "schedule_creation_allowed",
                "paused_stores",
                "paused_reasons",
            )
        }
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"operational_control:{str(exc)[:120]}")
        out["operational_control_flags"] = {}

    if out["errors"]:
        out["available"] = len(out["errors"]) < 4
    return out


def _section_store_readiness(
    *,
    store: Optional[Store],
    store_slug: str,
) -> dict[str, Any]:
    from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness

    if store is not None:
        ev = evaluate_onboarding_readiness(store)
        flags = ev.get("flags") if isinstance(ev.get("flags"), dict) else {}
        return {
            "scope": "store",
            "store_slug": (store_slug or "").strip()[:255] or None,
            "store_id": int(getattr(store, "id", 0) or 0) or None,
            "ready": bool(ev.get("ready")),
            "completion_percent": int(ev.get("completion_percent") or 0),
            "blocking_steps": list(ev.get("blocking_steps") or [])[:16],
            "soft_notes": list(ev.get("soft_notes") or [])[:8],
            "sandbox_mode_active": bool(ev.get("sandbox_mode_active")),
            "widget_configured": bool(flags.get("widget_installed")),
            "whatsapp_configured": bool(flags.get("whatsapp_configured")),
            "recovery_enabled": bool(flags.get("recovery_enabled")),
            "store_connected": bool(flags.get("store_connected")),
            "provider_ready": bool(flags.get("provider_ready")),
            "milestones": {
                k: bool(v)
                for k, v in (ev.get("milestones") or {}).items()
                if isinstance(ev.get("milestones"), dict)
            },
        }

    try:
        from services.cartflow_admin_operational_summary import (
            build_admin_operational_summary_readonly,
        )

        summary = build_admin_operational_summary_readonly()
        agg = summary.get("aggregate_onboarding") or {}
        trust = summary.get("trust_signals_summary") or {}
        return {
            "scope": "platform",
            "ready_stores": int(agg.get("onboarding_ready_stores") or 0),
            "blocked_stores": int(agg.get("onboarding_blocked_stores") or 0),
            "total_stores_scanned": int(agg.get("total_stores_scanned") or 0),
            "sandbox_stores": int(agg.get("sandbox_mode_stores") or 0),
            "platform_category": summary.get("platform_admin_category"),
            "runtime_trust_label_ar": trust.get("runtime_trust_label_ar"),
            "onboarding_ready_platform": bool(trust.get("onboarding_ready", True)),
        }
    except Exception as exc:  # noqa: BLE001
        return {"scope": "platform", "available": False, "error": str(exc)[:200]}


def _recovery_counts(*, store_slug: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {
        "active_running": 0,
        "scheduled": 0,
        "completed": 0,
        "skipped": 0,
        "failed": 0,
        "available": True,
        "scoped_to_store_slug": (store_slug or "").strip()[:255] or None,
    }
    try:
        db.create_all()
        q = db.session.query(RecoverySchedule.status, func.count(RecoverySchedule.id))
        ss = (store_slug or "").strip()[:255]
        if ss:
            q = q.filter(RecoverySchedule.store_slug == ss)
        counts: dict[str, int] = {}
        for st, cnt in q.group_by(RecoverySchedule.status).all():
            key = str(st or "").strip().lower()
            if key:
                counts[key] = int(cnt or 0)
        out["active_running"] = counts.get("running", 0)
        out["scheduled"] = counts.get("scheduled", 0)
        out["completed"] = counts.get("completed", 0)
        out["failed"] = sum(counts.get(s, 0) for s in _FAILED_RECOVERY_STATUSES)
        out["skipped"] = sum(counts.get(s, 0) for s in _SKIPPED_RECOVERY_STATUSES)
        out["by_status"] = counts
    except SQLAlchemyError as exc:
        db.session.rollback()
        out["available"] = False
        out["error"] = str(exc)[:200]
    return out


def _section_operational_signals(
    *,
    store: Optional[Store],
) -> dict[str, Any]:
    signals: dict[str, Any] = {
        "provider_issues": [],
        "onboarding_blockers": [],
        "identity_warnings": [],
        "lifecycle_warnings": [],
        "trust_warnings": [],
    }
    try:
        from services.cartflow_admin_operational_summary import (
            build_admin_operational_summary_readonly,
        )

        summary = build_admin_operational_summary_readonly()
        deg = summary.get("degradation_flags") or {}
        if deg.get("repeated_provider_failures"):
            signals["provider_issues"].append("repeated_provider_failures")
        if deg.get("provider_instability") or not summary.get("admin_runtime_summary_reuse", {}).get(
            "provider_runtime_ok", True
        ):
            signals["provider_issues"].append("provider_runtime_degraded")
        if deg.get("onboarding_pressure"):
            signals["onboarding_blockers"].append("onboarding_pressure")
        if deg.get("high_recent_duplicate_anomalies") or deg.get("duplicate_guard_pressure"):
            signals["identity_warnings"].append("duplicate_guard_pressure")
        if deg.get("repeated_lifecycle_pressure") or deg.get("impossible_transition_pressure"):
            signals["lifecycle_warnings"].append("lifecycle_pressure")
        if deg.get("dashboard_payload_pressure"):
            signals["lifecycle_warnings"].append("dashboard_payload_pressure")
        if deg.get("stale_session_signals"):
            signals["trust_warnings"].append("stale_session_signals")
        trust = summary.get("trust_signals_summary") or {}
        if trust.get("runtime_degraded"):
            signals["trust_warnings"].append("runtime_degraded")
        if trust.get("runtime_warning"):
            signals["trust_warnings"].append("runtime_warning")
        ano = (summary.get("anomaly_visibility") or {}).get("recent_type_counts") or {}
        if int(ano.get("identity_merge_blocked", 0) or 0) > 0:
            signals["identity_warnings"].append("identity_merge_blocked")
        if int(ano.get("impossible_state_transition", 0) or 0) > 0:
            signals["lifecycle_warnings"].append("impossible_state_transition")
    except Exception as exc:  # noqa: BLE001
        signals["error"] = str(exc)[:200]

    if store is not None:
        try:
            from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness

            ev = evaluate_onboarding_readiness(store)
            for step in ev.get("blocking_steps") or []:
                signals["onboarding_blockers"].append(str(step)[:64])
        except Exception:
            pass

    try:
        from services.admin_operational_control.signals import build_operational_issues
        from services.admin_operational_health import build_operational_control_context

        ctx = build_operational_control_context()
        for issue in build_operational_issues(ctx):
            if not issue.active:
                continue
            code = str(issue.code or "")
            if code in ("whatsapp_failure", "provider_instability"):
                if code not in signals["provider_issues"]:
                    signals["provider_issues"].append(code)
            elif code == "recovery_runtime_down":
                signals["trust_warnings"].append(code)
            elif code in ("cart_event_slow", "db_pool_timeout", "background_task_failure"):
                signals["trust_warnings"].append(code)
    except Exception:
        pass

    return signals


def _schedule_event_kind(status: str) -> str:
    st = (status or "").strip().lower()
    return _STATUS_EVENT_KIND.get(st, f"recovery_{st or 'unknown'}")


def _log_event_kind(status: str) -> str:
    st = (status or "").strip().lower()
    if st in ("whatsapp_failed", "failed", "error"):
        return "recovery_failed"
    if st in ("sent", "delivered", "completed", "success"):
        return "recovery_completed"
    if st.startswith("skipped"):
        return "recovery_skipped"
    return f"recovery_log_{st or 'unknown'}"


def _collect_recent_events(*, store_slug: str = "") -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    ss = (store_slug or "").strip()[:255]

    try:
        from services.operational_control_v1 import get_operational_control_state

        for ev in (get_operational_control_state().get("recent_events") or [])[-8:]:
            if not isinstance(ev, dict):
                continue
            control = str(ev.get("control") or "control")
            effect = str(ev.get("effect") or "applied")
            kind = "provider_paused" if control == "pause_wa" else f"control_{control}"
            if "resume" in effect.lower():
                kind = f"{control}_resumed"
            events.append(
                {
                    "at": ev.get("at_utc"),
                    "kind": kind,
                    "summary": f"{control}: {effect}"[:180],
                    "source": "operational_control",
                }
            )
    except Exception:
        pass

    try:
        db.create_all()
        sq = db.session.query(RecoverySchedule).order_by(RecoverySchedule.updated_at.desc())
        if ss:
            sq = sq.filter(RecoverySchedule.store_slug == ss)
        for row in sq.limit(_MAX_STORE_EVENTS).all():
            updated = getattr(row, "updated_at", None)
            at = (
                updated.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if updated is not None
                else None
            )
            events.append(
                {
                    "at": at,
                    "kind": _schedule_event_kind(str(getattr(row, "status", "") or "")),
                    "summary": f"schedule status={getattr(row, 'status', '')}"[:120],
                    "source": "recovery_schedule",
                    "schedule_id": int(getattr(row, "id", 0) or 0) or None,
                    "store_slug": str(getattr(row, "store_slug", "") or "")[:64] or None,
                }
            )
    except SQLAlchemyError:
        db.session.rollback()

    if ss:
        try:
            db.create_all()
            lq = (
                db.session.query(CartRecoveryLog)
                .filter(CartRecoveryLog.store_slug == ss)
                .order_by(CartRecoveryLog.created_at.desc())
                .limit(8)
            )
            for row in lq.all():
                created = getattr(row, "created_at", None)
                at = (
                    created.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    if created is not None
                    else None
                )
                events.append(
                    {
                        "at": at,
                        "kind": _log_event_kind(str(getattr(row, "status", "") or "")),
                        "summary": f"log status={getattr(row, 'status', '')}"[:120],
                        "source": "recovery_log",
                        "store_slug": ss,
                    }
                )
        except SQLAlchemyError:
            db.session.rollback()

    events.sort(key=lambda e: str(e.get("at") or ""), reverse=True)
    return events[:_MAX_RECENT_EVENTS]


def _section_support_context(
    *,
    store: Optional[Store],
    store_slug: str,
    runtime_section: dict[str, Any],
    readiness_section: dict[str, Any],
) -> dict[str, Any]:
    ss = (store_slug or "").strip()[:255]
    ctx: dict[str, Any] = {
        "store_slug": ss or None,
        "zid_store_id": None,
        "merchant_user_id": None,
        "store_id": None,
        "store_connected": False,
        "has_oauth_access_token": False,
        "zid_platform_oauth_configured": False,
        "readiness_state": readiness_section,
        "runtime_state_summary": {
            "scheduler_ok": bool((runtime_section.get("scheduler") or {}).get("ok", True)),
            "recovery_health": (runtime_section.get("recovery_readiness") or {}).get("health"),
            "provider_ready": bool(
                (runtime_section.get("provider_readiness") or {}).get("ready")
            ),
            "wa_paused": bool(
                (runtime_section.get("operational_control_flags") or {}).get(
                    "platform_wa_paused"
                )
            ),
        },
    }
    if store is not None:
        ctx["store_id"] = int(getattr(store, "id", 0) or 0) or None
        ctx["zid_store_id"] = (getattr(store, "zid_store_id", None) or "").strip()[:128] or None
        mid = getattr(store, "merchant_user_id", None)
        ctx["merchant_user_id"] = int(mid) if mid is not None else None
        ctx["has_oauth_access_token"] = bool((getattr(store, "access_token") or "").strip())
        ctx["store_connected"] = ctx["has_oauth_access_token"]
    try:
        from integrations.zid_client import zid_oauth_configured

        ctx["zid_platform_oauth_configured"] = zid_oauth_configured()
    except Exception:
        ctx["zid_platform_oauth_configured"] = False
    return ctx


def build_admin_operational_snapshot_v1(
    *,
    store_slug: str = "",
    generated_by: str = "admin",
) -> dict[str, Any]:
    """
    Build a read-only operational snapshot for admin export.

    Optional ``store_slug`` scopes store readiness, recovery counts, support context,
    and recent events to one merchant store (``Store.zid_store_id``).
    """
    ss = (store_slug or "").strip()[:255]
    store = _resolve_store_by_slug(ss) if ss else None

    runtime = _section_runtime_health()
    readiness = _section_store_readiness(store=store, store_slug=ss)

    raw = {
        "metadata": _section_metadata(store_slug=ss, generated_by=generated_by),
        "runtime_health": runtime,
        "store_readiness": readiness,
        "recovery_overview": _recovery_counts(store_slug=ss),
        "operational_signals": _section_operational_signals(store=store),
        "recent_events": _collect_recent_events(store_slug=ss),
        "support_context": _section_support_context(
            store=store,
            store_slug=ss,
            runtime_section=runtime,
            readiness_section=readiness,
        ),
    }
    if ss and store is None:
        raw["metadata"]["store_slug_warning"] = "store_not_found_for_slug"
    return redact_operational_snapshot(raw)
