# -*- coding: utf-8 -*-
"""
Storefront runtime truth verification gate — DB vs public-config vs storefront beacon.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import Store, StoreIdentityAlias

_log = logging.getLogger("cartflow.storefront_runtime_truth")

TRUTH_STATUS_VERIFIED = "verified"
TRUTH_STATUS_PENDING = "pending"
TRUTH_STATUS_MISMATCH = "mismatch"
TRUTH_STATUS_UNRESOLVED = "unresolved"

MSG_VERIFIED_AR = "الإعدادات مفعّلة في المتجر"
MSG_PENDING_AR = "تم حفظ الإعدادات — نتحقق من ظهورها في المتجر"
MSG_MISMATCH_AR = "تم الحفظ، لكن لم تظهر الإعدادات في المتجر بعد"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _norm_color(raw: Any) -> str:
    return _norm_color_dom(raw)


def _norm_name(raw: Any) -> str:
    return str(raw or "").strip()


_RGB_RE = re.compile(
    r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})",
    re.IGNORECASE,
)


def _norm_color_dom(raw: Any) -> str:
    """Normalize hex or computed ``rgb()`` / ``rgba()`` for DOM vs DB comparison."""
    s = str(raw or "").strip()
    if not s:
        return ""
    if s.casefold().startswith("rgb"):
        m = _RGB_RE.match(s)
        if m:
            parts = [max(0, min(255, int(m.group(i)))) for i in range(1, 4)]
            return "#{:02x}{:02x}{:02x}".format(*parts).casefold()
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            return f"#{h}".casefold()
    bare = s.lstrip("#")
    if len(bare) == 6 and re.fullmatch(r"[0-9a-f]{6}", bare, re.IGNORECASE):
        return f"#{bare}".casefold()
    return s.casefold()


def beacon_dom_truth_fields(beacon: Optional[dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
    """
    Visible storefront DOM values from the latest beacon only.
    Ignores intended/config fields (``widget_name``, ``widget_color``).
    """
    if not beacon:
        return None, None
    title = beacon.get("rendered_title_text")
    if title is None:
        title = beacon.get("rendered_widget_title")
    color = beacon.get("rendered_primary_color_computed")
    if color is None:
        color = beacon.get("rendered_widget_color")
    title_s = _norm_name(title) if title is not None and str(title).strip() else None
    color_s = _norm_color_dom(color) if color is not None and str(color).strip() else None
    return title_s or None, color_s or None


def merchant_message_for_status(status: str) -> str:
    if status == TRUTH_STATUS_VERIFIED:
        return MSG_VERIFIED_AR
    if status == TRUTH_STATUS_MISMATCH:
        return MSG_MISMATCH_AR
    return MSG_PENDING_AR


def parse_beacon_on_row(row: Any) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    raw = getattr(row, "widget_last_beacon_json", None)
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def primary_storefront_slug_for_store(row: Any) -> Optional[str]:
    """Prefer ``zid_permalink`` alias; else first platform permalink-like alias."""
    if row is None:
        return None
    sid = getattr(row, "id", None)
    if sid is None:
        return None
    from services.store_identity_v1 import (
        ALIAS_KIND_ZID_PERMALINK,
        canonical_store_slug_on_row,
        list_public_cache_keys_for_store_row,
        looks_like_zid_storefront_permalink,
        normalize_identity_value,
    )

    try:
        permalink_rows = (
            db.session.query(StoreIdentityAlias)
            .filter(StoreIdentityAlias.store_id == int(sid))
            .filter(StoreIdentityAlias.alias_kind == ALIAS_KIND_ZID_PERMALINK)
            .all()
        )
        for ar in permalink_rows:
            val = normalize_identity_value(getattr(ar, "alias_value", None))
            if val and looks_like_zid_storefront_permalink(val):
                return val
    except (SQLAlchemyError, OSError):
        db.session.rollback()

    canon = canonical_store_slug_on_row(row) or ""
    for key in list_public_cache_keys_for_store_row(row):
        kk = normalize_identity_value(key)
        if not kk or kk == canon:
            continue
        if looks_like_zid_storefront_permalink(kk):
            return kk
    return None


def _triple_match(
    *,
    db_val: Any,
    pub_val: Any,
    beacon_val: Any,
    normalizer=_norm_name,
) -> Tuple[bool, Optional[str]]:
    db_n = normalizer(db_val)
    pub_n = normalizer(pub_val)
    beacon_n = normalizer(beacon_val)
    if not beacon_n:
        return False, "beacon_missing"
    if db_n != pub_n:
        return False, "db_public_config_mismatch"
    if db_n != beacon_n or pub_n != beacon_n:
        return False, "storefront_beacon_mismatch"
    return True, None


def evaluate_storefront_runtime_truth(
    store_row: Any,
    *,
    storefront_slug: Optional[str] = None,
    trigger: str = "evaluate",
) -> Dict[str, Any]:
    """Compare dashboard DB vs public-config vs last storefront beacon."""
    from services.store_identity_runtime_truth_v1 import (
        build_store_identity_runtime_truth_report,
    )
    from services.store_widget_customization import widget_customization_fields_for_api

    if store_row is None:
        return {
            "ok": False,
            "status": TRUTH_STATUS_UNRESOLVED,
            "verified": False,
            "message_ar": MSG_MISMATCH_AR,
            "mismatch_reason": "no_store_row",
        }

    sf = (storefront_slug or primary_storefront_slug_for_store(store_row) or "").strip()
    dash_custom = widget_customization_fields_for_api(store_row)
    db_name = dash_custom.get("widget_name")
    db_color = dash_custom.get("widget_primary_color")

    identity_report: dict[str, Any] = {}
    if sf:
        identity_report = build_store_identity_runtime_truth_report(
            storefront_slug=sf,
            dashboard_store_row=store_row,
        )
    else:
        identity_report = {
            "passed": False,
            "checks": {"storefront_resolved": False},
            "storefront_slug": None,
            "resolved_store_id": None,
            "resolved_via": "no_storefront_slug",
        }

    beacon = parse_beacon_on_row(store_row) or {}
    beacon_dom_name, beacon_dom_color = beacon_dom_truth_fields(beacon)
    beacon_intended_name = beacon.get("widget_name") or beacon.get("rendered_widget_name")
    beacon_intended_color = beacon.get("widget_color") or beacon.get("rendered_widget_color")
    beacon_slug = (
        beacon.get("store_slug")
        or beacon.get("store")
        or getattr(store_row, "widget_last_runtime_slug", None)
    )

    pub_name = identity_report.get("public_config_widget_name")
    pub_color = identity_report.get("public_config_color")

    name_ok, name_reason = _triple_match(
        db_val=db_name, pub_val=pub_name, beacon_val=beacon_dom_name
    )
    color_ok, color_reason = _triple_match(
        db_val=db_color,
        pub_val=pub_color,
        beacon_val=beacon_dom_color,
        normalizer=_norm_color_dom,
    )
    dom_name_ok = bool(beacon_dom_name) and _norm_name(db_name) == beacon_dom_name
    dom_color_ok = bool(beacon_dom_color) and _norm_color_dom(db_color) == beacon_dom_color

    checks = dict(identity_report.get("checks") or {})
    checks["db_public_config_name"] = identity_report.get("checks", {}).get(
        "widget_name_match", db_name == pub_name
    )
    checks["db_public_config_color"] = identity_report.get("checks", {}).get(
        "widget_color_match", _norm_color(db_color) == _norm_color(pub_color)
    )
    checks["beacon_name_match"] = name_ok
    checks["beacon_color_match"] = color_ok
    checks["beacon_dom_name_match"] = dom_name_ok
    checks["beacon_dom_color_match"] = dom_color_ok
    checks["beacon_dom_present"] = bool(beacon_dom_name and beacon_dom_color)

    mismatch_reasons: List[str] = []
    if not checks.get("storefront_resolved"):
        mismatch_reasons.append("storefront_unresolved")
    if not identity_report.get("alias_match"):
        mismatch_reasons.append("alias_mismatch")
    if not checks.get("db_public_config_name"):
        mismatch_reasons.append(name_reason or "widget_name_mismatch")
    if not checks.get("db_public_config_color"):
        mismatch_reasons.append(color_reason or "widget_color_mismatch")
    if not beacon_dom_name:
        mismatch_reasons.append("beacon_dom_title_missing")
    if not beacon_dom_color:
        mismatch_reasons.append("beacon_dom_color_missing")
    if not name_ok:
        mismatch_reasons.append(name_reason or "beacon_dom_name_mismatch")
    if not color_ok:
        mismatch_reasons.append(color_reason or "beacon_dom_color_mismatch")
    if not dom_name_ok and beacon_dom_name:
        mismatch_reasons.append("dashboard_dom_title_mismatch")
    if not dom_color_ok and beacon_dom_color:
        mismatch_reasons.append("dashboard_dom_color_mismatch")
    if beacon_slug and sf and _norm_name(beacon_slug) != _norm_name(sf):
        mismatch_reasons.append("beacon_slug_mismatch")

    if not sf or not checks.get("storefront_resolved"):
        status = TRUTH_STATUS_UNRESOLVED
    elif (
        dom_name_ok
        and dom_color_ok
        and name_ok
        and color_ok
        and identity_report.get("passed")
    ):
        status = TRUTH_STATUS_VERIFIED
    elif not beacon_dom_name and identity_report.get("passed"):
        status = TRUTH_STATUS_PENDING
    else:
        status = TRUTH_STATUS_MISMATCH

    verified = status == TRUTH_STATUS_VERIFIED
    mismatch_reason = ";".join(dict.fromkeys(m for m in mismatch_reasons if m))

    last_seen = getattr(store_row, "widget_last_seen_at", None)
    last_seen_s = None
    if isinstance(last_seen, datetime):
        last_seen_s = last_seen.astimezone(timezone.utc).isoformat()

    gate = {
        "ok": True,
        "trigger": trigger,
        "status": status,
        "verified": verified,
        "message_ar": merchant_message_for_status(status),
        "mismatch_reason": mismatch_reason or None,
        "dashboard_store_id": getattr(store_row, "id", None),
        "dashboard_slug": identity_report.get("dashboard_slug"),
        "storefront_slug": sf or None,
        "resolved_store_id": identity_report.get("resolved_store_id"),
        "resolved_via": identity_report.get("resolved_via"),
        "aliases": identity_report.get("aliases") or [],
        "dashboard_widget_name": db_name,
        "dashboard_widget_color": db_color,
        "public_config_widget_name": pub_name,
        "public_config_color": pub_color,
        "beacon_rendered_title_text": beacon_dom_name,
        "beacon_rendered_primary_color_computed": beacon_dom_color,
        "beacon_intended_widget_name": beacon_intended_name,
        "beacon_intended_widget_color": beacon_intended_color,
        "beacon_widget_name": beacon_dom_name,
        "beacon_widget_color": beacon_dom_color,
        "beacon_store_slug": beacon_slug,
        "beacon_runtime_version": beacon.get("runtime_version"),
        "beacon_page_url": beacon.get("page_url"),
        "beacon_timestamp": beacon.get("timestamp"),
        "widget_last_seen_at": last_seen_s,
        "checks": checks,
        "identity_report": {
            k: identity_report.get(k)
            for k in (
                "passed",
                "cache_keys",
                "cache_hits",
                "zid_identity",
            )
        },
        "warnings": [] if verified else [mismatch_reason or status],
    }
    return gate


def persist_truth_gate_on_store(store_row: Any, gate: Dict[str, Any]) -> None:
    from schema_storefront_runtime_truth import ensure_storefront_runtime_truth_schema

    ensure_storefront_runtime_truth_schema(db)
    if store_row is None or not gate:
        return
    try:
        store_row.widget_runtime_truth_status = str(gate.get("status") or "")[:32] or None
        store_row.widget_runtime_truth_at = _utc_now()
        store_row.widget_runtime_truth_json = json.dumps(gate, ensure_ascii=False)[:8000]
        db.session.commit()
    except (SQLAlchemyError, OSError):
        db.session.rollback()


def log_operational_truth_alert(gate: Dict[str, Any]) -> None:
    status = str(gate.get("status") or "")
    if status not in (TRUTH_STATUS_MISMATCH, TRUTH_STATUS_UNRESOLVED):
        return
    try:
        print("[STOREFRONT RUNTIME TRUTH ALERT]", flush=True)
        print(f"status={status}", flush=True)
        print(f"store_id={gate.get('dashboard_store_id')}", flush=True)
        print(f"dashboard_slug={(gate.get('dashboard_slug') or '-')[:128]}", flush=True)
        print(f"storefront_slug={(gate.get('storefront_slug') or '-')[:128]}", flush=True)
        print(f"mismatch_reason={(gate.get('mismatch_reason') or '-')[:256]}", flush=True)
    except OSError:
        pass


def run_post_save_storefront_truth_gate(
    store_row: Any,
    *,
    trigger: str = "dashboard_save",
) -> Dict[str, Any]:
    """After widget settings save: sync aliases, warm cache, verify public-config."""
    if store_row is None:
        return {
            "ok": False,
            "status": TRUTH_STATUS_UNRESOLVED,
            "verified": False,
            "message_ar": MSG_MISMATCH_AR,
        }

    from services.store_identity_v1 import (
        ensure_zid_permalink_alias_for_dashboard_store,
        sync_zid_identities_for_dashboard_store,
    )
    from services.widget_config_cache import update_from_dashboard_store_row

    try:
        sync_zid_identities_for_dashboard_store(store_row)
        update_from_dashboard_store_row(store_row)
        db.session.expire(store_row)
    except Exception as exc:  # noqa: BLE001
        _log.warning("post-save truth gate sync skipped: %s", exc)
        db.session.rollback()

    sf = primary_storefront_slug_for_store(store_row)
    if sf:
        ensure_zid_permalink_alias_for_dashboard_store(store_row, sf)

    gate = evaluate_storefront_runtime_truth(
        store_row,
        storefront_slug=sf,
        trigger=trigger,
    )
    persist_truth_gate_on_store(store_row, gate)
    log_operational_truth_alert(gate)
    return gate


def attach_truth_gate_to_merchant_response(
    payload: Dict[str, Any],
    gate: Dict[str, Any],
) -> Dict[str, Any]:
    out = dict(payload)
    out["storefront_runtime_truth"] = {
        "verified": bool(gate.get("verified")),
        "status": gate.get("status"),
        "message_ar": gate.get("message_ar"),
        "mismatch_reason": gate.get("mismatch_reason"),
        "storefront_slug": gate.get("storefront_slug"),
        "warnings": gate.get("warnings") or [],
    }
    if not gate.get("verified"):
        out["storefront_runtime_truth_warning"] = gate.get("mismatch_reason") or gate.get(
            "status"
        )
    return out


def record_storefront_runtime_beacon(payload: dict[str, Any]) -> Tuple[bool, Optional[int]]:
    """
    Persist storefront beacon + re-evaluate truth gate for resolved Store row.
    Returns (updated, store_id).
    """
    from schema_storefront_runtime_truth import ensure_storefront_runtime_truth_schema
    from services.store_identity_v1 import (
        is_widget_sandbox_slug,
        resolve_store_row_for_storefront_api,
    )
    from services.zid_storefront_widget_install_v1 import record_widget_storefront_seen

    ensure_storefront_runtime_truth_schema(db)

    slug = (
        str(
            payload.get("store_slug")
            or payload.get("store")
            or payload.get("runtime_store_slug")
            or ""
        )
        .strip()[:255]
    )
    if not slug:
        return False, None

    if is_widget_sandbox_slug(slug):
        try:
            page_url = str(payload.get("page_url") or "")
            if ".zid.store" in page_url.lower() or ".salla." in page_url.lower():
                print(
                    f"[STOREFRONT RUNTIME TRUTH ALERT] demo_slug_on_platform_store "
                    f"slug={slug[:64]} page={(page_url or '-')[:128]}",
                    flush=True,
                )
        except OSError:
            pass
        return False, None

    record_widget_storefront_seen(store_slug=slug)

    row, _via = resolve_store_row_for_storefront_api(slug)
    if row is None:
        try:
            print(
                f"[STOREFRONT RUNTIME TRUTH ALERT] storefront_unresolved "
                f"slug={slug[:64]} via={_via}",
                flush=True,
            )
        except OSError:
            pass
        return False, None

    rendered_title = (
        payload.get("rendered_title_text")
        or payload.get("rendered_widget_title")
    )
    rendered_color = (
        payload.get("rendered_primary_color_computed")
        or payload.get("rendered_widget_color")
    )
    beacon_doc = {
        "store_slug": slug,
        "store": slug,
        "rendered_title_text": rendered_title,
        "rendered_primary_color_computed": rendered_color,
        "runtime_truth": payload.get("runtime_truth"),
        "runtime_version": payload.get("runtime_version"),
        "page_url": payload.get("page_url"),
        "timestamp": payload.get("timestamp") or _utc_now().isoformat(),
        "beacon_tag": payload.get("beacon_tag"),
    }
    row.widget_last_runtime_slug = slug[:255]
    row.widget_last_beacon_json = json.dumps(beacon_doc, ensure_ascii=False)[:8000]

    gate = evaluate_storefront_runtime_truth(
        row,
        storefront_slug=slug,
        trigger="storefront_beacon",
    )
    persist_truth_gate_on_store(row, gate)
    log_operational_truth_alert(gate)

    try:
        db.session.commit()
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return False, None

    return True, int(getattr(row, "id", 0) or 0)


def build_admin_widget_settings_mismatch_alerts(
    *,
    stores: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Admin Operations alerts for widget settings / identity mismatches."""
    from services.admin_operations_center_v1 import _alert_with_records

    alerts: list[dict[str, Any]] = []
    for st in stores:
        truth_status = str(st.get("widget_runtime_truth_status") or "").strip().lower()
        if truth_status not in (TRUTH_STATUS_MISMATCH, TRUTH_STATUS_UNRESOLVED):
            continue
        slug = st.get("store_slug") or ""
        name = st.get("display_name") or slug or "متجر"
        gate_raw = st.get("widget_runtime_truth_json")
        gate: dict[str, Any] = {}
        if isinstance(gate_raw, dict):
            gate = gate_raw
        elif isinstance(gate_raw, str) and gate_raw.strip():
            try:
                parsed = json.loads(gate_raw)
                if isinstance(parsed, dict):
                    gate = parsed
            except json.JSONDecodeError:
                gate = {}

        detail = (
            f"{name} — عدم تطابق إعدادات الودجيت بين اللوحة والمتجر."
            if truth_status == TRUTH_STATUS_MISMATCH
            else f"{name} — لم يُحل slug المتجر (storefront) بعد."
        )
        record = {
            "store_id": st.get("store_id"),
            "store_slug": slug,
            "storefront_slug": gate.get("storefront_slug") or st.get("widget_last_runtime_slug"),
            "resolved_store_id": gate.get("resolved_store_id"),
            "dashboard_widget_name": gate.get("dashboard_widget_name"),
            "dashboard_widget_color": gate.get("dashboard_widget_color"),
            "public_config_widget_name": gate.get("public_config_widget_name"),
            "public_config_color": gate.get("public_config_color"),
            "beacon_widget_name": gate.get("beacon_widget_name"),
            "beacon_widget_color": gate.get("beacon_widget_color"),
            "widget_last_seen_at": st.get("widget_last_seen_at"),
            "last_runtime_slug": st.get("widget_last_runtime_slug"),
            "mismatch_reason": gate.get("mismatch_reason") or truth_status,
            "aliases": gate.get("aliases") or [],
        }
        alerts.append(
            _alert_with_records(
                kind="widget_settings_mismatch",
                title_ar="Store Identity / Widget Settings Mismatch",
                detail_ar=detail,
                records=[record],
                records_total=1,
            )
        )
    return alerts


