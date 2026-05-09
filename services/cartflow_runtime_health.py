# -*- coding: utf-8 -*-
"""
Runtime health visibility foundation: read-only snapshots, anomaly symbols, admin-ready summaries.

Does not change WhatsApp sending, scheduling, recovery flow, or the observability package itself.
Opt-in structured logs via CARTFLOW_STRUCTURED_HEALTH_LOG=1 to avoid noise.
"""
from __future__ import annotations

import logging
import os
import threading
from collections import Counter, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger("cartflow")

PREFIX_HEALTH = "[CARTFLOW HEALTH]"
PREFIX_ANOMALY = "[CARTFLOW ANOMALY]"
PREFIX_PROVIDER = "[CARTFLOW PROVIDER]"

# Symbolic anomalies (system-level; no PII in aggregate keys)
ANOMALY_DUPLICATE_SEND_ATTEMPT = "duplicate_send_attempt"
ANOMALY_SEND_AFTER_RETURN = "send_after_return"
ANOMALY_SEND_AFTER_CONVERSION = "send_after_conversion"
ANOMALY_IDENTITY_MERGE_BLOCKED = "identity_merge_blocked"
ANOMALY_MISSING_CUSTOMER_PHONE = "missing_customer_phone"
ANOMALY_PROVIDER_SEND_FAILURE = "provider_send_failure"
ANOMALY_IMPOSSIBLE_STATE_TRANSITION = "impossible_state_transition"
ANOMALY_DASHBOARD_PAYLOAD_CONFLICT = "dashboard_payload_conflict"

# Map dashboard / diagnostic conflict codes → anomaly symbols
CONFLICT_CODE_TO_ANOMALY: dict[str, str] = {
    "recovered_cart_with_send_success_log": ANOMALY_IMPOSSIBLE_STATE_TRANSITION,
    "identity_trust_failed_with_send_success_log": ANOMALY_IDENTITY_MERGE_BLOCKED,
    "anti_spam_skip_without_behavioral_return": ANOMALY_DASHBOARD_PAYLOAD_CONFLICT,
}

_MAX_ANOMALY_BUFFER = 200
_anomaly_lock = threading.Lock()
_recent_anomalies: deque[dict[str, Any]] = deque(maxlen=_MAX_ANOMALY_BUFFER)


