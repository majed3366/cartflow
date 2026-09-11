# -*- coding: utf-8 -*-
"""Merchant store platform connection (Zid OAuth) — authenticated store only."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from secrets import compare_digest
from typing import Any, Optional

from extensions import db
from models import Store
from services.merchant_onboarding_store import (
    merchant_store_display_name,
    resolve_merchant_onboarding_store,
)

log = logging.getLogger("cartflow")

_OAUTH_STATE_PREAMBLE = b"cartflow-store-oauth-v1|"
_OAUTH_STATE_TTL_S = 30 * 60


def _signing_secret() -> bytes:
    return (
        os.getenv("SECRET_KEY") or "dev-only-change-in-production"
    ).strip().encode("utf-8")


def is_merchant_store_platform_connected(store: Optional[Any]) -> bool:
    """True only for CONNECTED_VERIFIED. Access token presence is not sufficient."""
    from services.merchant_connection_capability_v1 import store_connection_is_verified

    return store_connection_is_verified(store)


def _format_dt_ar(dt: Optional[datetime]) -> str:
    if dt is None:
        return "—"
    d = dt
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _infer_platform_ar(store: Optional[Any], *, connected: bool) -> str:
    if not connected or store is None:
        return "—"
    return "زد"


@dataclass
class MerchantStoreConnectionStatus:
    connected: bool
    status_label_ar: str
    status_description_ar: str
    store_name: str
    platform_ar: str
    connected_at_ar: str
    zid_connect_available: bool
    zid_connect_url: str
    salla_connect_available: bool
    shopify_note_ar: str
    pending_setup_message_ar: str
    widget_installation_status: Optional[str] = None
    widget_status_label_ar: str = "—"
    widget_status_description_ar: str = ""
    widget_installed_at_ar: str = "—"
    widget_last_seen_at_ar: str = "—"
    widget_install_error: Optional[str] = None
    store_connected_ok: bool = False
    widget_installed_ok: bool = False
    connection_state: str = ""
    verified: bool = False
    platform: str = ""
    auth_state: str = ""
    identity_state: str = ""
    capability_state: str = ""
    verified_at: Optional[str] = None
    failure_reason: Optional[str] = None

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "status_label_ar": self.status_label_ar,
            "status_description_ar": self.status_description_ar,
            "store_name": self.store_name,
            "platform_ar": self.platform_ar,
            "connected_at_ar": self.connected_at_ar,
            "zid_connect_available": self.zid_connect_available,
            "zid_connect_url": self.zid_connect_url,
            "salla_connect_available": self.salla_connect_available,
            "shopify_note_ar": self.shopify_note_ar,
            "pending_setup_message_ar": self.pending_setup_message_ar,
            "widget_installation_status": self.widget_installation_status,
            "widget_status_label_ar": self.widget_status_label_ar,
            "widget_status_description_ar": self.widget_status_description_ar,
            "widget_installed_at_ar": self.widget_installed_at_ar,
            "widget_last_seen_at_ar": self.widget_last_seen_at_ar,
            "widget_install_error": self.widget_install_error,
            "store_connected_ok": self.store_connected_ok,
            "widget_installed_ok": self.widget_installed_ok,
            "connection_state": self.connection_state,
            "verified": self.verified,
            "platform": self.platform,
            "auth_state": self.auth_state,
            "identity_state": self.identity_state,
            "capability_state": self.capability_state,
            "verified_at": self.verified_at,
            "failure_reason": self.failure_reason,
        }


def build_merchant_store_connection_status(
    *,
    cookies: Optional[dict[str, str]] = None,
) -> MerchantStoreConnectionStatus:
    from services.dashboard_snapshot_hot_path_guard_v1 import guard_dashboard_hot_path

    guard_dashboard_hot_path("store_connection_live", endpoint="store-connection")
    store, meta = resolve_merchant_onboarding_store(cookies=cookies)
    store_name = meta.store_name or merchant_store_display_name(store)
    return build_merchant_store_connection_status_for_store(
        store,
        store_name=store_name,
    )


def build_merchant_store_connection_status_for_store(
    store: Optional[Any],
    *,
    store_name: Optional[str] = None,
) -> MerchantStoreConnectionStatus:
    from integrations.zid_client import zid_oauth_configured
    from services.merchant_connection_capability_v1 import (
        read_store_connection_capability,
        store_has_platform_credentials,
    )
    from services.zid_storefront_widget_install_v1 import build_widget_install_api_fields

    name = (store_name or merchant_store_display_name(store) or "").strip()
    cap = read_store_connection_capability(store)
    connected = bool(cap.verified)
    zid_ready = zid_oauth_configured()
    pending_msg = "ميزة الربط قيد الإعداد"
    widget_fields = (
        build_widget_install_api_fields(store, connected=connected)
        if store is not None
        else build_widget_install_api_fields(None, connected=False)
    )
    platform_ar = "زد" if store_has_platform_credentials(store) or connected else "—"
    connected_at = cap.verified_at
    connected_at_ar = _format_dt_ar(connected_at) if connected else "—"
    cap_dict = cap.to_api_dict()

    return MerchantStoreConnectionStatus(
        connected=connected,
        status_label_ar=cap.merchant_label_ar,
        status_description_ar=cap.merchant_description_ar,
        store_name=name,
        platform_ar=platform_ar,
        connected_at_ar=connected_at_ar,
        zid_connect_available=zid_ready,
        zid_connect_url="/api/merchant/store-connection/zid/connect",
        salla_connect_available=False,
        shopify_note_ar="Shopify قريباً",
        pending_setup_message_ar=pending_msg,
        widget_installation_status=widget_fields.get("widget_installation_status"),
        widget_status_label_ar=widget_fields.get("widget_status_label_ar") or "—",
        widget_status_description_ar=widget_fields.get(
            "widget_status_description_ar"
        )
        or "",
        widget_installed_at_ar=widget_fields.get("widget_installed_at_ar") or "—",
        widget_last_seen_at_ar=widget_fields.get("widget_last_seen_at_ar") or "—",
        widget_install_error=widget_fields.get("widget_install_error"),
        store_connected_ok=connected,
        widget_installed_ok=bool(widget_fields.get("widget_installed_ok")),
        connection_state=cap.connection_state,
        verified=connected,
        platform=cap.platform,
        auth_state=cap.auth_state,
        identity_state=cap.identity_state,
        capability_state=cap.capability_state,
        verified_at=cap_dict.get("verified_at"),
        failure_reason=cap.failure_reason,
    )


def issue_oauth_state(*, merchant_user_id: int, store_id: int) -> str:
    exp = int(time.time()) + _OAUTH_STATE_TTL_S
    payload = _OAUTH_STATE_PREAMBLE + f"{int(store_id)}:{int(merchant_user_id)}:{exp}".encode(
        "ascii"
    )
    sig = hmac.new(_signing_secret(), payload, hashlib.sha256).hexdigest()
    return f"{int(store_id)}:{int(merchant_user_id)}:{exp}:{sig}"


def parse_oauth_state(raw: str | None) -> Optional[tuple[int, int]]:
    if not raw or raw.count(":") != 3:
        return None
    store_s, mid_s, exp_s, sig = raw.split(":", 3)
    try:
        store_id = int(store_s)
        merchant_id = int(mid_s)
        exp = int(exp_s)
    except ValueError:
        return None
    if store_id <= 0 or merchant_id <= 0 or exp < int(time.time()):
        return None
    payload = _OAUTH_STATE_PREAMBLE + f"{store_id}:{merchant_id}:{exp}".encode("ascii")
    expected = hmac.new(_signing_secret(), payload, hashlib.sha256).hexdigest()
    if not compare_digest(sig.encode("ascii"), expected.encode("ascii")):
        return None
    return store_id, merchant_id


def apply_oauth_token_to_merchant_store(
    *,
    store_id: int,
    merchant_user_id: int,
    token_response: dict[str, Any],
) -> bool:
    """
    Persist OAuth tokens on the authenticated merchant's Store row only.
    Does not use latest-store or demo fallbacks.
    """
    from integrations.zid_client import persist_oauth_tokens_on_store_row

    from schema_zid_oauth_authorization import ensure_store_zid_oauth_authorization_schema

    ensure_store_zid_oauth_authorization_schema(db)
    row = db.session.get(Store, int(store_id))
    if row is None:
        return False
    owner = getattr(row, "merchant_user_id", None)
    if owner is not None and int(owner) != int(merchant_user_id):
        log.warning(
            "[STORE CONNECTION] ownership_mismatch store_id=%s merchant_id=%s owner=%s",
            store_id,
            merchant_user_id,
            owner,
        )
        return False
    if not persist_oauth_tokens_on_store_row(row, token_response):
        return False
    try:
        from services.store_identity_v1 import ensure_cartflow_zid_alias_for_store

        ensure_cartflow_zid_alias_for_store(row)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "[STORE CONNECTION] cartflow_alias_failed store_id=%s err=%s",
            store_id,
            type(exc).__name__,
        )
    db.session.commit()
    log.info(
        "[STORE CONNECTION] oauth_applied store_id=%s merchant_id=%s zid_store_id=%s",
        store_id,
        merchant_user_id,
        (row.zid_store_id or "")[:64],
    )
    try:
        from services.zid_connection_verification_v1 import (  # noqa: PLC0415
            verify_and_persist_zid_connection,
        )

        verify_and_persist_zid_connection(row, trigger="merchant_oauth")
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "[STORE CONNECTION] verification_failed store_id=%s err=%s",
            store_id,
            type(exc).__name__,
        )
        try:
            from services.merchant_connection_capability_v1 import (
                STATE_VERIFICATION_PENDING,
                persist_connection_failure_state,
            )

            persist_connection_failure_state(row, STATE_VERIFICATION_PENDING)
            row.connected_at = None
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    try:
        from services.zid_storefront_widget_install_v1 import (  # noqa: PLC0415
            maybe_install_zid_storefront_widget,
        )

        maybe_install_zid_storefront_widget(row, trigger="merchant_oauth")
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "[STORE CONNECTION] widget_install_trigger_failed store_id=%s err=%s",
            store_id,
            type(exc).__name__,
        )
    return True


def disconnect_merchant_store(
    *,
    cookies: Optional[dict[str, str]] = None,
) -> tuple[bool, str]:
    from services.merchant_connection_capability_v1 import store_has_platform_credentials

    store, meta = resolve_merchant_onboarding_store(cookies=cookies)
    if store is None:
        if meta.source == "unauthenticated":
            return False, "يلزم تسجيل الدخول."
        return False, "لم يُعثر على متجر مرتبط بحسابك."
    if not store_has_platform_credentials(store) and not getattr(
        store, "connected_at", None
    ):
        return True, "المتجر غير مربوط بالفعل."

    store.access_token = ""
    store.zid_authorization_token = None
    store.refresh_token = None
    store.token_expires_at = None
    store.connected_at = None
    try:
        from services.merchant_connection_capability_v1 import (
            clear_connection_failure_state,
        )

        clear_connection_failure_state(store)
    except Exception:  # noqa: BLE001
        pass
    db.session.commit()
    log.info(
        "[STORE CONNECTION] disconnected store_id=%s merchant_id=%s",
        getattr(store, "id", None),
        meta.merchant_id,
    )
    try:
        from services.zid_connection_verification_v1 import (  # noqa: PLC0415
            _refresh_store_connection_snapshot,
        )

        _refresh_store_connection_snapshot(store)
    except Exception:  # noqa: BLE001
        pass
    return True, "تم فصل الربط."


def resolve_connect_context(
    *,
    cookies: Optional[dict[str, str]] = None,
) -> tuple[Optional[Store], Optional[int], str]:
    store, meta = resolve_merchant_onboarding_store(cookies=cookies)
    if meta.merchant_id is None:
        return None, None, "يلزم تسجيل الدخول."
    if store is None:
        return None, int(meta.merchant_id), "لم يُعثر على متجر مرتبط بحسابك."
    return store, int(meta.merchant_id), ""


__all__ = [
    "MerchantStoreConnectionStatus",
    "apply_oauth_token_to_merchant_store",
    "build_merchant_store_connection_status",
    "disconnect_merchant_store",
    "is_merchant_store_platform_connected",
    "issue_oauth_state",
    "parse_oauth_state",
    "resolve_connect_context",
]
