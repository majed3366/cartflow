# -*- coding: utf-8 -*-
"""
Portable merchant connection capability — server-owned, platform-agnostic shape.

Zid dual-header / Manager probe logic lives in the Zid adapter verification module.
Merchant UI consumes this normalized status only.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import StoreIdentityAlias

STATE_CONNECTED_VERIFIED = "CONNECTED_VERIFIED"
STATE_RECONNECT_REQUIRED = "RECONNECT_REQUIRED"
STATE_AUTH_INCOMPLETE = "AUTH_INCOMPLETE"
STATE_AUTH_REJECTED = "AUTH_REJECTED"
STATE_IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
STATE_VERIFICATION_PENDING = "VERIFICATION_PENDING"

MERCHANT_LABEL_AR: dict[str, str] = {
    STATE_CONNECTED_VERIFIED: "تم الربط",
    STATE_RECONNECT_REQUIRED: "إعادة الربط مطلوبة",
    STATE_AUTH_INCOMPLETE: "لم يكتمل الربط",
    STATE_AUTH_REJECTED: "تعذر التحقق من الربط",
    STATE_IDENTITY_MISMATCH: "تعذر تأكيد هوية المتجر",
    STATE_VERIFICATION_PENDING: "جارٍ التحقق من الربط",
}

MERCHANT_DESCRIPTION_AR: dict[str, str] = {
    STATE_CONNECTED_VERIFIED: "",
    STATE_RECONNECT_REQUIRED: "انتهت صلاحية الربط. أعد الربط للمتابعة.",
    STATE_AUTH_INCOMPLETE: "لم يكتمل الربط. أعد المحاولة من إعدادات الحساب.",
    STATE_AUTH_REJECTED: "تعذر التحقق من الربط. أعد الربط للمتابعة.",
    STATE_IDENTITY_MISMATCH: "تعذر تأكيد هوية المتجر. تأكد من اختيار المتجر الصحيح.",
    STATE_VERIFICATION_PENDING: "جارٍ التحقق من الربط. لن يظهر «تم الربط» قبل نجاح التحقق.",
}

DISCONNECTED_LABEL_AR = "غير مربوط"
DISCONNECTED_DESCRIPTION_AR = "ابدأ بربط متجرك لتفعيل استرجاع السلال."

ALIAS_KIND_PLATFORM_CONNECTION_STATE = "platform_connection_state"

AUTH_STATE_MISSING = "missing"
AUTH_STATE_INCOMPLETE = "incomplete"
AUTH_STATE_READY = "ready"
AUTH_STATE_EXPIRED = "expired"
AUTH_STATE_REJECTED = "rejected"

IDENTITY_STATE_UNBOUND = "unbound"
IDENTITY_STATE_BOUND = "bound"
IDENTITY_STATE_MISMATCH = "mismatch"

CAPABILITY_STATE_NONE = "none"
CAPABILITY_STATE_VERIFIED = "verified"
CAPABILITY_STATE_NOT_VERIFIED = "not_verified"


def _present_secret(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _as_utc(dt: Any) -> Optional[datetime]:
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def credentials_known_expired(store: Any) -> bool:
    exp = _as_utc(getattr(store, "token_expires_at", None) if store is not None else None)
    if exp is None:
        return False
    return exp < datetime.now(timezone.utc)


def store_has_access_token(store: Any) -> bool:
    return store is not None and _present_secret(getattr(store, "access_token", None))


def store_has_authorization_token(store: Any) -> bool:
    return store is not None and _present_secret(
        getattr(store, "zid_authorization_token", None)
    )


def store_has_platform_credentials(store: Any) -> bool:
    return store_has_access_token(store) or store_has_authorization_token(store)


def store_has_dual_tokens(store: Any) -> bool:
    return store_has_access_token(store) and store_has_authorization_token(store)


def _store_pk(store: Any) -> Optional[int]:
    if store is None:
        return None
    raw = getattr(store, "id", None)
    try:
        pk = int(raw)
    except (TypeError, ValueError):
        return None
    return pk if pk > 0 else None


@dataclass(frozen=True)
class StoreConnectionCapability:
    platform: str
    auth_state: str
    identity_state: str
    capability_state: str
    verified: bool
    verified_at: Optional[datetime]
    failure_reason: Optional[str]
    connection_state: str
    merchant_label_ar: str
    merchant_description_ar: str
    zid_numeric_id: Optional[str] = None
    zid_permalink: Optional[str] = None

    def to_api_dict(self) -> dict[str, Any]:
        verified_at = self.verified_at
        if verified_at is not None and verified_at.tzinfo is None:
            verified_at = verified_at.replace(tzinfo=timezone.utc)
        return {
            "platform": self.platform,
            "auth_state": self.auth_state,
            "identity_state": self.identity_state,
            "capability_state": self.capability_state,
            "verified": self.verified,
            "verified_at": verified_at.isoformat() if verified_at else None,
            "failure_reason": self.failure_reason,
            "connection_state": self.connection_state,
            "status_label_ar": self.merchant_label_ar,
            "zid_numeric_id": self.zid_numeric_id,
            "zid_permalink": self.zid_permalink,
        }


def _capability(
    *,
    connection_state: str,
    auth_state: str,
    identity_state: str,
    failure_reason: Optional[str] = None,
    verified_at: Optional[datetime] = None,
    zid_numeric_id: Optional[str] = None,
    zid_permalink: Optional[str] = None,
    platform: str = "zid",
) -> StoreConnectionCapability:
    verified = connection_state == STATE_CONNECTED_VERIFIED
    if connection_state:
        label = MERCHANT_LABEL_AR[connection_state]
        desc = MERCHANT_DESCRIPTION_AR[connection_state]
        cap_state = CAPABILITY_STATE_VERIFIED if verified else CAPABILITY_STATE_NOT_VERIFIED
    else:
        label = DISCONNECTED_LABEL_AR
        desc = DISCONNECTED_DESCRIPTION_AR
        cap_state = CAPABILITY_STATE_NONE
    return StoreConnectionCapability(
        platform=platform,
        auth_state=auth_state,
        identity_state=identity_state,
        capability_state=cap_state,
        verified=verified,
        verified_at=verified_at if verified else None,
        failure_reason=None if verified else failure_reason,
        connection_state=connection_state,
        merchant_label_ar=label,
        merchant_description_ar=desc,
        zid_numeric_id=zid_numeric_id,
        zid_permalink=zid_permalink,
    )


_STORE_IDENTITY_ATTR = "_cf_connection_identity_v1"


def invalidate_store_connection_identity(store: Any) -> None:
    if store is None:
        return
    try:
        delattr(store, _STORE_IDENTITY_ATTR)
    except Exception:
        pass


def load_store_connection_identity(store_id: int, store: Any = None) -> dict[str, Any]:
    """One store-scoped alias query: numeric id, permalink, persisted failure state."""
    if store is not None:
        cached = getattr(store, _STORE_IDENTITY_ATTR, None)
        if isinstance(cached, dict) and "zid_numeric_ids" in cached:
            return cached
    from services.store_identity_v1 import (
        ALIAS_KIND_ZID_NUMERIC_ID,
        ALIAS_KIND_ZID_PERMALINK,
        normalize_identity_value,
    )

    out: dict[str, Any] = {
        "zid_numeric_ids": [],
        "zid_permalinks": [],
        "persisted_state": None,
    }
    try:
        rows = (
            db.session.query(StoreIdentityAlias)
            .filter(StoreIdentityAlias.store_id == int(store_id))
            .filter(
                StoreIdentityAlias.alias_kind.in_(
                    (
                        ALIAS_KIND_ZID_NUMERIC_ID,
                        ALIAS_KIND_ZID_PERMALINK,
                        ALIAS_KIND_PLATFORM_CONNECTION_STATE,
                    )
                )
            )
            .all()
        )
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
        return out

    numeric: list[str] = []
    permalinks: list[str] = []
    persisted: Optional[str] = None
    prefix = f"{int(store_id)}:"
    for row in rows:
        kind = (getattr(row, "alias_kind", None) or "").strip()
        val = normalize_identity_value(getattr(row, "alias_value", None))
        if not val:
            continue
        if kind == ALIAS_KIND_ZID_NUMERIC_ID:
            numeric.append(val)
        elif kind == ALIAS_KIND_ZID_PERMALINK:
            permalinks.append(val)
        elif kind == ALIAS_KIND_PLATFORM_CONNECTION_STATE:
            if val.startswith(prefix):
                persisted = val[len(prefix) :].strip() or None
            elif ":" in val:
                persisted = val.split(":", 1)[-1].strip() or persisted
    out["zid_numeric_ids"] = numeric
    out["zid_permalinks"] = permalinks
    out["persisted_state"] = persisted
    if store is not None:
        try:
            setattr(store, _STORE_IDENTITY_ATTR, out)
        except Exception:
            pass
    return out


def persist_connection_failure_state(
    store: Any,
    state: str,
    *,
    session: Any = None,
) -> None:
    """Durably record a non-verified state. Does not write connected_at."""
    invalidate_store_connection_identity(store)
    pk = _store_pk(store)
    if pk is None:
        return
    if state not in {
        STATE_RECONNECT_REQUIRED,
        STATE_AUTH_INCOMPLETE,
        STATE_AUTH_REJECTED,
        STATE_IDENTITY_MISMATCH,
        STATE_VERIFICATION_PENDING,
    }:
        return
    sess = session or db.session
    try:
        sess.query(StoreIdentityAlias).filter(
            StoreIdentityAlias.store_id == pk,
            StoreIdentityAlias.alias_kind == ALIAS_KIND_PLATFORM_CONNECTION_STATE,
        ).delete(synchronize_session=False)
        sess.add(
            StoreIdentityAlias(
                store_id=pk,
                alias_kind=ALIAS_KIND_PLATFORM_CONNECTION_STATE,
                alias_value=f"{pk}:{state}"[:255],
                platform="zid",
            )
        )
        sess.flush()
    except (SQLAlchemyError, OSError):
        sess.rollback()


def clear_connection_failure_state(store: Any, *, session: Any = None) -> None:
    invalidate_store_connection_identity(store)
    pk = _store_pk(store)
    if pk is None:
        return
    sess = session or db.session
    try:
        sess.query(StoreIdentityAlias).filter(
            StoreIdentityAlias.store_id == pk,
            StoreIdentityAlias.alias_kind == ALIAS_KIND_PLATFORM_CONNECTION_STATE,
        ).delete(synchronize_session=False)
        sess.flush()
    except (SQLAlchemyError, OSError):
        sess.rollback()


def read_store_connection_capability(
    store: Any,
    *,
    identity: Optional[dict[str, Any]] = None,
) -> StoreConnectionCapability:
    """
    Canonical connection status from persisted store facts. No external HTTP.

    Query cost: +0 when ``identity`` is supplied; otherwise +1 store-scoped alias query.
    """
    if store is None:
        return _capability(
            connection_state="",
            auth_state=AUTH_STATE_MISSING,
            identity_state=IDENTITY_STATE_UNBOUND,
            platform="",
        )

    access = store_has_access_token(store)
    authorization = store_has_authorization_token(store)
    expired = credentials_known_expired(store)
    connected_at = _as_utc(getattr(store, "connected_at", None))
    pk = _store_pk(store)
    bundle = identity
    if bundle is None and pk is not None:
        bundle = load_store_connection_identity(pk, store=store)
    bundle = bundle or {
        "zid_numeric_ids": [],
        "zid_permalinks": [],
        "persisted_state": None,
    }
    numeric_ids = list(bundle.get("zid_numeric_ids") or [])
    permalinks = list(bundle.get("zid_permalinks") or [])
    persisted_state = bundle.get("persisted_state")
    numeric = numeric_ids[0] if numeric_ids else None
    permalink = permalinks[0] if permalinks else None
    identity_state = IDENTITY_STATE_BOUND if numeric else IDENTITY_STATE_UNBOUND
    if persisted_state == STATE_IDENTITY_MISMATCH:
        identity_state = IDENTITY_STATE_MISMATCH

    if not access and not authorization:
        return _capability(
            connection_state="",
            auth_state=AUTH_STATE_MISSING,
            identity_state=identity_state,
            zid_numeric_id=numeric,
            zid_permalink=permalink,
        )

    if not access or not authorization:
        return _capability(
            connection_state=STATE_AUTH_INCOMPLETE,
            auth_state=AUTH_STATE_INCOMPLETE,
            identity_state=identity_state,
            failure_reason=(
                "missing_authorization" if access else "missing_access_token"
            ),
            zid_numeric_id=numeric,
            zid_permalink=permalink,
        )

    if expired:
        return _capability(
            connection_state=STATE_RECONNECT_REQUIRED,
            auth_state=AUTH_STATE_EXPIRED,
            identity_state=identity_state,
            failure_reason="expired",
            zid_numeric_id=numeric,
            zid_permalink=permalink,
        )

    if (
        connected_at is not None
        and numeric
        and identity_state != IDENTITY_STATE_MISMATCH
    ):
        return _capability(
            connection_state=STATE_CONNECTED_VERIFIED,
            auth_state=AUTH_STATE_READY,
            identity_state=IDENTITY_STATE_BOUND,
            verified_at=connected_at,
            zid_numeric_id=numeric,
            zid_permalink=permalink,
        )

    if persisted_state == STATE_IDENTITY_MISMATCH or (
        connected_at is not None and not numeric
    ):
        return _capability(
            connection_state=STATE_IDENTITY_MISMATCH,
            auth_state=AUTH_STATE_READY,
            identity_state=IDENTITY_STATE_MISMATCH,
            failure_reason="identity_mismatch",
            zid_numeric_id=numeric,
            zid_permalink=permalink,
        )

    if persisted_state == STATE_AUTH_REJECTED:
        return _capability(
            connection_state=STATE_AUTH_REJECTED,
            auth_state=AUTH_STATE_REJECTED,
            identity_state=identity_state,
            failure_reason="manager_rejected",
            zid_numeric_id=numeric,
            zid_permalink=permalink,
        )

    if persisted_state == STATE_AUTH_INCOMPLETE:
        return _capability(
            connection_state=STATE_AUTH_INCOMPLETE,
            auth_state=AUTH_STATE_INCOMPLETE,
            identity_state=identity_state,
            failure_reason="auth_incomplete",
            zid_numeric_id=numeric,
            zid_permalink=permalink,
        )

    if persisted_state == STATE_RECONNECT_REQUIRED:
        return _capability(
            connection_state=STATE_RECONNECT_REQUIRED,
            auth_state=AUTH_STATE_EXPIRED,
            identity_state=identity_state,
            failure_reason="reconnect_required",
            zid_numeric_id=numeric,
            zid_permalink=permalink,
        )

    return _capability(
        connection_state=STATE_VERIFICATION_PENDING,
        auth_state=AUTH_STATE_READY,
        identity_state=identity_state,
        failure_reason="verification_pending",
        zid_numeric_id=numeric,
        zid_permalink=permalink,
    )


def store_connection_is_verified(store: Any) -> bool:
    """Authoritative connected predicate. Not access_token-only."""
    return read_store_connection_capability(store).verified


def apply_verified_connection_public_guard(payload: Any) -> dict[str, Any]:
    """Fail closed: never paint تم الربط unless verified is true."""
    if not isinstance(payload, dict):
        return {
            "connected": False,
            "verified": False,
            "store_connected_ok": False,
            "status_label_ar": DISCONNECTED_LABEL_AR,
        }
    out = dict(payload)
    inner = out.get("store_connection") if isinstance(out.get("store_connection"), dict) else None
    target = inner if inner is not None else out
    verified = bool(target.get("verified"))
    if verified:
        target["connected"] = True
        target["store_connected_ok"] = True
        target["status_label_ar"] = MERCHANT_LABEL_AR[STATE_CONNECTED_VERIFIED]
        return out
    target["connected"] = False
    target["store_connected_ok"] = False
    target["verified"] = False
    label = (target.get("status_label_ar") or "").strip()
    if label == MERCHANT_LABEL_AR[STATE_CONNECTED_VERIFIED]:
        state = (target.get("connection_state") or "").strip()
        target["status_label_ar"] = MERCHANT_LABEL_AR.get(state) or DISCONNECTED_LABEL_AR
        if not state:
            target["connection_state"] = STATE_VERIFICATION_PENDING
            target["status_label_ar"] = MERCHANT_LABEL_AR[STATE_VERIFICATION_PENDING]
    return out


def oauth_callback_redirect_params(cap: StoreConnectionCapability) -> dict[str, str]:
    if cap.verified:
        return {"store_connected": "1"}
    state = cap.connection_state
    if state == STATE_AUTH_INCOMPLETE:
        return {"store_connect_incomplete": "1"}
    if state == STATE_AUTH_REJECTED:
        return {"store_connect_rejected": "1"}
    if state == STATE_IDENTITY_MISMATCH:
        return {"store_connect_mismatch": "1"}
    if state == STATE_RECONNECT_REQUIRED:
        return {"store_connect_reconnect": "1"}
    if state == STATE_VERIFICATION_PENDING:
        return {"store_verification_pending": "1"}
    return {"store_connect_incomplete": "1"}


__all__ = [
    "ALIAS_KIND_PLATFORM_CONNECTION_STATE",
    "AUTH_STATE_EXPIRED",
    "AUTH_STATE_INCOMPLETE",
    "AUTH_STATE_MISSING",
    "AUTH_STATE_READY",
    "AUTH_STATE_REJECTED",
    "DISCONNECTED_DESCRIPTION_AR",
    "DISCONNECTED_LABEL_AR",
    "IDENTITY_STATE_BOUND",
    "IDENTITY_STATE_MISMATCH",
    "IDENTITY_STATE_UNBOUND",
    "MERCHANT_DESCRIPTION_AR",
    "MERCHANT_LABEL_AR",
    "STATE_AUTH_INCOMPLETE",
    "STATE_AUTH_REJECTED",
    "STATE_CONNECTED_VERIFIED",
    "STATE_IDENTITY_MISMATCH",
    "STATE_RECONNECT_REQUIRED",
    "STATE_VERIFICATION_PENDING",
    "StoreConnectionCapability",
    "clear_connection_failure_state",
    "credentials_known_expired",
    "load_store_connection_identity",
    "oauth_callback_redirect_params",
    "persist_connection_failure_state",
    "read_store_connection_capability",
    "apply_verified_connection_public_guard",
    "store_connection_is_verified",
    "store_has_access_token",
    "store_has_authorization_token",
    "store_has_dual_tokens",
    "store_has_platform_credentials",
]