def merge_dom_truth_into_identity_report(
    report: Dict[str, Any],
    *,
    dashboard_store_row: Any,
    storefront_slug: str,
) -> Dict[str, Any]:
    """Override ``passed`` unless latest beacon confirms visible DOM matches dashboard."""
    gate = evaluate_storefront_runtime_truth(
        dashboard_store_row,
        storefront_slug=storefront_slug,
        trigger="identity_runtime_truth",
    )
    out = dict(report)
    out["storefront_dom_truth"] = gate
    checks = dict(out.get("checks") or {})
    checks["storefront_dom_verified"] = bool(gate.get("verified"))
    checks["beacon_dom_present"] = (gate.get("checks") or {}).get("beacon_dom_present")
    out["checks"] = checks
    out["passed"] = bool(
        checks.get("storefront_resolved")
        and checks.get("alias_match")
        and checks.get("widget_name_match")
        and checks.get("widget_color_match")
        and gate.get("verified")
    )
    return out


__all__ = [
    "beacon_dom_truth_fields",
    "merge_dom_truth_into_identity_report",
    "MSG_MISMATCH_AR",
    "MSG_PENDING_AR",
    "MSG_VERIFIED_AR",
    "TRUTH_STATUS_MISMATCH",
    "TRUTH_STATUS_PENDING",
    "TRUTH_STATUS_UNRESOLVED",
    "TRUTH_STATUS_VERIFIED",
    "attach_truth_gate_to_merchant_response",
    "build_admin_widget_settings_mismatch_alerts",
    "evaluate_storefront_runtime_truth",
    "merchant_message_for_status",
    "persist_truth_gate_on_store",
    "primary_storefront_slug_for_store",
    "record_storefront_runtime_beacon",
    "run_post_save_storefront_truth_gate",
]
