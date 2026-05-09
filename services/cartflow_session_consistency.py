# -*- coding: utf-8 -*-
"""
Session / cart runtime consistency diagnostics (read-only signals).

Does not alter WhatsApp sends, recovery timing, lifecycle/duplicate/provider modules,
or database schema. Emits throttled structured logs and optional dashboard hints.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Optional

log = logging.getLogger("cartflow")

PREFIX_SESSION = "[CARTFLOW SESSION]"
PREFIX_CONSISTENCY = "[CARTFLOW CONSISTENCY]"

MERCHANT_STALE_IGNORED_AR = "تم تجاهل حالة قديمة لحماية السلة"
MERCHANT_CONFLICT_PREVENTED_AR = "تم منع تعارض في حالة السلة"
MERCHANT_DRIFT_HINT_AR = "تم ملاحظة اختلاف بسيط في عرض الحالة — يُعرض أحدث سياق موثوق."

_LOG_LOCK = threading.Lock()
_counters: dict[str, int] = {
    "session_log": 0,
    "consistency_log": 0,
    "stale_merge_signals": 0,
    "dashboard_drift": 0,
    "provider_stale_callbacks": 0,
    "frontend_stale_signals": 0,
}
_last_emit: dict[str, float] = {}
_EMIT_COOLDOWN_S = 90.0
_drift_anomaly_last: dict[str, float] = {}
# Recent event marks (monotonic seconds) for trust / health snapshots
_RECENT_WINDOW_S = 600.0
_last_dashboard_drift_mono: float = 0.0
_last_stale_behavioral_mono: float = 0.0
_last_provider_callback_stale_mono: float = 0.0
_last_frontend_stale_mono: float = 0.0


def session_consistency_log_enabled() -> bool:
    v = (os.getenv("CARTFLOW_SESSION_CONSISTENCY_LOG") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def structured_health_style_enabled() -> bool:
    v = (os.getenv("CARTFLOW_STRUCTURED_HEALTH_LOG") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _emit(
    prefix: str,
    kind: str,
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
    runtime_source: str = "",
    detected_state: str = "",
    canonical_state: str = "",
) -> None:
    if not (session_consistency_log_enabled() or structured_health_style_enabled()):
        return
    fp = f"{kind}|{(session_id or '')[:32]}|{(cart_id or '')[:24]}"
    now = time.monotonic()
    with _LOG_LOCK:
        tprev = _last_emit.get(fp)
        if tprev is not None and (now - tprev) < _EMIT_COOLDOWN_S:
            return
        _last_emit[fp] = now
        if len(_last_emit) > 300:
            _last_emit.clear()
    parts = [
        prefix,
        f"type={_safe(kind)}",
        f"store_slug={_safe(store_slug or '-')}",
        f"session_id={_safe((session_id or '')[:64])}",
        f"cart_id={_safe((cart_id or '')[:64])}",
        f"runtime_source={_safe(runtime_source or '-')}",
        f"detected_state={_safe(detected_state or '-')}",
        f"canonical_state={_safe(canonical_state or '-')}",
    ]
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.info("%s", line)


def _safe(s: str) -> str:
    return (s or "").strip().replace("\n", " ")[:200] or "-"


def emit_session_event(
    kind: str,
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
    runtime_source: str = "",
    detected_state: str = "",
    canonical_state: str = "",
) -> None:
    with _LOG_LOCK:
        _counters["session_log"] = int(_counters.get("session_log", 0)) + 1
    _emit(
        PREFIX_SESSION,
        kind,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        runtime_source=runtime_source,
        detected_state=detected_state,
        canonical_state=canonical_state,
    )


def emit_consistency_event(
    kind: str,
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
    runtime_source: str = "",
    detected_state: str = "",
    canonical_state: str = "",
) -> None:
    with _LOG_LOCK:
        _counters["consistency_log"] = int(_counters.get("consistency_log", 0)) + 1
    _emit(
        PREFIX_CONSISTENCY,
        kind,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        runtime_source=runtime_source,
        detected_state=detected_state,
        canonical_state=canonical_state,
    )


def validate_session_runtime_consistency(
    *,
    session_id: str,
    cart_id: str,
    store_slug: str = "",
) -> list[str]:
    """Return symbolic issue codes (empty list = OK). Diagnostics only."""
    issues: list[str] = []
    sid = (session_id or "").strip()
    cid = (cart_id or "").strip()
    if not sid and not cid:
        issues.append("missing_session_and_cart_scope")
    return issues


def detect_stale_behavioral_merge_intent(
    prior: dict[str, Any],
    raw_incoming: dict[str, Any],
) -> Optional[str]:
    """
    Detect pre-prune intent to weaken terminal engagement (for diagnostics).
    Does not modify data.
    """
    if not isinstance(prior, dict) or not isinstance(raw_incoming, dict):
        return None
    for k in (
        "customer_replied",
        "user_returned_to_site",
        "customer_returned_to_site",
        "recovery_link_clicked",
    ):
        if prior.get(k) is True and raw_incoming.get(k) is False:
            return f"weaken_terminal:{k}"
    ph = str(prior.get("lifecycle_hint") or "").strip().lower()
    nh = str(raw_incoming.get("lifecycle_hint") or "").strip().lower()
    strong_prior = ph in ("interactive", "clicked", "returned")
    if strong_prior:
        if nh in ("", "pending") or (nh != ph and nh not in ("interactive", "clicked", "returned")):
            return "lifecycle_hint_downgrade_intent"
    return None


def note_raw_behavioral_merge_for_session_consistency(
    prior: dict[str, Any],
    raw_incoming: dict[str, Any],
    *,
    session_id: str = "",
    cart_id: str = "",
    store_slug: str = "",
) -> None:
    """Call before lifecycle prune — logs only."""
    global _last_stale_behavioral_mono
    hint = detect_stale_behavioral_merge_intent(prior, raw_incoming)
    if not hint:
        return
    with _LOG_LOCK:
        _counters["stale_merge_signals"] = int(_counters.get("stale_merge_signals", 0)) + 1
        _last_stale_behavioral_mono = time.monotonic()
    emit_consistency_event(
        "stale_behavioral_merge",
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        runtime_source="behavioral_merge",
        detected_state=hint,
        canonical_state="terminal_preserved_by_prune",
    )


def detect_cross_runtime_mismatch(
    *,
    phase_key: str,
    latest_log_status: Optional[str],
    behavioral: dict[str, Any],
    sent_ct: int,
) -> list[str]:
    """
    Heuristic mismatch between dashboard phase, latest log, and behavioral snapshot.
    """
    issues: list[str] = []
    ls = (latest_log_status or "").strip().lower()
    pk = (phase_key or "").strip()
    bh = behavioral if isinstance(behavioral, dict) else {}

    if ls == "stopped_converted" and pk not in (
        "stopped_purchase",
        "recovery_complete",
    ):
        issues.append("log_converted_phase_mismatch")
    if bh.get("customer_replied") is True and ls == "queued":
        issues.append("replied_with_queued_log")
    if (
        bh.get("user_returned_to_site") is True
        and ls == "queued"
        and int(sent_ct or 0) == 0
    ):
        issues.append("returned_while_queued_pending")

    st = (bh.get("lifecycle_hint") or "").strip().lower()
    if st == "returned" and ls in ("mock_sent", "sent_real"):
        issues.append("lifecycle_returned_vs_send_success_log")

    return issues


def detect_dashboard_runtime_drift(
    *,
    phase_key: str,
    latest_log_status: Optional[str],
    behavioral: dict[str, Any],
    sent_ct: int,
) -> list[str]:
    return detect_cross_runtime_mismatch(
        phase_key=phase_key,
        latest_log_status=latest_log_status,
        behavioral=behavioral,
        sent_ct=sent_ct,
    )


def note_frontend_stale_state_intent(
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
    detected_state: str = "",
    canonical_state: str = "",
) -> None:
    """Diagnostics for widget/local snapshot lagging canonical runtime (no repair)."""
    global _last_frontend_stale_mono
    with _LOG_LOCK:
        _counters["frontend_stale_signals"] = int(
            _counters.get("frontend_stale_signals", 0)
        ) + 1
        _last_frontend_stale_mono = time.monotonic()
    emit_session_event(
        "frontend_state_stale",
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        runtime_source="widget_or_client",
        detected_state=detected_state or "stale_client_snapshot",
        canonical_state=canonical_state or "-",
    )


def note_stale_provider_callback_intent(
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
    detected_state: str = "",
    canonical_state: str = "",
) -> None:
    """Diagnostics-only hook for late/stale provider callbacks vs lifecycle (no repair)."""
    global _last_provider_callback_stale_mono
    with _LOG_LOCK:
        _counters["provider_stale_callbacks"] = int(
            _counters.get("provider_stale_callbacks", 0)
        ) + 1
        _last_provider_callback_stale_mono = time.monotonic()
    emit_consistency_event(
        "provider_callback_stale",
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        runtime_source="provider_callback",
        detected_state=detected_state or "late_or_conflicting",
        canonical_state=canonical_state or "-",
    )


def _maybe_record_session_drift_anomaly(cart_key: str, *, detail: str = "") -> None:
    now = time.monotonic()
    ck = (cart_key or "").strip()[:200]
    if not ck:
        ck = "-"
    with _LOG_LOCK:
        last = _drift_anomaly_last.get(ck)
        if last is not None and (now - last) < 120.0:
            return
        _drift_anomaly_last[ck] = now
        if len(_drift_anomaly_last) > 500:
            _drift_anomaly_last.clear()
    try:
        from services.cartflow_runtime_health import (  # noqa: PLC0415
            ANOMALY_DASHBOARD_PAYLOAD_CONFLICT,
            record_runtime_anomaly,
        )

        record_runtime_anomaly(
            ANOMALY_DASHBOARD_PAYLOAD_CONFLICT,
            source="session_consistency",
            detail=(detail or "runtime_drift")[:120],
        )
    except Exception:
        pass


def finalize_dashboard_session_payload(
    payload: dict[str, Any],
    *,
    ac: Any,
    phase_key: str,
    coarse: str,
    latest_log_status: Optional[str],
    behavioral: dict[str, Any],
    sent_ct: int,
    store_slug: str,
) -> None:
    """
    Add additive trust fields to normal recovery dashboard payload; never removes keys.
    """
    global _last_dashboard_drift_mono
    sid = str(getattr(ac, "recovery_session_id", None) or "").strip()
    cid = str(getattr(ac, "zid_cart_id", None) or "").strip()
    ss = (store_slug or "").strip()[:255] or "-"

    scope_issues = validate_session_runtime_consistency(
        session_id=sid, cart_id=cid, store_slug=ss
    )
    drift_issues = detect_dashboard_runtime_drift(
        phase_key=phase_key,
        latest_log_status=latest_log_status,
        behavioral=behavioral,
        sent_ct=int(sent_ct or 0),
    )
    all_issues = [*scope_issues, *drift_issues]
    ok = len(all_issues) == 0

    payload["normal_recovery_session_runtime_consistent"] = ok
    if all_issues:
        payload["normal_recovery_session_consistency_codes"] = all_issues
        if "log_converted_phase_mismatch" in all_issues:
            hint_ar = MERCHANT_STALE_IGNORED_AR
        elif "missing_session_and_cart_scope" in all_issues:
            hint_ar = MERCHANT_CONFLICT_PREVENTED_AR
        else:
            hint_ar = MERCHANT_DRIFT_HINT_AR
        payload["normal_recovery_session_trust_hint_ar"] = hint_ar
        with _LOG_LOCK:
            _counters["dashboard_drift"] = int(_counters.get("dashboard_drift", 0)) + 1
            _last_dashboard_drift_mono = time.monotonic()
        emit_consistency_event(
            "dashboard_runtime_mismatch",
            store_slug=ss,
            session_id=sid,
            cart_id=cid,
            runtime_source="normal_recovery_payload",
            detected_state=",".join(all_issues)[:120],
            canonical_state=phase_key,
        )
        _maybe_record_session_drift_anomaly(f"{ss}|{sid}|{cid}", detail=",".join(all_issues)[:80])

    _ = coarse  # reserved for future rules (no behavior change now)


def get_session_consistency_diagnostics_readonly() -> dict[str, Any]:
    now = time.monotonic()
    with _LOG_LOCK:
        ctr = dict(_counters)
        ld = float(_last_dashboard_drift_mono)
        ls = float(_last_stale_behavioral_mono)
        lf = float(_last_frontend_stale_mono)
        lpc = float(_last_provider_callback_stale_mono)
    recent_drift = bool(ld > 0.0 and (now - ld) < _RECENT_WINDOW_S)
    recent_stale = bool(
        (ls > 0.0 and (now - ls) < _RECENT_WINDOW_S)
        or (lf > 0.0 and (now - lf) < _RECENT_WINDOW_S)
        or (lpc > 0.0 and (now - lpc) < _RECENT_WINDOW_S)
    )
    return {
        "counters": ctr,
        "session_runtime_consistent": not recent_drift,
        "stale_state_detected": recent_stale,
        "runtime_state_drift_detected": recent_drift,
        "behavioral_state_consistent": not (
            ls > 0.0 and (now - ls) < _RECENT_WINDOW_S
        ),
        "recent_event_window_s": _RECENT_WINDOW_S,
    }


def reset_session_consistency_for_tests() -> None:
    global _last_dashboard_drift_mono
    global _last_stale_behavioral_mono
    global _last_provider_callback_stale_mono
    global _last_frontend_stale_mono
    with _LOG_LOCK:
        _counters.update({k: 0 for k in _counters})
        _last_emit.clear()
        _drift_anomaly_last.clear()
        _last_dashboard_drift_mono = 0.0
        _last_stale_behavioral_mono = 0.0
        _last_provider_callback_stale_mono = 0.0
        _last_frontend_stale_mono = 0.0
