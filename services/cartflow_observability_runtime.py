# -*- coding: utf-8 -*-
"""
CartFlow operational observability: structured diagnostics and read-only health signals.

Does not alter recovery scheduling, WhatsApp send behavior, or identity merge rules.
New logs use consistent prefixes; legacy print/log lines remain unchanged.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

log = logging.getLogger("cartflow")

# --- Diagnostic categories (for grep / metrics routing) ---
CATEGORY_IDENTITY = "identity"
CATEGORY_RECOVERY = "recovery"
CATEGORY_WHATSAPP = "whatsapp"
CATEGORY_SCHEDULING = "scheduling"
CATEGORY_DUPLICATE_PROTECTION = "duplicate_protection"
CATEGORY_BEHAVIORAL_MERGE = "behavioral_merge"
CATEGORY_DASHBOARD_RUNTIME = "dashboard_runtime"
CATEGORY_PROVIDER = "provider"
CATEGORY_FRONTEND_RUNTIME = "frontend_runtime"
CATEGORY_STATE_TRANSITION = "state_transition"

# --- Structured log line prefixes (new observability only) ---
PREFIX_DIAGNOSTIC = "[CARTFLOW DIAGNOSTIC]"
PREFIX_RECOVERY = "[CARTFLOW RECOVERY]"
PREFIX_WHATSAPP = "[CARTFLOW WHATSAPP]"
PREFIX_STATE = "[CARTFLOW STATE]"
PREFIX_IDENTITY = "[CARTFLOW IDENTITY]"
# Existing production identity drift banner (unchanged elsewhere):
#   [CARTFLOW IDENTITY WARNING]


class RecoveryLifecycleEvent:
    """Trace tokens for recovery pipeline observability (logging only)."""

    RECOVERY_CREATED = "recovery_created"
    WAITING_DELAY = "waiting_delay"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    SKIPPED_MISSING_PHONE = "skipped_missing_phone"
    SKIPPED_RETURNED = "skipped_returned"
    SKIPPED_CONVERTED = "skipped_converted"
    QUEUED = "queued"
    SEND_STARTED = "send_started"
    SEND_SUCCESS = "send_success"
    SEND_FAILED = "send_failed"
    REPLY_RECEIVED = "reply_received"
    RETURNED_TO_SITE = "returned_to_site"
    MERGE_BLOCKED = "merge_blocked"
    TRUST_WARNING = "trust_warning"
    AUTOMATION_GATED = "automation_gated"


def emit_structured_runtime_line(
    prefix: str,
    category: str,
    message: str,
    **fields: Any,
) -> None:
    """Single-line structured operational log (merchant-safe values only in fields)."""
    p = (prefix or "").strip()[:32] or PREFIX_DIAGNOSTIC
    cat = (category or "").strip()[:48] or "-"
    msg = (message or "").strip()[:240] or "-"
    parts = [p, f"category={cat}", f"msg={msg}"]
    for k in sorted(fields.keys()):
        key = str(k).strip()[:48]
        if not key:
            continue
        val = fields[k]
        if val is None:
            sval = "-"
        else:
            sval = str(val).strip().replace("\n", " ")[:512] or "-"
        parts.append(f"{key}={sval}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.info("%s", line)


def trace_recovery_lifecycle(
    event: str,
    *,
    session_id: str = "",
    cart_id: str = "",
    store_slug: str = "",
    extra_status: str = "",
) -> None:
    """Correlate one cart/session across recovery events (stdout + logger)."""
    emit_structured_runtime_line(
        PREFIX_RECOVERY,
        CATEGORY_RECOVERY,
        "lifecycle",
        event=(event or "").strip()[:64] or "-",
        session_id=(session_id or "").strip()[:128] or "-",
        cart_id=(cart_id or "").strip()[:128] or "-",
        store_slug=(store_slug or "").strip()[:128] or "-",
        detail=(extra_status or "").strip()[:128] or "-",
    )


def trace_recovery_lifecycle_from_log_status(
    *,
    status: str,
    session_id: str,
    cart_id: Optional[str],
    store_slug: str,
) -> None:
    """Map CartRecoveryLog.status to a lifecycle trace event (diagnostics only)."""
    s = (status or "").strip().lower()
    ev = RecoveryLifecycleEvent.AUTOMATION_GATED
    if s in ("mock_sent", "sent_real"):
        ev = RecoveryLifecycleEvent.SEND_SUCCESS
    elif s == "whatsapp_failed":
        ev = RecoveryLifecycleEvent.SEND_FAILED
    elif s == "queued":
        ev = RecoveryLifecycleEvent.QUEUED
    elif s == "skipped_duplicate":
        ev = RecoveryLifecycleEvent.SKIPPED_DUPLICATE
    elif s in ("skipped_no_verified_phone",):
        ev = RecoveryLifecycleEvent.SKIPPED_MISSING_PHONE
    elif s in ("skipped_anti_spam", "returned_to_site"):
        ev = RecoveryLifecycleEvent.SKIPPED_RETURNED
    elif s in ("stopped_converted",):
        ev = RecoveryLifecycleEvent.SKIPPED_CONVERTED
    elif s in (
        "skipped_delay_gate",
        "skipped_reason_template_disabled",
        "skipped_attempt_limit",
        "skipped_missing_reason_tag",
        "skipped_missing_last_activity",
    ):
        ev = RecoveryLifecycleEvent.WAITING_DELAY
    elif s.startswith("skipped_followup") or s == "skipped_user_rejected_help":
        ev = RecoveryLifecycleEvent.REPLY_RECEIVED
    trace_recovery_lifecycle(
        ev,
        session_id=session_id,
        cart_id=cart_id or "",
        store_slug=store_slug,
        extra_status=s[:64],
    )


def runtime_health_snapshot_readonly() -> dict[str, bool]:
    """
    Lightweight read-only flags for operators (no side effects, no secrets).

    Values are best-effort; false does not mean the feature is broken in tests.
    """
    import os

    from extensions import db, text

    flags: dict[str, bool] = {
        "duplicate_prevention_active": True,
        "identity_resolution_ok": False,
        "whatsapp_provider_ready": False,
        "recovery_runtime_active": False,
        "dashboard_runtime_active": True,
    }
    try:
        sid = (os.getenv("TWILIO_ACCOUNT_SID") or "").strip()
        tok = (os.getenv("TWILIO_AUTH_TOKEN") or "").strip()
        frm = (os.getenv("TWILIO_WHATSAPP_FROM") or "").strip()
        flags["whatsapp_provider_ready"] = bool(sid and tok and frm)
    except OSError:
        flags["whatsapp_provider_ready"] = False
    try:
        db.create_all()
        db.session.scalar(text("SELECT 1"))
        flags["recovery_runtime_active"] = True
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        flags["recovery_runtime_active"] = False
    try:
        from main import _dashboard_recovery_store_row  # noqa: PLC0415

        flags["identity_resolution_ok"] = _dashboard_recovery_store_row() is not None
    except Exception:
        flags["identity_resolution_ok"] = False
    return flags


def detect_recovery_runtime_conflicts(
    *,
    abandoned_status: str,
    behavioral: dict[str, Any],
    latest_log_status: Optional[str],
    identity_trust_failed: bool,
    sent_ok_latest_log: bool,
    recovery_log_statuses: Optional[frozenset[str]] = None,
) -> list[str]:
    """
    Return symbolic conflict codes (no PII). Callers may log via log_runtime_conflicts.

    Read-only heuristics; may produce false positives on edge ordering.
    """
    conflicts: list[str] = []
    st = (abandoned_status or "").strip().lower()
    bh_returned = behavioral.get("user_returned_to_site") is True
    log_s = (latest_log_status or "").strip().lower()
    sent_ok = bool(sent_ok_latest_log)
    log_ss = recovery_log_statuses or frozenset()
    durable_return_evidence = "returned_to_site" in log_ss
    if st == "recovered" and sent_ok:
        conflicts.append("recovered_cart_with_send_success_log")
    if identity_trust_failed and sent_ok:
        conflicts.append("identity_trust_failed_with_send_success_log")
    if log_s == "skipped_anti_spam" and not bh_returned and not durable_return_evidence:
        conflicts.append("anti_spam_skip_without_behavioral_return")
    return conflicts


def log_runtime_conflicts(
    conflicts: list[str],
    *,
    session_id: str = "",
    cart_id: str = "",
    category: str = CATEGORY_STATE_TRANSITION,
) -> None:
    for code in conflicts:
        c = (code or "").strip()[:80]
        if not c:
            continue
        emit_structured_runtime_line(
            PREFIX_DIAGNOSTIC,
            category,
            "runtime_conflict",
            code=c,
            session_id=(session_id or "").strip()[:128] or "-",
            cart_id=(cart_id or "").strip()[:128] or "-",
        )

