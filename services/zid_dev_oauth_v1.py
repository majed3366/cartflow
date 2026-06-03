# -*- coding: utf-8 -*-
"""
Zid Partner development-store OAuth activation (read-only marketplace install path).

Gated by ZID_DEV_OAUTH_ENABLED — does not replace merchant dashboard OAuth (signed state).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from extensions import db
from models import Store
from schema_production_store_bootstrap import ensure_production_store_schema

log = logging.getLogger("cartflow")

ZID_DEV_INTEGRATION_SOURCE = "zid_dev"
_MISSING_CODE_MESSAGE = (
    "Zid callback reached but no authorization code was received."
)


def zid_dev_oauth_enabled() -> bool:
    """Explicit opt-in for Zid development-store activation (not public marketplace)."""
    return (os.getenv("ZID_DEV_OAUTH_ENABLED") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _resolve_deploy_commit_short() -> str:
    for key in (
        "RAILWAY_GIT_COMMIT_SHA",
        "GIT_COMMIT",
        "SOURCE_VERSION",
        "COMMIT_SHA",
    ):
        val = (os.getenv(key) or "").strip()
        if val:
            return val[:7]
    return "unknown"


def zid_dev_oauth_runtime_check_log(*, branch: str) -> None:
    """Temporary runtime branch marker for Zid dev install OAuth verification."""
    enabled = "true" if zid_dev_oauth_enabled() else "false"
    line = (
        f"[ZID DEV CHECK] enabled={enabled} "
        f"commit={_resolve_deploy_commit_short()} branch={branch}"
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def zid_auth_zid_branch_trace_log(
    *,
    request: Any,
    branch: str,
    reason: str,
    enabled: bool,
    merchant_id: Optional[int] = None,
    store: Any = None,
    connect_err: str = "",
    resolution_source: str = "",
) -> None:
    """
    Trace why GET /auth/zid chose dev_oauth vs legacy_connect (no behavior change).

    dev_oauth only when ZID_DEV_OAUTH_ENABLED and merchant_id is None (no session cookie).
    legacy_connect when flag off OR any valid merchant session cookie is present.
    """
    from services.merchant_auth_http import merchant_cookie_name

    ck = dict(getattr(request, "cookies", {}) or {})
    cookie_names = sorted(ck.keys())[:16]
    mcn = merchant_cookie_name()
    has_merchant_cookie = mcn in ck
    store_id = getattr(store, "id", None) if store is not None else None
    line = (
        "[ZID AUTH/ZID BRANCH] "
        f"enabled={'true' if enabled else 'false'} "
        f"branch={branch} "
        f"reason={reason} "
        f"commit={_resolve_deploy_commit_short()} "
        f"merchant_id={merchant_id if merchant_id is not None else '-'} "
        f"store_present={'true' if store is not None else 'false'} "
        f"store_id={store_id if store_id is not None else '-'} "
        f"resolution_source={(resolution_source or '-')[:64]} "
        f"connect_err={(connect_err or '-')[:120]} "
        f"merchant_cookie_present={'true' if has_merchant_cookie else 'false'} "
        f"merchant_cookie_name={mcn} "
        f"cookie_names={','.join(cookie_names) if cookie_names else '-'}"
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def zid_oauth_activation_audit_log(
    *,
    route: str,
    request: Any,
    code: str = "",
    oauth_state: str = "",
    oauth_error: str = "",
    branch: str = "",
) -> None:
    """
    Temporary audit-only logging for Zid install/OAuth activation (no behavior change).

    Captures referer/user-agent to distinguish oauth.zid.sa redirects vs dashboard navigation.
    """
    headers = getattr(request, "headers", None)
    referer = "-"
    user_agent = "-"
    if headers is not None:
        referer = (headers.get("referer") or headers.get("Referer") or "-")[:220]
        user_agent = (headers.get("user-agent") or headers.get("User-Agent") or "-")[:220]
    qp = getattr(request, "query_params", None)
    keys = list(qp.keys()) if qp is not None else []
    raw_query = str(getattr(getattr(request, "url", None), "query", None) or "")
    code_val = (code or "").strip()
    state_val = (oauth_state or "").strip()
    err_val = (oauth_error or "").strip()
    if qp is not None and not err_val:
        err_val = (qp.get("error") or "").strip()
    parts = [
        "[ZID OAUTH AUDIT]",
        f"route={route}",
        f"query_keys={','.join(keys) if keys else '-'}",
        f"query_empty={str(not bool(keys)).lower()}",
        f"raw_query_len={len(raw_query)}",
        f"code_present={str(bool(code_val)).lower()}",
        f"error_present={str(bool(err_val)).lower()}",
        f"state_present={str(bool(state_val)).lower()}",
        f"state_len={len(state_val)}",
        f"referer={referer}",
        f"user_agent={user_agent}",
    ]
    if branch:
        parts.append(f"branch={branch}")
    if err_val:
        parts.append(f"oauth_error={err_val[:120]}")
    err_desc = (qp.get("error_description") or "").strip()[:160] if qp is not None else ""
    if err_desc:
        parts.append(f"oauth_error_description={err_desc}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def zid_dev_oauth_callback_query_log(request: Any) -> dict[str, Any]:
    """
    Log and summarize the callback query string (never log authorization codes).

    Browsers do not send URL fragments (#...) to the server — empty query with
    #code= in the address bar appears as no code here.
    """
    raw_query = str(getattr(getattr(request, "url", None), "query", None) or "")
    keys = list(getattr(request, "query_params", {}).keys())
    safe_parts: list[str] = []
    qp = getattr(request, "query_params", None)
    for key in keys:
        val = (qp.get(key) or "").strip() if qp is not None else ""
        if key == "code":
            safe_parts.append("code=[REDACTED]")
        else:
            safe_parts.append(f"{key}={val[:160]}")
    query_safe = "&".join(safe_parts) if safe_parts else "(empty)"
    line = (
        "[ZID OAUTH CALLBACK QUERY] "
        f"keys={','.join(keys) if keys else '-'} "
        f"raw_len={len(raw_query)} query_safe={query_safe[:480]}"
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass
    oauth_error = (qp.get("error") or "").strip() if qp is not None else ""
    oauth_error_description = (
        (qp.get("error_description") or "").strip()[:220] if qp is not None else ""
    )
    zid_oauth_activation_audit_log(
        route="/auth/callback",
        request=request,
        oauth_error=oauth_error,
        oauth_state=(qp.get("state") or "").strip() if qp is not None else "",
        code=(qp.get("code") or "").strip() if qp is not None else "",
    )
    return {
        "callback_query_keys": keys,
        "callback_query_empty": not bool(keys),
        "callback_query_safe": query_safe[:480],
        "callback_raw_query_len": len(raw_query),
        "oauth_error": oauth_error or None,
        "oauth_error_description": oauth_error_description or None,
    }


def zid_dev_oauth_log(event: str, **fields: str) -> None:
    parts = [f"[ZID OAUTH DEV] {event}"]
    for k, v in fields.items():
        parts.append(f"{k}={v}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def persist_zid_dev_store_from_token_response(
    token_response: dict[str, Any],
) -> Optional[Store]:
    """
    Upsert Store by zid_store_id from OAuth token response (development install only).
    """
    from integrations.zid_client import (
        fetch_zid_store_id_from_profile,
        parse_zid_store_id_from_token,
        persist_oauth_tokens_on_store_row,
    )

    ensure_production_store_schema(db, context="zid_oauth_persist")
    access = (token_response.get("access_token") or "").strip()
    if not access:
        return None
    zid = parse_zid_store_id_from_token(token_response) or fetch_zid_store_id_from_profile(
        access
    )
    if not zid:
        return None
    row = db.session.query(Store).filter(Store.zid_store_id == zid).first()
    if row is None:
        row = Store(zid_store_id=zid, is_active=True)
        db.session.add(row)
    prior_zid = (getattr(row, "zid_store_id", None) or "").strip()
    if not persist_oauth_tokens_on_store_row(row, token_response):
        return None
    now = datetime.now(timezone.utc)
    row.integration_source = ZID_DEV_INTEGRATION_SOURCE
    row.connected_at = now
    row.is_active = True
    try:
        from services.store_identity_v1 import sync_zid_store_identities_after_oauth

        sync_zid_store_identities_after_oauth(
            row,
            token_response=token_response,
            prior_zid=prior_zid if prior_zid != (row.zid_store_id or "").strip() else None,
        )
    except Exception:  # noqa: BLE001
        pass
    db.session.commit()
    try:
        from services.zid_storefront_widget_install_v1 import (  # noqa: PLC0415
            maybe_install_zid_storefront_widget,
        )

        maybe_install_zid_storefront_widget(row, trigger="zid_dev_oauth")
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "zid_dev_oauth widget_install_trigger_failed zid=%s err=%s",
            zid[:64],
            type(exc).__name__,
        )
    return row


def build_zid_dev_store_status_readonly() -> dict[str, Any]:
    """Read-only status for the latest zid_dev-connected store (no token leakage)."""
    ensure_production_store_schema(db, context="zid_dev_status")
    row = (
        db.session.query(Store)
        .filter(Store.integration_source == ZID_DEV_INTEGRATION_SOURCE)
        .order_by(Store.connected_at.desc(), Store.id.desc())
        .first()
    )
    if row is None:
        return {
            "connected": False,
            "zid_store_id": None,
            "integration_source": None,
            "connected_at": None,
            "token_present": False,
            "zid_dev_oauth_enabled": zid_dev_oauth_enabled(),
        }
    connected_at = getattr(row, "connected_at", None)
    if connected_at is not None and connected_at.tzinfo is None:
        connected_at = connected_at.replace(tzinfo=timezone.utc)
    return {
        "connected": bool((row.access_token or "").strip()),
        "zid_store_id": (row.zid_store_id or "").strip() or None,
        "integration_source": (row.integration_source or "").strip() or None,
        "connected_at": connected_at.isoformat() if connected_at else None,
        "token_present": bool((row.access_token or "").strip()),
        "zid_dev_oauth_enabled": zid_dev_oauth_enabled(),
    }
