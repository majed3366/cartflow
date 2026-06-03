# -*- coding: utf-8 -*-
"""
Zid storefront widget install orchestration (Partner Custom Snippet path).

Official Zid injection is via Partner Dashboard Custom Snippets (applied to stores
where the app is installed). There is no per-store POST install API; this module
verifies partner manifest + storefront presence and records honest status on Store.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from extensions import db
from schema_zid_widget_install import ensure_store_zid_widget_install_schema

log = logging.getLogger("cartflow")

_STATUS_INSTALLING = "installing"
_STATUS_INSTALLED = "installed"
_STATUS_FAILED = "failed"
_STATUS_UNSUPPORTED = "unsupported"
_STATUS_PENDING = "pending_partner_snippet"

_INSTALL_COOLDOWN = timedelta(minutes=5)
_VERIFY_STALE = timedelta(hours=24)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _public_widget_loader_url() -> str:
    base = (
        os.getenv("CARTFLOW_PUBLIC_BASE_URL")
        or os.getenv("PUBLIC_BASE_URL")
        or "https://smartreplyai.net"
    ).strip().rstrip("/")
    return f"{base}/static/widget_loader.js"


def _partner_snippet_approved_env() -> bool:
    return (os.getenv("ZID_PARTNER_WIDGET_SNIPPET_APPROVED") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _emit(tag: str, **fields: str) -> None:
    parts = [f"[{tag}]"]
    for k, v in fields.items():
        if v is None:
            continue
        parts.append(f"{k}={str(v)[:220]}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _manifest_contains_loader(manifest: Any, loader_url: str) -> bool:
    if not isinstance(manifest, dict):
        return False
    needle = "widget_loader"
    loader_host = urlparse(loader_url).netloc.lower()
    for item in manifest.get("external_scripts") or []:
        if not isinstance(item, dict):
            continue
        url = (item.get("url") or item.get("src") or "").strip()
        if not url:
            continue
        if needle in url.lower():
            return True
        if loader_host and loader_host in url.lower():
            return True
    bundle = manifest.get("app_scripts_bundle")
    if isinstance(bundle, dict):
        try:
            blob = json.dumps(bundle, ensure_ascii=False).lower()
        except (TypeError, ValueError):
            blob = str(bundle).lower()
        if needle in blob or "cartflow" in blob:
            return True
    return False


def _html_contains_loader(html: str, loader_url: str) -> bool:
    low = (html or "").lower()
    if "widget_loader" in low or "cartflow" in low:
        return True
    path = urlparse(loader_url).path
    if path and path.lower() in low:
        return True
    return False


def widget_installation_status_label_ar(status: str) -> str:
    s = (status or "").strip().lower()
    if s == _STATUS_INSTALLED:
        return "تم تثبيت الودجت"
    if s == _STATUS_INSTALLING:
        return "جاري التثبيت"
    if s == _STATUS_FAILED:
        return "فشل التثبيت"
    if s == _STATUS_UNSUPPORTED:
        return "غير مدعوم تلقائياً"
    if s == _STATUS_PENDING:
        return "بانتظار تفعيل شريك زد"
    return "—"


def widget_installation_description_ar(
    *,
    status: str,
    install_error: str = "",
    connected: bool,
) -> str:
    s = (status or "").strip().lower()
    if not connected:
        return ""
    if s == _STATUS_INSTALLED:
        return "يظهر الودجت في واجهة متجرك دون لصق كود يدوي."
    if s == _STATUS_INSTALLING:
        return "زد يفعّل الودجت عبر تطبيق CartFlow — افتح متجرك للتحقق خلال دقائق."
    if s == _STATUS_PENDING:
        return (
            "يلزم تفعيل Custom Snippet لـ CartFlow في لوحة شريك زد "
            "(مرة واحدة لكل المتاجر المثبتة)."
        )
    if s == _STATUS_UNSUPPORTED:
        return (
            "زد لا يوفّر API لتثبيت الودجت لكل متجر. "
            "تواصل مع الدعم لتفعيل مسار الشريك الرسمي."
        )
    if s == _STATUS_FAILED:
        err = (install_error or "").strip()
        if err:
            return f"تعذّر التحقق: {err[:160]}"
        return "تعذّر التحقق من ظهور الودجت — أعد الربط أو افتح المتجر."
    return ""


def build_widget_install_api_fields(store: Any, *, connected: bool) -> dict[str, Any]:
    if store is None:
        return {
            "widget_installation_status": None,
            "widget_status_label_ar": "—",
            "widget_status_description_ar": "",
            "widget_installed_at_ar": "—",
            "widget_last_seen_at_ar": "—",
            "widget_install_error": None,
            "store_connected_ok": connected,
            "widget_installed_ok": False,
        }
    status = (getattr(store, "widget_installation_status", None) or "").strip().lower()
    installed_at = _normalize_dt(getattr(store, "widget_installed_at", None))
    last_seen = _normalize_dt(getattr(store, "widget_last_seen_at", None))
    err = (getattr(store, "widget_install_error", None) or "").strip()
    return {
        "widget_installation_status": status or None,
        "widget_status_label_ar": widget_installation_status_label_ar(status),
        "widget_status_description_ar": widget_installation_description_ar(
            status=status,
            install_error=err,
            connected=connected,
        ),
        "widget_installed_at_ar": (
            installed_at.strftime("%Y-%m-%d") if installed_at else "—"
        ),
        "widget_last_seen_at_ar": (
            last_seen.strftime("%Y-%m-%d %H:%M") if last_seen else "—"
        ),
        "widget_install_error": err or None,
        "store_connected_ok": connected,
        "widget_installed_ok": status == _STATUS_INSTALLED,
    }


def _should_skip_reinstall(store: Any, *, force: bool) -> bool:
    if force:
        return False
    status = (getattr(store, "widget_installation_status", None) or "").strip().lower()
    if status == _STATUS_UNSUPPORTED:
        return True
    if status == _STATUS_INSTALLED:
        last_seen = _normalize_dt(getattr(store, "widget_last_seen_at", None))
        if last_seen and _utc_now() - last_seen < _VERIFY_STALE:
            return True
        installed_at = _normalize_dt(getattr(store, "widget_installed_at", None))
        if installed_at and _utc_now() - installed_at < _VERIFY_STALE:
            return True
    if status == _STATUS_INSTALLING:
        installed_at = _normalize_dt(getattr(store, "widget_installed_at", None))
        if installed_at and _utc_now() - installed_at < _INSTALL_COOLDOWN:
            return True
    return False


def record_widget_storefront_seen(*, store_slug: str) -> bool:
    """Update widget_last_seen_at when loader runs on a real storefront."""
    from services.store_identity_v1 import resolve_store_row_for_storefront_api

    slug = (store_slug or "").strip()
    if not slug or slug.lower() in ("demo", "default", "demo2"):
        return False
    ensure_store_zid_widget_install_schema(db)
    row, _via = resolve_store_row_for_storefront_api(slug)
    if row is None:
        return False
    now = _utc_now()
    row.widget_last_seen_at = now
    status = (row.widget_installation_status or "").strip().lower()
    if status in ("", _STATUS_INSTALLING, _STATUS_PENDING, _STATUS_FAILED):
        row.widget_installation_status = _STATUS_INSTALLED
        row.widget_installed_at = row.widget_installed_at or now
        row.widget_install_error = None
    db.session.commit()
    return True


def maybe_install_zid_storefront_widget(
    store: Any,
    *,
    trigger: str = "oauth",
    force: bool = False,
) -> dict[str, Any]:
    """
    After Zid OAuth link: verify partner snippet path and set install status.

    Does not claim success without manifest approval and/or storefront proof.
    """
    from integrations.zid_client import (
        fetch_zid_app_scripts_manifest,
        fetch_zid_manager_store_url,
        probe_storefront_for_widget_loader,
    )

    store_id = getattr(store, "id", None)
    zid_slug = (getattr(store, "zid_store_id", None) or "").strip()
    token = (getattr(store, "access_token", None) or "").strip()

    if store is None or not token:
        return {"ok": False, "skipped": True, "reason": "no_store_or_token"}

    ensure_store_zid_widget_install_schema(db)

    if _should_skip_reinstall(store, force=force):
        return {
            "ok": True,
            "skipped": True,
            "reason": "recent_status",
            "status": getattr(store, "widget_installation_status", None),
        }

    _emit(
        "ZID WIDGET INSTALL START",
        store_id=str(store_id or "-"),
        zid_store_id=zid_slug[:64] or "-",
        trigger=(trigger or "-")[:32],
    )

    loader_url = _public_widget_loader_url()
    manifest_ok = False
    manifest_detail = ""
    try:
        manifest, status = fetch_zid_app_scripts_manifest()
        if status // 100 == 2 and _manifest_contains_loader(manifest, loader_url):
            manifest_ok = True
        elif status == 0:
            manifest_detail = "manifest_unreachable"
        else:
            manifest_detail = f"manifest_http_{status}"
    except Exception as exc:  # noqa: BLE001
        manifest_detail = type(exc).__name__

    partner_env = _partner_snippet_approved_env()
    partner_path_available = manifest_ok or partner_env

    storefront_ok = False
    storefront_detail = ""
    store_url = ""
    if token:
        store_url = fetch_zid_manager_store_url(token) or ""
        if store_url:
            found, detail = probe_storefront_for_widget_loader(
                store_url,
                loader_url=loader_url,
            )
            storefront_ok = found
            storefront_detail = detail
            try:
                from services.store_identity_v1 import sync_zid_store_identities_after_oauth

                sync_zid_store_identities_after_oauth(store, store_url=store_url)
            except Exception:  # noqa: BLE001
                pass

    now = _utc_now()

    if not partner_path_available:
        store.widget_installation_status = _STATUS_UNSUPPORTED
        store.widget_install_error = (
            manifest_detail or "zid_no_per_store_widget_install_api"
        )[:500]
        store.widget_installed_at = None
        db.session.commit()
        _emit(
            "ZID WIDGET INSTALL FAILED",
            store_id=str(store_id or "-"),
            reason="unsupported",
            detail=store.widget_install_error or "-",
        )
        return {
            "ok": False,
            "status": _STATUS_UNSUPPORTED,
            "manifest_ok": manifest_ok,
            "storefront_ok": storefront_ok,
        }

    if storefront_ok:
        store.widget_installation_status = _STATUS_INSTALLED
        store.widget_installed_at = now
        store.widget_last_seen_at = store.widget_last_seen_at or now
        store.widget_install_error = None
        db.session.commit()
        _emit(
            "ZID WIDGET INSTALL SUCCESS",
            store_id=str(store_id or "-"),
            zid_store_id=zid_slug[:64] or "-",
            method="storefront_probe",
        )
        return {
            "ok": True,
            "status": _STATUS_INSTALLED,
            "manifest_ok": manifest_ok,
            "storefront_ok": True,
        }

    next_status = _STATUS_INSTALLING if manifest_ok else _STATUS_PENDING
    store.widget_installation_status = next_status
    store.widget_installed_at = now
    store.widget_install_error = None
    db.session.commit()
    _emit(
        "ZID WIDGET INSTALL SUCCESS",
        store_id=str(store_id or "-"),
        zid_store_id=zid_slug[:64] or "-",
        method="partner_snippet_await_storefront",
        status=next_status,
        storefront_detail=storefront_detail[:120] or "-",
    )
    return {
        "ok": True,
        "status": next_status,
        "manifest_ok": manifest_ok,
        "storefront_ok": False,
        "store_url": store_url[:200] if store_url else None,
    }


__all__ = [
    "build_widget_install_api_fields",
    "maybe_install_zid_storefront_widget",
    "record_widget_storefront_seen",
    "widget_installation_description_ar",
    "widget_installation_status_label_ar",
]
