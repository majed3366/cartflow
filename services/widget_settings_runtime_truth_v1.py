# -*- coding: utf-8 -*-
"""
Widget settings runtime truth — dashboard vs public-config vs storefront runtime beacon.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from extensions import db
from models import Store
from services.cartflow_widget_recovery_gate import cartflow_widget_recovery_gate_fields_for_api
from services.cartflow_widget_trigger_settings import widget_trigger_config_for_api
from services.storefront_runtime_truth_gate_v1 import parse_beacon_on_row
from services.store_identity_runtime_truth_v1 import _public_config_fields_for_slug
from services.store_identity_v1 import resolve_store_row_for_storefront_api
from services.widget_config_cache import (
    build_snapshot_from_store_row,
    get_snapshot,
    normalize_store_slug,
)


def _delay_ms(value: Any, unit: Any) -> int:
    try:
        v = max(0, int(value))
    except (TypeError, ValueError):
        v = 0
    u = str(unit or "minutes").strip().lower()
    if u == "hours":
        return v * 3_600_000
    if u == "days":
        return v * 86_400_000
    return v * 60_000


def _norm_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and v in (0, 1):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "1", "yes", "on"):
            return True
        if s in ("false", "0", "no", "off"):
            return False
    return None


def _norm_frequency(v: Any) -> str:
    s = str(v or "per_session").strip().lower().replace(" ", "_")
    if s in ("per_session", "per_24h", "no_rapid_repeat"):
        return s
    return "per_session"


def dashboard_widget_settings(store_row: Any) -> Dict[str, Any]:
    gate = cartflow_widget_recovery_gate_fields_for_api(store_row)
    trig_wrap = widget_trigger_config_for_api(store_row)
    trig = (
        trig_wrap.get("widget_trigger_config")
        if isinstance(trig_wrap, dict)
        else {}
    )
    if not isinstance(trig, dict):
        trig = {}
    delay_v = gate.get("cartflow_widget_delay_value", 0)
    delay_u = gate.get("cartflow_widget_delay_unit", "minutes")
    return {
        "enabled": bool(gate.get("cartflow_widget_enabled", True)),
        "exit_intent": bool(trig.get("exit_intent_enabled", True)),
        "hesitation": bool(trig.get("hesitation_trigger_enabled", True)),
        "delay_value": delay_v,
        "delay_unit": delay_u,
        "delay_ms": _delay_ms(delay_v, delay_u),
        "frequency": _norm_frequency(trig.get("exit_intent_frequency")),
        "hesitation_after_seconds": trig.get("hesitation_after_seconds"),
    }


def public_config_widget_settings(
    storefront_slug: str,
    store_row: Any = None,
) -> Dict[str, Any]:
    slug = normalize_store_slug(storefront_slug)
    snap = get_snapshot(slug) if slug else None
    if snap is None and store_row is not None:
        snap = build_snapshot_from_store_row(store_row)
    tpl = snap.get("template_bundle") if isinstance(snap, dict) else {}
    if not isinstance(tpl, dict):
        tpl = {}
    trig = tpl.get("widget_trigger_config")
    if not isinstance(trig, dict):
        trig = {}
    delay_v = tpl.get("cartflow_widget_delay_value", 0)
    delay_u = tpl.get("cartflow_widget_delay_unit", "minutes")
    return {
        "enabled": bool(tpl.get("cartflow_widget_enabled", True)),
        "exit_intent": bool(trig.get("exit_intent_enabled", True)),
        "hesitation": bool(trig.get("hesitation_trigger_enabled", True)),
        "delay_value": delay_v,
        "delay_unit": delay_u,
        "delay_ms": _delay_ms(delay_v, delay_u),
        "frequency": _norm_frequency(trig.get("exit_intent_frequency")),
        "hesitation_after_seconds": trig.get("hesitation_after_seconds"),
    }


def _parse_runtime_truth_raw(beacon: Optional[dict[str, Any]]) -> Dict[str, Any]:
    if not beacon:
        return {}
    rt = beacon.get("runtime_truth")
    if isinstance(rt, str) and rt.strip():
        try:
            parsed = json.loads(rt)
            if isinstance(parsed, dict):
                rt = parsed
        except (TypeError, ValueError, json.JSONDecodeError):
            rt = {}
    if not isinstance(rt, dict):
        rt = {}
    return rt


def runtime_truth_beacon_present(beacon: Optional[dict[str, Any]]) -> bool:
    """True when storefront posted a config/runtime truth snapshot (not DOM-only)."""
    rt = _parse_runtime_truth_raw(beacon)
    if not rt:
        return False
    if _norm_bool(rt.get("config_loaded")) is True:
        return True
    return _norm_bool(rt.get("widget_enabled")) is not None


def _disabled_runtime_beacon_ok(runtime: Dict[str, Any]) -> bool:
    disabled_eff = bool(
        runtime.get("disabled_effective") or runtime.get("widget_disabled_effective")
    )
    return (
        runtime.get("enabled") is False
        and runtime.get("config_loaded") is True
        and runtime.get("widget_rendered") is False
        and disabled_eff
    )


def runtime_widget_settings_from_beacon(beacon: Optional[dict[str, Any]]) -> Dict[str, Any]:
    if not beacon:
        return {}
    rt = _parse_runtime_truth_raw(beacon)
    if not rt:
        return {}
    out: Dict[str, Any] = {}
    en = _norm_bool(rt.get("widget_enabled"))
    if en is not None:
        out["enabled"] = en
    ex = _norm_bool(rt.get("exit_intent_enabled"))
    if ex is not None:
        out["exit_intent"] = ex
    hes = _norm_bool(rt.get("hesitation_trigger_enabled"))
    if hes is not None:
        out["hesitation"] = hes
    if "exit_intent_frequency" in rt:
        out["frequency"] = _norm_frequency(rt.get("exit_intent_frequency"))
    if "hesitation_after_seconds" in rt:
        try:
            out["hesitation_after_seconds"] = int(rt.get("hesitation_after_seconds"))
        except (TypeError, ValueError):
            pass
    if "delay_configured_ms" in rt:
        try:
            out["delay_ms"] = max(0, int(rt.get("delay_configured_ms")))
        except (TypeError, ValueError):
            pass
    if "delay_configured_value" in rt:
        try:
            out["delay_value"] = int(rt.get("delay_configured_value"))
        except (TypeError, ValueError):
            pass
    if "delay_configured_unit" in rt:
        out["delay_unit"] = str(rt.get("delay_configured_unit") or "minutes")
    if "delay_remaining_ms" in rt:
        try:
            out["delay_remaining_ms"] = max(0, int(rt.get("delay_remaining_ms")))
        except (TypeError, ValueError):
            pass
    if "prompt_not_before_ms" in rt:
        out["prompt_not_before_ms"] = rt.get("prompt_not_before_ms")
    if "widget_disabled_effective" in rt:
        out["widget_disabled_effective"] = bool(rt.get("widget_disabled_effective"))
    if "disabled_effective" in rt:
        out["disabled_effective"] = bool(rt.get("disabled_effective"))
    elif "widget_disabled_effective" in rt:
        out["disabled_effective"] = bool(rt.get("widget_disabled_effective"))
    if "widget_globally_allowed" in rt:
        out["widget_globally_allowed"] = bool(rt.get("widget_globally_allowed"))
    cfg = _norm_bool(rt.get("config_loaded"))
    if cfg is not None:
        out["config_loaded"] = cfg
    rendered = _norm_bool(rt.get("widget_rendered"))
    if rendered is not None:
        out["widget_rendered"] = rendered
    return out


def _settings_equal(
    a: Dict[str, Any],
    b: Dict[str, Any],
    *,
    keys: Tuple[str, ...],
) -> bool:
    for k in keys:
        if k not in a or k not in b:
            return False
        av, bv = a.get(k), b.get(k)
        if k == "frequency":
            if _norm_frequency(av) != _norm_frequency(bv):
                return False
            continue
        if isinstance(av, bool) or isinstance(bv, bool):
            if bool(av) != bool(bv):
                return False
            continue
        if av != bv:
            return False
    return True


def _compare_settings(
    left: Dict[str, Any],
    right: Dict[str, Any],
    *,
    label_left: str,
    label_right: str,
) -> Tuple[bool, List[dict[str, Any]]]:
    keys = (
        "enabled",
        "exit_intent",
        "hesitation",
        "delay_value",
        "delay_unit",
        "frequency",
        "hesitation_after_seconds",
    )
    mismatches: List[dict[str, Any]] = []
    for k in keys:
        if k not in left and k not in right:
            continue
        lv, rv = left.get(k), right.get(k)
        if k == "frequency":
            ok = _norm_frequency(lv) == _norm_frequency(rv)
        elif k in ("enabled", "exit_intent", "hesitation"):
            ok = bool(lv) == bool(rv)
        else:
            ok = lv == rv
        if not ok:
            mismatches.append(
                {
                    "setting": k,
                    "expected_source": label_left,
                    "expected": lv,
                    "actual_source": label_right,
                    "actual": rv,
                }
            )
    return len(mismatches) == 0, mismatches


def _empty_cart_bridge_state() -> Dict[str, Any]:
    return {
        "last_event_type": None,
        "last_event_source_platform": None,
        "last_detected_by": None,
        "last_items_count": None,
        "last_cart_total": None,
        "last_event_at": None,
        "hesitation_armed_from_cart_event": False,
    }


def cart_bridge_state_from_beacon(beacon: Optional[dict[str, Any]]) -> Dict[str, Any]:
    """Read the normalized cart-bridge snapshot carried in the runtime-truth beacon."""
    rt = _parse_runtime_truth_raw(beacon)
    cb = rt.get("cart_bridge") if isinstance(rt, dict) else None
    if not isinstance(cb, dict):
        return _empty_cart_bridge_state()
    return {
        "last_event_type": cb.get("last_event_type"),
        "last_event_source_platform": cb.get("last_event_source_platform"),
        "last_detected_by": cb.get("last_detected_by"),
        "last_items_count": cb.get("last_items_count"),
        "last_cart_total": cb.get("last_cart_total"),
        "last_event_at": cb.get("last_event_at"),
        "hesitation_armed_from_cart_event": bool(
            cb.get("hesitation_armed_from_cart_event")
        ),
    }


def evaluate_widget_settings_runtime_truth(
    store_row: Any,
    *,
    storefront_slug: Optional[str] = None,
) -> Dict[str, Any]:
    from services.storefront_runtime_truth_gate_v1 import primary_storefront_slug_for_store

    sf = (storefront_slug or primary_storefront_slug_for_store(store_row) or "").strip()
    dash = dashboard_widget_settings(store_row) if store_row is not None else {}
    pub: Dict[str, Any] = {}
    if sf:
        resolved, _via = resolve_store_row_for_storefront_api(sf)
        pub = public_config_widget_settings(sf, resolved or store_row)
    beacon = parse_beacon_on_row(store_row) or {}
    runtime = runtime_widget_settings_from_beacon(beacon)

    compare_keys = (
        "enabled",
        "exit_intent",
        "hesitation",
        "delay_value",
        "delay_unit",
        "frequency",
    )
    dash_pub_ok, dash_pub_mm = _compare_settings(dash, pub, label_left="dashboard", label_right="public_config")
    dash_rt_ok, dash_rt_mm = _compare_settings(
        dash,
        runtime,
        label_left="dashboard",
        label_right="runtime",
    ) if runtime else (False, [{"setting": "runtime_truth", "expected_source": "beacon", "actual_source": "missing"}])
    pub_rt_ok, pub_rt_mm = _compare_settings(
        pub,
        runtime,
        label_left="public_config",
        label_right="runtime",
    ) if runtime else (False, [])

    runtime_present = runtime_truth_beacon_present(beacon)
    config_match = dash_pub_ok
    if not sf:
        status = "unresolved"
        passed = False
    elif not runtime_present:
        status = "pending"
        passed = False
    elif dash_pub_ok and dash_rt_ok and pub_rt_ok:
        if dash.get("enabled") is False and not _disabled_runtime_beacon_ok(runtime):
            status = "mismatch"
            passed = False
        else:
            status = "verified"
            passed = True
    else:
        status = "mismatch"
        passed = False

    mismatches = dash_pub_mm + dash_rt_mm + pub_rt_mm

    identity_pub = _public_config_fields_for_slug(sf, store_row) if sf else {}

    return {
        "ok": True,
        "store_slug": sf or None,
        "passed": passed,
        "status": status,
        "config_match": config_match,
        "partial_pass": config_match,
        "dashboard": dash,
        "public_config": pub,
        "runtime": runtime if runtime_present else None,
        "checks": {
            "dashboard_public_config": dash_pub_ok,
            "config_match": config_match,
            "dashboard_runtime": dash_rt_ok if runtime_present else None,
            "public_config_runtime": pub_rt_ok if runtime_present else None,
            "runtime_beacon_present": runtime_present,
            "disabled_runtime_ok": _disabled_runtime_beacon_ok(runtime)
            if runtime_present and dash.get("enabled") is False
            else None,
            "identity_enabled_match": identity_pub.get("public_config_widget_enabled")
            == dash.get("enabled")
            if dash
            else None,
        },
        "mismatches": mismatches,
        "cart_bridge": cart_bridge_state_from_beacon(beacon),
        "beacon_runtime_version": beacon.get("runtime_version"),
        "beacon_timestamp": beacon.get("timestamp"),
    }


def build_admin_widget_runtime_mismatch_alerts(
    *,
    stores: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Admin Operations: widget_runtime_mismatch when settings ≠ runtime beacon."""
    from services.admin_operations_center_v1 import _alert_with_records

    alerts: list[dict[str, Any]] = []
    for st in stores:
        store_id = st.get("store_id")
        if not store_id:
            continue
        try:
            row = db.session.get(Store, int(store_id))
        except Exception:  # noqa: BLE001
            db.session.rollback()
            row = None
        if row is None:
            continue
        sf = (
            st.get("widget_last_runtime_slug")
            or st.get("store_slug")
            or getattr(row, "zid_store_id", None)
            or ""
        )
        report = evaluate_widget_settings_runtime_truth(row, storefront_slug=str(sf).strip())
        if report.get("status") != "mismatch":
            continue
        name = st.get("display_name") or sf or "متجر"
        records: List[dict[str, Any]] = []
        for mm in report.get("mismatches") or []:
            records.append(
                {
                    "store_id": store_id,
                    "store_slug": st.get("store_slug"),
                    "storefront_slug": report.get("store_slug"),
                    "setting": mm.get("setting"),
                    "expected": mm.get("expected"),
                    "actual": mm.get("actual"),
                    "expected_source": mm.get("expected_source"),
                    "actual_source": mm.get("actual_source"),
                    "suggested_fix_ar": (
                        f"راجع إعداد «{mm.get('setting')}» في اللوحة ({mm.get('expected')}) "
                        f"وتأكد من ظهوره في المتجر ({mm.get('actual')})."
                    ),
                }
            )
        if not records:
            continue
        alerts.append(
            _alert_with_records(
                kind="widget_runtime_mismatch",
                title_ar="Widget runtime settings mismatch",
                detail_ar=f"{name} — إعدادات الودجيت في اللوحة لا تطابق سلوك المتجر الفعلي.",
                records=records[:12],
                records_total=len(records),
            )
        )
    return alerts


