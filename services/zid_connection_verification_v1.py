# -*- coding: utf-8 -*-
"""
Zid Adapter — verified connection (Manager probe + external identity bind).

Runs only during OAuth callback / explicit reconnect verification.
Never called from dashboard render.
Does not enable Scheduler, recovery campaigns, WhatsApp, or storefront execution.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from services.merchant_connection_capability_v1 import (
    STATE_AUTH_INCOMPLETE,
    STATE_AUTH_REJECTED,
    STATE_CONNECTED_VERIFIED,
    STATE_IDENTITY_MISMATCH,
    STATE_RECONNECT_REQUIRED,
    STATE_VERIFICATION_PENDING,
    StoreConnectionCapability,
    clear_connection_failure_state,
    credentials_known_expired,
    persist_connection_failure_state,
    read_store_connection_capability,
    store_has_authorization_token,
    store_has_dual_tokens,
)
from services.store_identity_v1 import (
    ALIAS_KIND_ZID_NUMERIC_ID,
    ALIAS_KIND_ZID_PERMALINK,
    PLATFORM_ZID,
    canonical_store_slug_on_row,
    collect_zid_identities_from_manager_store,
    extract_zid_permalink_from_url,
    register_store_identity_alias,
    resolve_store_row_by_identifier,
)

log = logging.getLogger("cartflow")

_MANAGER_PROBE_TIMEOUT_S = 8.0


def _log_verify(**fields: Any) -> None:
    parts = ["[ZID CONNECTION VERIFY]"]
    for key, val in fields.items():
        if val is None:
            continue
        parts.append(f"{key}={str(val)[:180]}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def _digit_id(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s.isdigit() else None


def extract_zid_external_identity(payload: Any) -> tuple[Optional[str], Optional[str]]:
    """Authenticated Manager JSON → (numeric_id, permalink). No secrets."""
    numeric: Optional[str] = None
    permalink: Optional[str] = None
    for kind, value, _plat in collect_zid_identities_from_manager_store(payload):
        if kind == ALIAS_KIND_ZID_NUMERIC_ID and value and numeric is None:
            numeric = _digit_id(value) or numeric
        elif kind == ALIAS_KIND_ZID_PERMALINK and value and permalink is None:
            permalink = str(value).strip()
    if isinstance(payload, dict):
        if numeric is None:
            numeric = _digit_id(payload.get("id")) or _digit_id(payload.get("store_id"))
            store_obj = payload.get("store")
            if numeric is None and isinstance(store_obj, dict):
                numeric = _digit_id(store_obj.get("id"))
            data_obj = payload.get("data")
            if numeric is None and isinstance(data_obj, dict):
                numeric = _digit_id(data_obj.get("id")) or _digit_id(
                    data_obj.get("store_id")
                )
                nested = data_obj.get("store")
                if numeric is None and isinstance(nested, dict):
                    numeric = _digit_id(nested.get("id"))
        if permalink is None:
            for path in (
                ("url",),
                ("store", "url"),
                ("data", "url"),
                ("data", "store", "url"),
            ):
                cur: Any = payload
                ok = True
                for part in path:
                    if not isinstance(cur, dict):
                        ok = False
                        break
                    cur = cur.get(part)
                if ok and isinstance(cur, str) and cur.strip():
                    permalink = extract_zid_permalink_from_url(cur.strip()) or permalink
                    if permalink:
                        break
    if numeric is not None and not numeric.isdigit():
        numeric = None
    return numeric, permalink


def _identity_conflict(
    store: Any,
    *,
    numeric_id: str,
    permalink: Optional[str],
) -> bool:
    """Fail closed when authenticated Zid identity belongs to another CartFlow store."""
    sid = int(store.id)
    owner, _via = resolve_store_row_by_identifier(numeric_id)
    if owner is not None and int(getattr(owner, "id", 0) or 0) != sid:
        return True
    existing_numeric = [
        (getattr(a, "alias_value", None) or "").strip()
        for a in getattr(store, "identity_aliases", [])  # type: ignore[union-attr]
        if False
    ]
    # identity_aliases is dynamic; do not iterate relationship (extra queries).
    # Compare against loaded bundle in caller instead.
    _ = existing_numeric
    if permalink:
        pl_owner, _pl_via = resolve_store_row_by_identifier(permalink)
        if pl_owner is not None and int(getattr(pl_owner, "id", 0) or 0) != sid:
            return True
    return False


def _bind_authenticated_identity(
    store: Any,
    *,
    numeric_id: str,
    permalink: Optional[str],
    existing_numeric: list[str],
    existing_permalinks: list[str],
) -> bool:
    """Persist zid_numeric_id (and permalink) on THIS store only. Never reassign."""
    sid = int(store.id)
    if existing_numeric and numeric_id not in existing_numeric:
        return False
    if existing_permalinks and permalink and permalink not in existing_permalinks:
        return False
    if _identity_conflict(store, numeric_id=numeric_id, permalink=permalink):
        return False
    if not register_store_identity_alias(
        store_id=sid,
        alias_kind=ALIAS_KIND_ZID_NUMERIC_ID,
        alias_value=numeric_id,
        platform=PLATFORM_ZID,
    ):
        return False
    if permalink:
        if not register_store_identity_alias(
            store_id=sid,
            alias_kind=ALIAS_KIND_ZID_PERMALINK,
            alias_value=permalink,
            platform=PLATFORM_ZID,
        ):
            owner, _via = resolve_store_row_by_identifier(permalink)
            if owner is not None and int(getattr(owner, "id", 0) or 0) != sid:
                return False
    return True


def _fail(
    store: Any,
    state: str,
    *,
    reason: str,
    recovery_attempts_before: Any,
    whatsapp_before: Any,
    active_before: Any,
    keep_connected_at: bool = False,
) -> StoreConnectionCapability:
    persist_connection_failure_state(store, state)
    if not keep_connected_at:
        store.connected_at = None
    try:
        db.session.commit()
    except (SQLAlchemyError, OSError):
        db.session.rollback()
    _assert_no_execution_activation(
        store,
        recovery_attempts_before=recovery_attempts_before,
        whatsapp_before=whatsapp_before,
        active_before=active_before,
    )
    cap = read_store_connection_capability(store)
    _log_verify(
        store_id=getattr(store, "id", None),
        slug=(canonical_store_slug_on_row(store) or "-")[:64],
        state=cap.connection_state or state,
        reason=reason,
        verified="false",
        connected_at_written="false",
    )
    return cap


def _assert_no_execution_activation(
    store: Any,
    *,
    recovery_attempts_before: Any,
    whatsapp_before: Any,
    active_before: Any,
) -> None:
    """Connection verification must not flip execution switches."""
    try:
        if int(getattr(store, "recovery_attempts", 0) or 0) != int(
            recovery_attempts_before or 0
        ):
            store.recovery_attempts = recovery_attempts_before
    except (TypeError, ValueError):
        pass
    if getattr(store, "whatsapp_recovery_enabled", None) != whatsapp_before:
        store.whatsapp_recovery_enabled = whatsapp_before
    if bool(getattr(store, "is_active", True)) != bool(active_before):
        store.is_active = active_before


def verify_and_persist_zid_connection(
    store: Any,
    *,
    trigger: str = "oauth",
) -> StoreConnectionCapability:
    """
    Bounded Manager verification for one store row.

    Writes connected_at and zid_numeric_id only after CONNECTED_VERIFIED.
    """
    from integrations.zid_client import probe_zid_manager_store

    if store is None:
        return read_store_connection_capability(None)

    recovery_attempts_before = getattr(store, "recovery_attempts", None)
    whatsapp_before = getattr(store, "whatsapp_recovery_enabled", None)
    active_before = getattr(store, "is_active", True)

    slug = (canonical_store_slug_on_row(store) or "-")[:64]
    _log_verify(
        trigger=(trigger or "-")[:32],
        store_id=getattr(store, "id", None),
        slug=slug,
        dual_tokens=str(store_has_dual_tokens(store)).lower(),
        authorization=str(store_has_authorization_token(store)).lower(),
    )

    if not store_has_dual_tokens(store):
        return _fail(
            store,
            STATE_AUTH_INCOMPLETE,
            reason="dual_token_incomplete",
            recovery_attempts_before=recovery_attempts_before,
            whatsapp_before=whatsapp_before,
            active_before=active_before,
        )

    if credentials_known_expired(store):
        return _fail(
            store,
            STATE_RECONNECT_REQUIRED,
            reason="expired",
            recovery_attempts_before=recovery_attempts_before,
            whatsapp_before=whatsapp_before,
            active_before=active_before,
            keep_connected_at=True,
        )

    from services.merchant_connection_capability_v1 import load_store_connection_identity

    identity = load_store_connection_identity(int(store.id), store=store)
    existing_numeric = list(identity.get("zid_numeric_ids") or [])
    existing_permalinks = list(identity.get("zid_permalinks") or [])

    body, status, outcome = probe_zid_manager_store(
        store, timeout_s=_MANAGER_PROBE_TIMEOUT_S
    )
    _log_verify(
        store_id=getattr(store, "id", None),
        probe_outcome=outcome,
        http_status=status,
    )

    if outcome == "auth_incomplete":
        return _fail(
            store,
            STATE_AUTH_INCOMPLETE,
            reason="dual_token_incomplete",
            recovery_attempts_before=recovery_attempts_before,
            whatsapp_before=whatsapp_before,
            active_before=active_before,
        )
    if outcome == "auth_rejected":
        return _fail(
            store,
            STATE_AUTH_REJECTED,
            reason="manager_rejected",
            recovery_attempts_before=recovery_attempts_before,
            whatsapp_before=whatsapp_before,
            active_before=active_before,
        )
    if outcome != "ok" or body is None:
        return _fail(
            store,
            STATE_VERIFICATION_PENDING,
            reason="probe_unavailable",
            recovery_attempts_before=recovery_attempts_before,
            whatsapp_before=whatsapp_before,
            active_before=active_before,
        )

    numeric_id, permalink = extract_zid_external_identity(body)
    if not numeric_id:
        return _fail(
            store,
            STATE_IDENTITY_MISMATCH,
            reason="identity_unresolved",
            recovery_attempts_before=recovery_attempts_before,
            whatsapp_before=whatsapp_before,
            active_before=active_before,
        )

    if not _bind_authenticated_identity(
        store,
        numeric_id=numeric_id,
        permalink=permalink,
        existing_numeric=existing_numeric,
        existing_permalinks=existing_permalinks,
    ):
        return _fail(
            store,
            STATE_IDENTITY_MISMATCH,
            reason="identity_mismatch",
            recovery_attempts_before=recovery_attempts_before,
            whatsapp_before=whatsapp_before,
            active_before=active_before,
        )

    clear_connection_failure_state(store)
    store.connected_at = datetime.now(timezone.utc)
    _assert_no_execution_activation(
        store,
        recovery_attempts_before=recovery_attempts_before,
        whatsapp_before=whatsapp_before,
        active_before=active_before,
    )
    try:
        db.session.commit()
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return _fail(
            store,
            STATE_VERIFICATION_PENDING,
            reason="persist_failed",
            recovery_attempts_before=recovery_attempts_before,
            whatsapp_before=whatsapp_before,
            active_before=active_before,
        )

    cap = read_store_connection_capability(store)
    _log_verify(
        store_id=getattr(store, "id", None),
        slug=slug,
        state=STATE_CONNECTED_VERIFIED,
        zid_numeric_id=numeric_id,
        permalink=(permalink or "-")[:64],
        verified="true",
        connected_at_written="true",
        scheduler_activated="false",
    )
    return cap


def verify_zid_connection_for_slug(store_slug: str) -> StoreConnectionCapability:
    """Live-server helper: verify the named CartFlow store. No Scheduler changes."""
    from models import Store

    slug = (store_slug or "").strip()
    row = db.session.query(Store).filter(Store.zid_store_id == slug).first()
    if row is None:
        return read_store_connection_capability(None)
    return verify_and_persist_zid_connection(row, trigger="live_slug")


__all__ = [
    "extract_zid_external_identity",
    "verify_and_persist_zid_connection",
    "verify_zid_connection_for_slug",
]
