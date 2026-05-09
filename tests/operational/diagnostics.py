# -*- coding: utf-8 -*-
"""
Read-only operational snapshot for tests or manual inspection.

This module does not register HTTP routes. It mirrors fields the operator cares about
without mutating application state beyond reading in-memory guards.
"""
from __future__ import annotations

from typing import Any

from services.recovery_session_phone import (
    get_recovery_customer_phone,
    get_recovery_phone_resolution_source,
)


def build_operational_diagnostics_snapshot(*, probe_recovery_key: str = "__operational_probe__") -> dict[str, Any]:
    """
    Returns a small dict suitable for assertions or log correlation.
    DB-backed fields (last_recovery_status, return_to_site) are not queried here to
    keep the helper lightweight; tests that need them should query models directly.
    """
    import main as m

    with m._recovery_session_lock:
        dup_guard = {
            "started_len": len(m._session_recovery_started),
            "logged_len": len(m._session_recovery_logged),
            "sent_len": len(m._session_recovery_sent),
            "returned_len": len(m._session_recovery_returned),
            "converted_len": len(m._session_recovery_converted),
        }
    rk = (probe_recovery_key or "").strip()[:800]
    phone_probe = get_recovery_customer_phone(rk) if rk else None
    src_probe = get_recovery_phone_resolution_source(rk) if rk else "customer_profile"
    try:
        from services.cartflow_duplicate_guard import get_duplicate_guard_diagnostics_readonly

        dup_diag = get_duplicate_guard_diagnostics_readonly()
    except Exception:
        dup_diag = {}
    return {
        "runtime_status": {
            "module": "main",
            "app_loaded": getattr(m, "app", None) is not None,
        },
        "duplicate_send_guard": dup_guard,
        "duplicate_guard_operational": dup_diag,
        "phone_resolution": {
            "probe_key": rk,
            "probe_phone_is_empty": not (phone_probe or "").strip(),
            "probe_resolution_source": src_probe,
        },
        "last_recovery_status": "query CartRecoveryLog / dashboard payloads in tests",
        "return_to_site_status": "query AbandonedCart.raw_payload cf_behavioral or behavioral APIs in tests",
    }