def _beacon_dict_from_store(store: dict[str, Any]) -> Optional[dict[str, Any]]:
    raw = store.get("widget_last_beacon_json")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    return None


def _platform_from_page_url(page_url: str) -> str:
    u = str(page_url or "").lower()
    if ".zid.store" in u:
        return "zid"
    if ".salla." in u or "salla.sa" in u:
        return "salla"
    if ".myshopify.com" in u or "shopify" in u:
        return "shopify"
    return "generic"


_CART_PAGE_RE = re.compile(r"/(cart|checkout|basket)(?:[/?#]|$)", re.IGNORECASE)


def build_cart_event_bridge_missing_alerts(
    *,
    stores: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Future-facing, read-only admin alert: the widget is installed and
    public-config loaded, the merchant is on a cart/checkout page, yet no
    normalized CartFlow cart event was received (cart bridge not connected).
    """
    from services.admin_operations_center_v1 import _alert_with_records

    alerts: list[dict[str, Any]] = []
    for st in stores:
        beacon = _beacon_dict_from_store(st)
        if not beacon:
            continue
        rt = _parse_runtime_truth_raw(beacon)
        if not rt:
            continue
        if _norm_bool(rt.get("config_loaded")) is not True:
            continue
        page_url = str(beacon.get("page_url") or "")
        if not page_url or not _CART_PAGE_RE.search(page_url):
            continue
        cb = rt.get("cart_bridge") if isinstance(rt, dict) else None
        last_event_at = cb.get("last_event_at") if isinstance(cb, dict) else None
        if last_event_at:
            continue

        slug = st.get("store_slug") or st.get("widget_last_runtime_slug") or ""
        platform = _platform_from_page_url(page_url)
        name = st.get("display_name") or slug or "متجر"
        record = {
            "store_slug": slug,
            "platform": platform,
            "page_url": page_url[:512],
            "expected_signal": (
                "normalized CartFlowCartEvent (add_to_cart / cart_detected)"
            ),
            "detected_storefront_state": (
                "cart/checkout page visited with public-config loaded, "
                "but no cart bridge event received"
            ),
            "suggested_fix_ar": (
                "تحقق من اتصال Cart Event Bridge ومحوّل المنصة "
                "(zidCartEventSource): راجع سجلات [CF CART EVENT SOURCE] و"
                "[CF CART EVENT NORMALIZED] في المتصفح، وتأكد أن المتجر يطلق "
                "إشارة إضافة/تحديث السلة."
            ),
        }
        alerts.append(
            _alert_with_records(
                kind="cart_event_bridge_missing",
                title_ar="جسر أحداث السلة غير متصل",
                detail_ar=(
                    f"{name} — الودجيت مُركّب وpublic-config محمّل وصفحة السلة "
                    "مفتوحة، لكن لم يصل أي حدث سلة موحّد إلى CartFlow."
                ),
                records=[record],
                records_total=1,
            )
        )
    return alerts


__all__ = [
    "build_admin_widget_runtime_mismatch_alerts",
    "build_cart_event_bridge_missing_alerts",
    "cart_bridge_state_from_beacon",
    "dashboard_widget_settings",
    "evaluate_widget_settings_runtime_truth",
    "public_config_widget_settings",
    "runtime_truth_beacon_present",
    "runtime_widget_settings_from_beacon",
]
