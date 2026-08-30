# -*- coding: utf-8 -*-
"""HTTP composition helpers. Called from main.py middleware only."""
from __future__ import annotations

from typing import Any, Optional

from services.db_lifecycle_v1.connection_trace import maybe_install_connection_trace
from services.db_lifecycle_v1.pool_truth import pool_truth_snapshot
from services.db_lifecycle_v1.request_owner import (
    bind_admission,
    bind_merchant_safe,
    request_owner_begin,
    request_owner_end,
)
from services.db_lifecycle_v1.request_session_scope import (
    begin_logical_session_scope,
    end_logical_session_scope,
)
from services.db_lifecycle_v1.unit_of_work import release_before_response

# Always-heavy GETs: admit before auth DB. Projection stays handler-level
# (cache hit must not consume a heavy slot).
HEAVY_GET_ROUTES = frozenset(
    {
        "/api/dashboard/messages",
        "/api/dashboard/followups",
        "/api/dashboard/normal-carts",
    }
)


def bind_request(request: Any) -> dict[str, Any]:
    maybe_install_connection_trace()
    rec = request_owner_begin(request)
    token = begin_logical_session_scope(request_id=str(rec.get("request_id") or ""))
    try:
        request.state.db_lifecycle_request_id = rec.get("request_id") or ""
        request.state.db_logical_scope_token = token
    except Exception:  # noqa: BLE001
        pass
    return rec


def maybe_reject_heavy_before_db(request: Any) -> Optional[Any]:
    """
    INV-DB-07 / INV-DB-08: admit heavy GETs before auth/store DB.

    Cookie-less auth-required paths return 401 without a checkout.
    """
    path = getattr(getattr(request, "url", None), "path", "") or "/"
    method = (getattr(request, "method", "") or "").upper()
    if method != "GET" or path not in HEAVY_GET_ROUTES:
        bind_admission("n/a")
        return None

    try:
        from services.merchant_auth_v1 import (
            development_dashboard_bypass_active,
            merchant_id_from_request_cookies,
            path_requires_merchant_auth,
        )

        if path_requires_merchant_auth(path) and not development_dashboard_bypass_active():
            mid = merchant_id_from_request_cookies(dict(request.cookies))
            if not mid:
                bind_admission("skip_unauthenticated")
                from json_response import j

                return j({"ok": False, "error": "auth_required"}, 401)
    except Exception:  # noqa: BLE001
        pass

    from services.db_resource_safety_v1.admission_v1 import try_acquire

    if not try_acquire(path):
        bind_admission("rejected")
        from json_response import j

        return j({"ok": False, "error": "db_pressure"}, 503)
    bind_admission("admitted")
    try:
        request.state.db_lifecycle_admitted_route = path
    except Exception:  # noqa: BLE001
        pass
    return None


def release_admission_if_held(request: Any) -> None:
    route = ""
    try:
        route = str(getattr(request.state, "db_lifecycle_admitted_route", "") or "")
    except Exception:  # noqa: BLE001
        route = ""
    if not route:
        return
    try:
        from services.db_resource_safety_v1.admission_v1 import release

        release(route)
    except Exception:  # noqa: BLE001
        pass
    try:
        request.state.db_lifecycle_admitted_route = ""
    except Exception:  # noqa: BLE001
        pass


def release_identity_phase(store_slug: str = "") -> None:
    """INV-DB-03: auth resolved a slug string — do not keep the checkout."""
    if store_slug:
        bind_merchant_safe(store_slug)
    release_before_response(reason="identity_phase")


def finish_request(
    request: Any,
    *,
    status_code: Optional[int] = None,
    exception: str = "",
) -> dict[str, Any]:
    from services.db_lifecycle_v1.connection_trace import active_holders
    from services.db_lifecycle_v1.holder_diag_v1 import emit, thread_task_identity

    holders_before = active_holders()
    release_admission_if_held(request)
    # INV-OWN-05: remove() while the logical request scope is still bound.
    release_before_response(reason="request_finally")
    holders_after = active_holders()
    rec = request_owner_end(outcome=str(status_code or exception or "")) or {}
    rec["pool"] = pool_truth_snapshot()
    token = None
    try:
        token = getattr(request.state, "db_logical_scope_token", None)
    except Exception:  # noqa: BLE001
        token = None
    end_logical_session_scope(token)
    route = str(rec.get("route") or "")
    if route.startswith("/static/"):
        return rec
    ctx = thread_task_identity()
    emit(
        "[DB REQUEST FINALLY] request_id=%s route=%s status=%s request_ms=%s "
        "finally_thread=%s/%s holders_before=%s holders_after=%s "
        "checked_out=%s checkout_count=%s last_hold_ms=%s residual_threads=%s"
        % (
            rec.get("request_id") or "-",
            rec.get("route") or "-",
            rec.get("outcome") or "",
            rec.get("request_ms"),
            ctx["thread_ident"],
            ctx["thread_name"],
            len(holders_before),
            len(holders_after),
            (rec.get("pool") or {}).get("checked_out"),
            rec.get("checkout_count"),
            rec.get("last_hold_ms"),
            ",".join(
                str(h.get("thread_ident") or "")
                for h in holders_after
            ) or "-",
        )
    )
    return rec


__all__ = [
    "HEAVY_GET_ROUTES",
    "bind_request",
    "finish_request",
    "maybe_reject_heavy_before_db",
    "release_admission_if_held",
    "release_identity_phase",
]