def structured_health_logging_enabled() -> bool:
    v = (os.getenv("CARTFLOW_STRUCTURED_HEALTH_LOG") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def emit_health_log(message: str, **fields: Any) -> None:
    if not structured_health_logging_enabled():
        return
    _emit_line(PREFIX_HEALTH, message, **fields)


def emit_anomaly_log(anomaly_type: str, **fields: Any) -> None:
    if not structured_health_logging_enabled():
        return
    _emit_line(PREFIX_ANOMALY, "signal", type=(anomaly_type or "").strip()[:80], **fields)


def emit_provider_log(message: str, **fields: Any) -> None:
    if not structured_health_logging_enabled():
        return
    _emit_line(PREFIX_PROVIDER, message, **fields)


def _emit_line(prefix: str, message: str, **fields: Any) -> None:
    msg = (message or "").strip()[:200] or "-"
    parts = [prefix, f"msg={msg}"]
    for k in sorted(fields.keys()):
        key = str(k).strip()[:48]
        if not key:
            continue
        val = fields[k]
        sval = "-" if val is None else str(val).strip().replace("\n", " ")[:256]
        parts.append(f"{key}={sval}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.info("%s", line)


def record_runtime_anomaly(
    anomaly_type: str,
    *,
    source: str = "",
    detail: str = "",
) -> None:
    """Buffer a symbolic anomaly for admin/runtime summaries (optional; no recovery side effects)."""
    at = (anomaly_type or "").strip()[:80] or "unknown"
    entry = {
        "type": at,
        "source": (source or "").strip()[:80],
        "detail": (detail or "").strip()[:200],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with _anomaly_lock:
        _recent_anomalies.append(entry)
    emit_anomaly_log(at, source=(source or "").strip()[:64] or "-")


def drain_recent_anomalies(limit: int = 50) -> list[dict[str, Any]]:
    """Copy up to ‎limit‎ recent buffered anomalies (newest last); does not clear buffer."""
    with _anomaly_lock:
        return list(_recent_anomalies)[-max(1, min(limit, _MAX_ANOMALY_BUFFER)) :]


def clear_runtime_anomaly_buffer_for_tests() -> None:
    """Empty the in-process anomaly ring buffer (for isolated tests)."""
    with _anomaly_lock:
        _recent_anomalies.clear()


def recent_anomaly_type_counts(limit: int = 200) -> dict[str, int]:
    """Histogram of buffered anomaly ‎type‎ values."""
    with _anomaly_lock:
        slice_ = list(_recent_anomalies)[-max(1, min(limit, _MAX_ANOMALY_BUFFER)) :]
    return dict(Counter(str(x.get("type") or "unknown") for x in slice_))


def aggregate_anomaly_symbols(symbols: list[str]) -> dict[str, int]:
    """Pure reducer for symbolic anomaly lists (e.g. from diagnostics)."""
    out: Counter[str] = Counter()
    for s in symbols:
        key = (s or "").strip()
        if key:
            out[key] += 1
    return dict(out)


def map_conflict_codes_to_anomalies(codes: list[str]) -> list[str]:
    """Turn internal conflict codes into canonical anomaly symbols."""
    out: list[str] = []
    for c in codes:
        raw = (c or "").strip()
        if not raw:
            continue
        mapped = CONFLICT_CODE_TO_ANOMALY.get(raw)
        if mapped:
            out.append(mapped)
        else:
            out.append(raw)
    return out


def _twilio_env_snapshot() -> dict[str, bool]:
    try:
        sid = (os.getenv("TWILIO_ACCOUNT_SID") or "").strip()
        tok = (os.getenv("TWILIO_AUTH_TOKEN") or "").strip()
        frm = (os.getenv("TWILIO_WHATSAPP_FROM") or "").strip()
        configured = bool(sid and tok and frm)
        return {
            "twilio_env_present": configured,
            "twilio_account_sid_present": bool(sid),
            "twilio_token_present": bool(tok),
            "twilio_whatsapp_from_present": bool(frm),
        }
    except OSError:
        return {
            "twilio_env_present": False,
            "twilio_account_sid_present": False,
            "twilio_token_present": False,
            "twilio_whatsapp_from_present": False,
        }


def _recent_whatsapp_failed_count(*, hours: int = 24) -> int:
    """Read-only count of ‎whatsapp_failed‎ log rows in time window (‎-1‎ = query error)."""
    try:
        from extensions import db  # noqa: PLC0415
        from models import CartRecoveryLog  # noqa: PLC0415

        db.create_all()
        since = datetime.now(timezone.utc) - timedelta(hours=max(1, min(int(hours), 168)))
        n = (
            db.session.query(func.count(CartRecoveryLog.id))
            .filter(
                CartRecoveryLog.status == "whatsapp_failed",
                CartRecoveryLog.created_at >= since,
            )
            .scalar()
        )
        return int(n or 0)
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        try:
            from extensions import db as _db  # noqa: PLC0415

            _db.session.rollback()
        except Exception:
            pass
        return -1


def build_runtime_health_snapshot() -> dict[str, Any]:
    """
    Nested read-only health sections for monitoring / future admin.

    No mutations; safe booleans/counters only.
    """
    from services.cartflow_observability_runtime import (  # noqa: PLC0415
        runtime_health_snapshot_readonly,
    )

    flat = runtime_health_snapshot_readonly()
    tw = _twilio_env_snapshot()
    fail_n = _recent_whatsapp_failed_count(hours=24)

    recovery_active = bool(flat.get("recovery_runtime_active"))
    wa_ready = bool(flat.get("whatsapp_provider_ready"))
    ident_ok = bool(flat.get("identity_resolution_ok"))

    with _anomaly_lock:
        buf_n = len(_recent_anomalies)
        id_conflict = any(
            str(x.get("type") or "") == ANOMALY_IDENTITY_MERGE_BLOCKED for x in _recent_anomalies
        )

    dup_guard_diag: dict[str, Any] = {}
    dup_anomaly_count = 0
    try:
        from services.cartflow_duplicate_guard import (  # noqa: PLC0415
            ANOMALY_DUPLICATE_ACTIVE_RECOVERY,
            ANOMALY_DUPLICATE_BEHAVIORAL_MERGE,
            get_duplicate_guard_diagnostics_readonly,
        )

        dup_guard_diag = get_duplicate_guard_diagnostics_readonly()
        sym_dup = frozenset(
            {
                ANOMALY_DUPLICATE_SEND_ATTEMPT,
                ANOMALY_SEND_AFTER_RETURN,
                ANOMALY_SEND_AFTER_CONVERSION,
                ANOMALY_DASHBOARD_PAYLOAD_CONFLICT,
                ANOMALY_DUPLICATE_ACTIVE_RECOVERY,
                ANOMALY_DUPLICATE_BEHAVIORAL_MERGE,
            }
        )
        ct = recent_anomaly_type_counts(limit=200)
        dup_anomaly_count = sum(int(ct.get(k, 0)) for k in sym_dup)
    except Exception:
        dup_guard_diag = {}
        dup_anomaly_count = 0

    dup_prev_ok = bool(dup_guard_diag.get("duplicate_prevention_runtime_ok", True))
    dup_blocked_recent = bool(dup_guard_diag.get("duplicate_send_blocked_recently", False))

    lc_diag: dict[str, Any] = {}
    try:
        from services.cartflow_lifecycle_guard import (  # noqa: PLC0415
            get_lifecycle_diagnostics_readonly,
        )

        lc_diag = get_lifecycle_diagnostics_readonly()
    except Exception:
        lc_diag = {}
    lc_runtime_ok = bool(lc_diag.get("lifecycle_runtime_ok", True))

    sess_diag: dict[str, Any] = {}
    try:
        from services.cartflow_session_consistency import (  # noqa: PLC0415
            get_session_consistency_diagnostics_readonly,
        )

        sess_diag = get_session_consistency_diagnostics_readonly()
    except Exception:
        sess_diag = {}

    ob_rt: dict[str, Any] = {}
    try:
        from services.cartflow_onboarding_readiness import (  # noqa: PLC0415
            build_onboarding_health_section,
        )

        ob_rt = build_onboarding_health_section()
    except Exception:
        ob_rt = {}

    pr_ready: dict[str, Any] = {}
    try:
        from services.cartflow_provider_readiness import (  # noqa: PLC0415
            get_whatsapp_provider_readiness,
            log_provider_readiness_snapshot,
        )

        pr_ready = get_whatsapp_provider_readiness()
        log_provider_readiness_snapshot(pr_ready)
    except Exception:
        pr_ready = {}

    return {
        "recovery_runtime": {
            "runtime_active": recovery_active,
            "last_error_seen": not recovery_active,
            "duplicate_prevention_active": bool(flat.get("duplicate_prevention_active")),
        },
        "whatsapp_runtime": {
            "runtime_active": wa_ready,
            "whatsapp_provider_configured": tw["twilio_env_present"],
            "provider_disabled_state": not tw["twilio_env_present"],
        },
        "identity_runtime": {
            "runtime_active": ident_ok,
            "identity_resolution_ok": ident_ok,
            "identity_conflict_detected": bool(id_conflict),
        },
        "dashboard_runtime": {
            "runtime_active": bool(flat.get("dashboard_runtime_active")),
            "dashboard_payload_runtime_ok": True,
        },
        "duplicate_protection_runtime": {
            "duplicate_prevention_active": bool(flat.get("duplicate_prevention_active")),
            "runtime_active": True,
            "duplicate_prevention_runtime_ok": dup_prev_ok,
            "duplicate_anomaly_count": int(dup_anomaly_count),
            "duplicate_send_blocked_recently": dup_blocked_recent,
            "duplicate_guard_counters": dup_guard_diag.get("counters", {}),
            "duplicate_inflight_send_keys": dup_guard_diag.get("inflight_send_keys", 0),
        },
        "lifecycle_consistency_runtime": {
            "lifecycle_runtime_ok": lc_runtime_ok,
            "lifecycle_conflict_detected": bool(
                lc_diag.get("lifecycle_conflict_detected", False)
            ),
            "invalid_transition_recently": bool(
                lc_diag.get("invalid_transition_recently", False)
            ),
            "runtime_state_consistent": bool(lc_diag.get("runtime_state_consistent", True)),
            "lifecycle_counters": lc_diag.get("counters", {}),
            "lifecycle_conflict_events_recent": int(
                lc_diag.get("lifecycle_conflict_events_recent", 0)
            ),
        },
        "session_consistency_runtime": {
            **sess_diag,
        },
        "onboarding_runtime": dict(ob_rt),
        "behavioral_runtime": {
            "behavioral_merge_runtime_ok": lc_runtime_ok,
            "runtime_active": recovery_active,
            "behavioral_state_consistent": bool(
                sess_diag.get("behavioral_state_consistent", True)
            ),
            "session_consistency_counters": sess_diag.get("counters", {}),
        },
        "provider_runtime": {
            "whatsapp_provider_ready": wa_ready,
            "provider_runtime_available": wa_ready,
            **tw,
            "recent_send_failures_24h": fail_n,
            "provider_effectively_disabled": not tw["twilio_env_present"],
            "provider_readiness_ready": bool(pr_ready.get("ready", False)),
            "provider_readiness_configured": bool(pr_ready.get("configured", False)),
            "provider_readiness_provider": str(pr_ready.get("provider") or "unknown"),
            "provider_readiness_mode": str(pr_ready.get("mode") or "unknown"),
            "provider_failure_class": str(pr_ready.get("failure_class") or ""),
            "provider_readiness_summary": {
                k: pr_ready[k]
                for k in (
                    "provider",
                    "configured",
                    "ready",
                    "mode",
                    "failure_class",
                    "merchant_label_ar",
                    "merchant_action_ar",
                    "missing_env",
                )
                if k in pr_ready
            },
            "onboarding_completion_percent": int(ob_rt.get("onboarding_completion_percent") or 0),
            "onboarding_ready_flag": bool(ob_rt.get("onboarding_ready", True)),
        },
        "_buffered_anomaly_events": buf_n,
    }


def derive_runtime_trust_signals(
    snapshot: Optional[dict[str, Any]] = None,
    *,
    recent_anomaly_count: Optional[int] = None,
) -> dict[str, Any]:
    """Coarse trust tri-state for dashboards (merchant-safe Arabic label)."""
    snap = snapshot if isinstance(snapshot, dict) else build_runtime_health_snapshot()
    pr = snap.get("provider_runtime") if isinstance(snap.get("provider_runtime"), dict) else {}
    rr = snap.get("recovery_runtime") if isinstance(snap.get("recovery_runtime"), dict) else {}
    ir = snap.get("identity_runtime") if isinstance(snap.get("identity_runtime"), dict) else {}
    dup_rt = (
        snap.get("duplicate_protection_runtime")
        if isinstance(snap.get("duplicate_protection_runtime"), dict)
        else {}
    )
    lc_rt = (
        snap.get("lifecycle_consistency_runtime")
        if isinstance(snap.get("lifecycle_consistency_runtime"), dict)
        else {}
    )
    sc_rt = (
        snap.get("session_consistency_runtime")
        if isinstance(snap.get("session_consistency_runtime"), dict)
        else {}
    )
    ob_rt = (
        snap.get("onboarding_runtime")
        if isinstance(snap.get("onboarding_runtime"), dict)
        else {}
    )

    prov_ok = bool(pr.get("whatsapp_provider_ready")) and not bool(pr.get("provider_effectively_disabled"))
    rec_ok = bool(rr.get("runtime_active"))
    ident_ok = bool(ir.get("identity_resolution_ok"))
    id_conflict = bool(ir.get("identity_conflict_detected"))
    dup_ok = bool(dup_rt.get("duplicate_prevention_runtime_ok", True))
    lc_ok = bool(lc_rt.get("lifecycle_runtime_ok", True))
    sess_runtime_ok = bool(sc_rt.get("session_runtime_consistent", True))
    stale_any = bool(sc_rt.get("stale_state_detected", False))
    onb_ready = bool(ob_rt.get("onboarding_ready", True))

    if recent_anomaly_count is None:
        with _anomaly_lock:
            recent_anomaly_count = len(_recent_anomalies)

    warn = (
        recent_anomaly_count > 0
        or (not prov_ok)
        or (not rec_ok)
        or id_conflict
        or (not dup_ok)
        or (not lc_ok)
        or (not sess_runtime_ok)
        or stale_any
        or (not onb_ready)
    )
    degraded = (not prov_ok) or (not rec_ok) or (not ident_ok) or (not dup_ok) or (not lc_ok)

    label_ar = "حالة التشغيل مستقرة"
    if degraded:
        label_ar = "توفّر بعض ضبط البيئة أو الاتصال للمراجعة"
    elif warn:
        label_ar = "مراقبة خفيفة — راجع الإشارات التشغيلية عند الحاجة"

    return {
        "runtime_stable": not degraded and not warn,
        "runtime_degraded": degraded,
        "runtime_warning": warn and not degraded,
        "runtime_trust_label_ar": label_ar,
        "session_runtime_consistent": sess_runtime_ok,
        "stale_state_detected": stale_any,
        "runtime_state_drift_detected": bool(sc_rt.get("runtime_state_drift_detected", False)),
        "behavioral_state_consistent": bool(sc_rt.get("behavioral_state_consistent", True)),
        "onboarding_ready": onb_ready,
        "onboarding_blocked": bool(ob_rt.get("onboarding_blocked", False)),
        "onboarding_completion_percent": int(ob_rt.get("onboarding_completion_percent") or 0),
    }


def build_admin_runtime_summary() -> dict[str, Any]:
    """
    Internal / admin-safe JSON-style summary (no secrets, no stack traces).

    For future admin routes — not wired to HTTP yet.
    """
    snap = build_runtime_health_snapshot()
    with _anomaly_lock:
        buf_len = len(_recent_anomalies)
        types_preview = dict(
            Counter(str(x.get("type") or "?") for x in list(_recent_anomalies)[-20:])
        )

    signals = derive_runtime_trust_signals(snap, recent_anomaly_count=buf_len)

    pr = snap.get("provider_runtime") if isinstance(snap.get("provider_runtime"), dict) else {}
    rr = snap.get("recovery_runtime") if isinstance(snap.get("recovery_runtime"), dict) else {}
    ir = snap.get("identity_runtime") if isinstance(snap.get("identity_runtime"), dict) else {}

    return {
        "recovery_runtime_ok": bool(rr.get("runtime_active")),
        "identity_runtime_ok": bool(ir.get("identity_resolution_ok"))
        and not bool(ir.get("identity_conflict_detected")),
        "provider_runtime_ok": bool(pr.get("whatsapp_provider_ready")),
        "dashboard_runtime_ok": bool(
            (snap.get("dashboard_runtime") or {}).get("runtime_active")
            if isinstance(snap.get("dashboard_runtime"), dict)
            else True
        ),
        "recent_anomaly_count": buf_len,
        "recent_anomaly_types_preview": types_preview,
        "duplicate_protection": {
            "duplicate_anomaly_count": (
                int((snap.get("duplicate_protection_runtime") or {}).get("duplicate_anomaly_count") or 0)
                if isinstance(snap.get("duplicate_protection_runtime"), dict)
                else 0
            ),
            "duplicate_send_blocked_recently": bool(
                (snap.get("duplicate_protection_runtime") or {}).get(
                    "duplicate_send_blocked_recently"
                )
            )
            if isinstance(snap.get("duplicate_protection_runtime"), dict)
            else False,
        },
        "lifecycle_consistency": {
            "lifecycle_conflict_detected": bool(
                (snap.get("lifecycle_consistency_runtime") or {}).get(
                    "lifecycle_conflict_detected"
                )
            )
            if isinstance(snap.get("lifecycle_consistency_runtime"), dict)
            else False,
            "invalid_transition_recently": bool(
                (snap.get("lifecycle_consistency_runtime") or {}).get(
                    "invalid_transition_recently"
                )
            )
            if isinstance(snap.get("lifecycle_consistency_runtime"), dict)
            else False,
        },
        "session_consistency": {
            "session_runtime_consistent": bool(
                (snap.get("session_consistency_runtime") or {}).get(
                    "session_runtime_consistent", True
                )
            )
            if isinstance(snap.get("session_consistency_runtime"), dict)
            else True,
            "stale_state_detected": bool(
                (snap.get("session_consistency_runtime") or {}).get("stale_state_detected", False)
            )
            if isinstance(snap.get("session_consistency_runtime"), dict)
            else False,
            "runtime_state_drift_detected": bool(
                (snap.get("session_consistency_runtime") or {}).get(
                    "runtime_state_drift_detected", False
                )
            )
            if isinstance(snap.get("session_consistency_runtime"), dict)
            else False,
            "behavioral_state_consistent": bool(
                (snap.get("session_consistency_runtime") or {}).get(
                    "behavioral_state_consistent", True
                )
            )
            if isinstance(snap.get("session_consistency_runtime"), dict)
            else True,
        },
        "onboarding": {
            "onboarding_ready": bool(
                (snap.get("onboarding_runtime") or {}).get("onboarding_ready", True)
            )
            if isinstance(snap.get("onboarding_runtime"), dict)
            else True,
            "onboarding_blocked": bool(
                (snap.get("onboarding_runtime") or {}).get("onboarding_blocked", False)
            )
            if isinstance(snap.get("onboarding_runtime"), dict)
            else False,
            "onboarding_completion_percent": int(
                (snap.get("onboarding_runtime") or {}).get("onboarding_completion_percent") or 0
            )
            if isinstance(snap.get("onboarding_runtime"), dict)
            else 0,
            "sandbox_mode_active": bool(
                (snap.get("onboarding_runtime") or {}).get("sandbox_mode_active", False)
            )
            if isinstance(snap.get("onboarding_runtime"), dict)
            else False,
        },
        "trust": {
            "runtime_stable": signals["runtime_stable"],
            "runtime_degraded": signals["runtime_degraded"],
            "runtime_warning": signals["runtime_warning"],
            "runtime_trust_label_ar": signals["runtime_trust_label_ar"],
            "session_runtime_consistent": signals.get("session_runtime_consistent", True),
            "stale_state_detected": signals.get("stale_state_detected", False),
            "runtime_state_drift_detected": signals.get("runtime_state_drift_detected", False),
            "behavioral_state_consistent": signals.get("behavioral_state_consistent", True),
            "onboarding_ready": signals.get("onboarding_ready", True),
            "onboarding_completion_percent": signals.get("onboarding_completion_percent", 0),
        },
        "provider": {
            "configured": bool(pr.get("twilio_env_present")),
            "recent_send_failures_24h": pr.get("recent_send_failures_24h"),
            "provider_readiness_ready": bool(pr.get("provider_readiness_ready", False)),
            "provider_readiness_configured": bool(pr.get("provider_readiness_configured", False)),
            "provider_failure_class": pr.get("provider_failure_class"),
        },
    }
