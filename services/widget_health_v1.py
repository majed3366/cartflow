# -*- coding: utf-8 -*-
"""
Admin Operations → Widget Health v1 (read-only observability).

Detect widget / runtime / integration problems before merchants report them by
aggregating existing per-store signals (runtime beacon, widget-seen, runtime
truth, public config). This module is PURE read-only: it never mutates widget
behavior, trigger logic, the cart event bridge, recovery, lifecycle, purchase
truth, or store identity. It only derives a health view + an issues list.

Data sources (no duplicate truth systems):
  * Store.widget_last_beacon_json  -> runtime_truth (+ widget_health, cart_bridge)
  * Store.widget_last_runtime_slug -> runtime version fallback
  * Store.widget_last_seen_at      -> last seen
  * Store.widget_runtime_truth_status -> identity/settings gate status
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

SECTION_KEY = "widget_health"

STATUS_HEALTHY = "healthy"
STATUS_WARNING = "warning"
STATUS_CRITICAL = "critical"

_STATUS_AR = {
    STATUS_HEALTHY: "سليم",
    STATUS_WARNING: "تحذير",
    STATUS_CRITICAL: "حرج",
}
_STATUS_EMOJI = {
    STATUS_HEALTHY: "🟢",
    STATUS_WARNING: "🟡",
    STATUS_CRITICAL: "🔴",
}
_STATUS_RANK = {STATUS_HEALTHY: 0, STATUS_WARNING: 1, STATUS_CRITICAL: 2}

# Issue registry — one entry per required issue kind. severity drives status.
_WIDGET_ISSUE_REGISTRY: dict[str, dict[str, str]] = {
    "widget_module_failed": {
        "severity": STATUS_CRITICAL,
        "problem_ar": "فشل تحميل إحدى وحدات تشغيل الودجِت",
        "impact_ar": "قد لا يظهر الودجِت للعملاء على هذا المتجر",
        "suggested_action_ar": (
            "راجع نشر ملفات تشغيل الودجِت (static/cartflow_widget_runtime) وتأكد من "
            "توفّرها بإصدار الـ runtime الصحيح على المتجر"
        ),
        "verification_ar": (
            "تأكد من غياب [CF V2 MODULE FAILED] وظهور [CF V2 ALL MODULES LOADED]"
        ),
    },
    "widget_bootstrap_blocked": {
        "severity": STATUS_CRITICAL,
        "problem_ar": "تم حظر إقلاع تشغيل الودجِت (Bootstrap Blocked)",
        "impact_ar": "الودجِت قد لا يظهر للعملاء",
        "suggested_action_ar": "راجع نشر تشغيل الودجِت وإصدار الـ runtime على المتجر",
        "verification_ar": (
            "تأكد من ظهور [CF V2 BOOTSTRAP READY] وغياب [CF V2 BOOTSTRAP BLOCKED]"
        ),
    },
    "widget_runtime_object_missing": {
        "severity": STATUS_CRITICAL,
        "problem_ar": "كائن تشغيل مفقود في CartflowWidgetRuntime",
        "impact_ar": "يُحظر الإقلاع ولا يظهر الودجِت",
        "suggested_action_ar": "تأكد من تحميل جميع وحدات runtime بالترتيب الصحيح",
        "verification_ar": (
            "تأكد من تسجيل CartflowWidgetRuntime.Triggers و CartflowWidgetRuntime."
            "TriggerOrchestrator"
        ),
    },
    "widget_settings_mismatch": {
        "severity": STATUS_WARNING,
        "problem_ar": "اختلاف بين إعدادات اللوحة وتشغيل الودجِت",
        "impact_ar": "قد يظهر الودجِت بسلوك مختلف عن إعدادات التاجر",
        "suggested_action_ar": "أعد حفظ إعدادات الودجِت وتحقق من public-config",
        "verification_ar": "طابق [CF ENABLE/EXIT/HESITATION TRUTH] مع إعدادات اللوحة",
    },
    "store_identity_mismatch": {
        "severity": STATUS_WARNING,
        "problem_ar": "تعذّر مطابقة هوية المتجر مع تشغيل الودجِت",
        "impact_ar": "قد لا تُربط أحداث الودجِت بالمتجر الصحيح",
        "suggested_action_ar": "تحقق من ربط رابط المتجر (zid_permalink) بهوية CartFlow",
        "verification_ar": "تأكد من storefront_resolved=true في تقرير حقيقة التشغيل",
    },
    "widget_not_seen": {
        "severity": STATUS_WARNING,
        "problem_ar": "لم يُرصد ظهور الودجِت على المتجر",
        "impact_ar": "العملاء قد لا يرون الودجِت",
        "suggested_action_ar": "تأكد من تثبيت الودجِت وتحميله على صفحات المتجر",
        "verification_ar": "تأكد من وصول beacon (widget-seen) من المتجر",
    },
    "runtime_beacon_missing": {
        "severity": STATUS_WARNING,
        "problem_ar": "لم يصل beacon حقيقة التشغيل",
        "impact_ar": "لا يمكن التحقق من تشغيل الودجِت فعلياً على المتجر",
        "suggested_action_ar": "تأكد من تحميل الودجِت وعدم حجب طلب widget-seen",
        "verification_ar": "تأكد من وصول POST /api/storefront/widget-seen",
    },
    "public_config_not_loaded": {
        "severity": STATUS_WARNING,
        "problem_ar": "لم يتم تحميل إعدادات العرض العامة (public-config)",
        "impact_ar": "قد لا يعمل الودجِت بإعدادات التاجر",
        "suggested_action_ar": "تحقق من /api/cartflow/public-config وربط المتجر",
        "verification_ar": "تأكد من config_loaded=true في beacon التشغيل",
    },
    "cart_event_bridge_missing": {
        "severity": STATUS_WARNING,
        "problem_ar": "لم تصل أحداث السلة عبر جسر الأحداث (Cart Event Bridge)",
        "impact_ar": "قد لا يُسلَّح مؤقّت التردد ولا يظهر الودجِت بعد الإضافة للسلة",
        "suggested_action_ar": "تحقق من تحميل وحدات جسر أحداث السلة على المتجر",
        "verification_ar": "تأكد من [CF CART EVENT NORMALIZED] بعد الإضافة للسلة",
    },
    "cart_event_false_positive": {
        "severity": STATUS_WARNING,
        "problem_ar": "حدث سلة مزيّف عند تحميل الصفحة",
        "impact_ar": "قد يظهر الودجِت قبل إضافة منتج فعلي",
        "suggested_action_ar": "راجع طبقات كشف السلة في zidCartEventSource",
        "verification_ar": "تأكد من initial_load_window_hydration_only عند التحميل",
    },
    "hesitation_not_armed": {
        "severity": STATUS_WARNING,
        "problem_ar": "لم يُسلَّح مؤقّت التردد رغم وجود حدث سلة",
        "impact_ar": "قد لا يظهر الودجِت عبر مسار التردد",
        "suggested_action_ar": "تأكد من تفعيل التردد ووصول حدث سلة طبيعي",
        "verification_ar": "تأكد من [CF HESITATION ARMED] بعد حدث السلة",
    },
    "widget_not_shown_after_cart_event": {
        "severity": STATUS_CRITICAL,
        "problem_ar": "لم يظهر الودجِت رغم وجود حدث سلة وتسليح التردد",
        "impact_ar": "العميل لم يرَ رسالة الاسترداد رغم توفّر الشروط",
        "suggested_action_ar": (
            "راجع مسار العرض (Shell/Flows) وحالات الكبت (frequency/suppression)"
        ),
        "verification_ar": "تأكد من [CF WIDGET SHOW] بعد [CF HESITATION TIMER FIRED]",
    },
    "widget_cors_error": {
        "severity": STATUS_WARNING,
        "problem_ar": "خطأ CORS أثناء إرسال beacon التشغيل",
        "impact_ar": "قد لا تُحفظ حقيقة التشغيل (Observability فقط)",
        "suggested_action_ar": (
            "تأكد من ترويسات CORS لِـ widget-seen (Allow-Origin/Allow-Credentials)"
        ),
        "verification_ar": (
            "تأكد من نجاح POST /api/storefront/widget-seen دون خطأ CORS"
        ),
    },
}

_CART_PAGE_TOKENS = ("/cart", "/checkout", "cart", "checkout", "سلة", "الدفع")


def _as_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (str, bytes)):
        try:
            val = json.loads(raw)
            return val if isinstance(val, dict) else {}
        except (ValueError, TypeError):
            return {}
    return {}


def _norm_bool(v: Any) -> Optional[bool]:
    if v is True or v is False:
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "1", "yes"):
            return True
        if s in ("false", "0", "no"):
            return False
    return None


def _str_list(v: Any) -> list[str]:
    if isinstance(v, list):
        return [str(x)[:128] for x in v if x is not None and str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip()[:128]]
    return []


def _beacon_from_store(store: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(store.get("widget_last_beacon_json"))


def _runtime_truth(beacon: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(beacon.get("runtime_truth"))


def _platform_from_beacon(beacon: dict[str, Any]) -> str:
    url = str(beacon.get("page_url") or "").lower()
    if ".zid.store" in url or "zid" in url:
        return "Zid"
    if ".salla." in url or "salla" in url:
        return "Salla"
    if "shopify" in url or "myshopify" in url:
        return "Shopify"
    return "—"


def _is_cart_page(beacon: dict[str, Any]) -> bool:
    url = str(beacon.get("page_url") or "").lower()
    if not url:
        return False
    return any(tok in url for tok in _CART_PAGE_TOKENS)


def widget_health_from_beacon(beacon: Any) -> dict[str, Any]:
    """Normalize the read-only widget health fields from a beacon (additive)."""
    b = _as_dict(beacon)
    rt = _runtime_truth(b)
    wh = _as_dict(rt.get("widget_health"))
    cb = _as_dict(rt.get("cart_bridge"))

    last_cart_event_type = (
        wh.get("last_cart_event_type") or cb.get("last_event_type") or None
    )
    last_cart_event_at = wh.get("last_cart_event_at") or cb.get("last_event_at") or None
    hesitation_armed = _norm_bool(
        wh.get("hesitation_armed")
        if wh.get("hesitation_armed") is not None
        else cb.get("hesitation_armed_from_cart_event")
    )

    return {
        "module_load_status": (wh.get("module_load_status") or "")[:32] or None
        if isinstance(wh.get("module_load_status"), str)
        else None,
        "failed_modules": _str_list(wh.get("failed_modules")),
        "bootstrap_ready": _norm_bool(wh.get("bootstrap_ready")),
        "bootstrap_blocked": _norm_bool(wh.get("bootstrap_blocked")),
        "missing_runtime_objects": _str_list(wh.get("missing_runtime_objects")),
        "runtime_version": (
            str(wh.get("runtime_version") or b.get("runtime_version") or "")[:128]
            or None
        ),
        "config_loaded": _norm_bool(rt.get("config_loaded")),
        "widget_enabled": _norm_bool(rt.get("widget_enabled")),
        "hesitation_trigger_enabled": _norm_bool(rt.get("hesitation_trigger_enabled")),
        "widget_shown": _norm_bool(
            wh.get("widget_shown")
            if wh.get("widget_shown") is not None
            else rt.get("widget_rendered")
        ),
        "last_cart_event_type": last_cart_event_type,
        "last_cart_event_at": last_cart_event_at,
        "hesitation_armed": bool(hesitation_armed),
        "cart_false_positive": _norm_bool(wh.get("cart_false_positive")),
        "last_runtime_error": (str(wh.get("last_runtime_error") or "")[:512] or None),
        "page_url": str(b.get("page_url") or "")[:2048] or None,
        "has_runtime_truth": bool(rt),
    }


def _issue(kind: str, *, store: dict[str, Any], where_extra: str = "",
           technical: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    meta = _WIDGET_ISSUE_REGISTRY.get(kind, {})
    sev = meta.get("severity", STATUS_WARNING)
    slug = str(store.get("store_slug") or "")[:128]
    name = str(store.get("display_name") or slug or "متجر")[:128]
    return {
        "kind": kind,
        "severity": sev,
        "severity_ar": _STATUS_AR.get(sev, sev),
        "severity_emoji": _STATUS_EMOJI.get(sev, ""),
        "problem_ar": meta.get("problem_ar", kind),
        "impact_ar": meta.get("impact_ar", ""),
        "suggested_action_ar": meta.get("suggested_action_ar", ""),
        "verification_ar": meta.get("verification_ar", ""),
        "store_slug": slug,
        "store_name": name,
        "where_ar": where_extra or "",
        "technical_details": technical or {},
    }


def detect_widget_issues(
    store: dict[str, Any],
    health: dict[str, Any],
    *,
    truth_status: str = "",
) -> list[dict[str, Any]]:
    """Read-only detection of the required widget issue kinds for one store."""
    issues: list[dict[str, Any]] = []
    beacon = _beacon_from_store(store)
    runtime_ver = health.get("runtime_version") or store.get(
        "widget_last_runtime_slug"
    )
    where = f"Runtime: {runtime_ver}" if runtime_ver else ""
    has_beacon = bool(health.get("has_runtime_truth"))
    last_seen = store.get("widget_last_seen_at")

    if not has_beacon:
        issues.append(_issue("runtime_beacon_missing", store=store, where_extra=where))
        if not last_seen:
            issues.append(_issue("widget_not_seen", store=store, where_extra=where))
        return issues

    # Critical runtime/bootstrap failures (the real-world incident).
    if health.get("module_load_status") == "failed" or health.get("failed_modules"):
        issues.append(
            _issue(
                "widget_module_failed",
                store=store,
                where_extra=where,
                technical={"failed_modules": health.get("failed_modules")},
            )
        )
    if health.get("bootstrap_blocked") is True:
        issues.append(
            _issue(
                "widget_bootstrap_blocked",
                store=store,
                where_extra=where,
                technical={
                    "missing_runtime_objects": health.get("missing_runtime_objects"),
                    "bootstrap_ready": health.get("bootstrap_ready"),
                },
            )
        )
    if health.get("missing_runtime_objects"):
        issues.append(
            _issue(
                "widget_runtime_object_missing",
                store=store,
                where_extra=where,
                technical={
                    "missing_runtime_objects": health.get("missing_runtime_objects")
                },
            )
        )

    # Config / identity.
    if health.get("config_loaded") is False:
        issues.append(
            _issue("public_config_not_loaded", store=store, where_extra=where)
        )
    ts = (truth_status or "").strip().lower()
    if ts == "unresolved":
        issues.append(_issue("store_identity_mismatch", store=store, where_extra=where))
    elif ts == "mismatch":
        issues.append(_issue("widget_settings_mismatch", store=store, where_extra=where))

    # Cart bridge / hesitation / show-after-cart.
    has_cart_event = bool(health.get("last_cart_event_at"))
    hesitation_on = health.get("hesitation_trigger_enabled") is not False
    if health.get("config_loaded") is True and _is_cart_page(beacon) and not has_cart_event:
        issues.append(
            _issue("cart_event_bridge_missing", store=store, where_extra=where)
        )
    if health.get("cart_false_positive") is True:
        issues.append(
            _issue("cart_event_false_positive", store=store, where_extra=where)
        )
    if has_cart_event and hesitation_on and not health.get("hesitation_armed"):
        issues.append(_issue("hesitation_not_armed", store=store, where_extra=where))
    if (
        has_cart_event
        and health.get("hesitation_armed")
        and health.get("widget_shown") is False
    ):
        issues.append(
            _issue(
                "widget_not_shown_after_cart_event", store=store, where_extra=where
            )
        )

    # CORS observability error captured in last_runtime_error.
    lre = (health.get("last_runtime_error") or "").lower()
    if "cors" in lre:
        issues.append(
            _issue(
                "widget_cors_error",
                store=store,
                where_extra=where,
                technical={"last_runtime_error": health.get("last_runtime_error")},
            )
        )

    return issues


def _status_from_issues(issues: list[dict[str, Any]]) -> str:
    rank = 0
    for it in issues:
        rank = max(rank, _STATUS_RANK.get(it.get("severity", STATUS_WARNING), 1))
    if rank >= _STATUS_RANK[STATUS_CRITICAL]:
        return STATUS_CRITICAL
    if rank >= _STATUS_RANK[STATUS_WARNING]:
        return STATUS_WARNING
    return STATUS_HEALTHY


def build_store_widget_health_row(store: dict[str, Any]) -> dict[str, Any]:
    """Per-store widget health row (Phase 1 + status + detected issues)."""
    beacon = _beacon_from_store(store)
    health = widget_health_from_beacon(beacon)
    truth_status = str(store.get("widget_runtime_truth_status") or "").strip()
    issues = detect_widget_issues(store, health, truth_status=truth_status)
    status = _status_from_issues(issues)

    has_beacon = bool(health.get("has_runtime_truth"))
    last_seen = store.get("widget_last_seen_at")
    cart_event_type = health.get("last_cart_event_type")
    if cart_event_type:
        bridge_status = "ok"
    elif has_beacon and _is_cart_page(beacon):
        bridge_status = "missing"
    else:
        bridge_status = "unknown"

    return {
        "store_name": str(store.get("display_name") or store.get("store_slug") or "متجر")[
            :128
        ],
        "store_slug": str(store.get("store_slug") or "")[:128],
        "platform": _platform_from_beacon(beacon),
        "runtime_version": health.get("runtime_version")
        or (store.get("widget_last_runtime_slug") or None),
        "widget_installed": bool(has_beacon or last_seen),
        "public_config_loaded": health.get("config_loaded") is True,
        "runtime_beacon_received": has_beacon,
        "store_identity_resolved": truth_status not in ("", "unresolved"),
        "cart_event_bridge_status": bridge_status,
        "last_cart_event_type": cart_event_type,
        "last_cart_event_at": health.get("last_cart_event_at"),
        "hesitation_armed": bool(health.get("hesitation_armed")),
        "widget_shown": health.get("widget_shown"),
        "last_runtime_error": health.get("last_runtime_error"),
        "last_seen": last_seen,
        "status": status,
        "status_ar": _STATUS_AR.get(status, status),
        "status_emoji": _STATUS_EMOJI.get(status, ""),
        "issue_kinds": [it["kind"] for it in issues],
        "issues": issues,
        "technical_details": {
            "module_load_status": health.get("module_load_status"),
            "failed_modules": health.get("failed_modules"),
            "bootstrap_ready": health.get("bootstrap_ready"),
            "bootstrap_blocked": health.get("bootstrap_blocked"),
            "missing_runtime_objects": health.get("missing_runtime_objects"),
            "runtime_version": health.get("runtime_version"),
            "page_url": health.get("page_url"),
            "runtime_truth_status": truth_status or None,
        },
    }


def _store_rows_from_db() -> list[dict[str, Any]]:
    """Reuse existing admin ops store readiness rows (single source of truth)."""
    try:
        from services.admin_operations_center_v1 import (  # noqa: PLC0415
            _store_readiness_summary,
        )

        _summary, per_store = _store_readiness_summary()
        return per_store or []
    except Exception:  # noqa: BLE001
        return []


def build_admin_widget_health_section_readonly(
    *, stores: Optional[list[dict[str, Any]]] = None
) -> dict[str, Any]:
    """Full Widget Health section payload (per-store health rows + issues)."""
    rows_in = stores if stores is not None else _store_rows_from_db()
    health_rows: list[dict[str, Any]] = []
    all_issues: list[dict[str, Any]] = []
    counts = {STATUS_HEALTHY: 0, STATUS_WARNING: 0, STATUS_CRITICAL: 0}

    for st in rows_in:
        row = build_store_widget_health_row(st)
        health_rows.append(row)
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        all_issues.extend(row["issues"])

    all_issues.sort(
        key=lambda it: _STATUS_RANK.get(it.get("severity", STATUS_WARNING), 1),
        reverse=True,
    )

    return {
        "section": SECTION_KEY,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_stores": len(health_rows),
            "healthy": counts.get(STATUS_HEALTHY, 0),
            "warning": counts.get(STATUS_WARNING, 0),
            "critical": counts.get(STATUS_CRITICAL, 0),
            "total_issues": len(all_issues),
        },
        "stores": health_rows,
        "issues": all_issues,
    }
