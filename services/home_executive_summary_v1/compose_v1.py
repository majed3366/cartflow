# -*- coding: utf-8 -*-
"""
Compose Home Executive Summary V1 (Gate 1-B — Executive Summary Composition).

Home answers: "What should the merchant know now?"
Prefers ``home_teaser_inputs_v1`` (lightweight). Never ships PI action/confidence
previews on Home — View Details routes to owning pages.
"""
from __future__ import annotations

from typing import Any, Mapping

from services.home_executive_summary_v1.flag_v1 import home_executive_summary_v1_enabled
from services.home_executive_summary_v1.slim_transport_v1 import (
    extract_home_teaser_inputs_v1,
    home_slim_transport_v1_enabled,
)

OWNERSHIP_V1 = {
    "home": "executive_summary",
    "decision_workspace": "decisions",
    "product_intelligence": "product_findings",
    "carts": "cart_operations",
    "communication": "communication",
    "settings": "configuration",
}

# Stable section ids (transport/UI). Titles are merchant-facing Arabic.
SECTION_IDS_V1 = (
    "health",
    "decisions",
    "observations",
    "carts",
    "communication",
)

OBS_EMPTY_AR = "لا توجد أدلة كافية لإصدار ملاحظة مرتبطة بمنتج محدد."
DECISIONS_EMPTY_AR = "لا تتوفر أدلة كافية لإصدار قرار اليوم."

GOVERNANCE_V1 = {
    "sprint": "home_stabilization_v1",
    "gate": "gate_2d_business_domain_composition",
    "single_owner": "home_executive_summary_v1",
    "single_data_source": "home_teaser_inputs_v1",
    "single_render_path": "maApplyHomeExecutiveSummaryV1",
    "sections": list(SECTION_IDS_V1),
    "product_intelligence": False,
    "home_creates_decisions": False,
}

# Card → owning constitutional page (View Details).
SECTION_OWNERSHIP_HREF_V1 = {
    "health": "#carts",
    "decisions": "#workspace",
    "observations": "#workspace",
    "carts": "#carts",
    "communication": "#communication",
}

# Gate 2 — Home decision teasers must route explicitly to Cart Workspace.
DECISIONS_VIEW_DETAILS_AR = "عرض التفاصيل ← مساحة القرار"


def _teasers(summary: Mapping[str, Any]) -> dict[str, Any]:
    raw = summary.get("home_teaser_inputs_v1")
    if isinstance(raw, Mapping) and raw.get("schema") == "home_teaser_inputs_v1":
        return dict(raw)
    return extract_home_teaser_inputs_v1(summary)


def _as_int(v: Any) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


def _observation_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    t = _teasers(summary)
    obs = t.get("observations") if isinstance(t.get("observations"), Mapping) else {}
    count = _as_int(obs.get("count"))
    top = obs.get("top") if isinstance(obs.get("top"), Mapping) else None
    if count <= 0 or not top:
        return {
            "id": "observations",
            "title_ar": "ملاحظات المنتجات",
            "summary_ar": OBS_EMPTY_AR,
            "status_ar": "أدلة غير كافية",
            "count": 0,
            "view_details_href": SECTION_OWNERSHIP_HREF_V1["observations"],
            "view_details_ar": "عرض التفاصيل",
            "empty": True,
            "empty_state_ar": OBS_EMPTY_AR,
            "findings_preview": [],
            "owner_page": "decision_workspace",
        }
    name = str(top.get("product_name_ar") or "").strip()
    statement = str(top.get("statement_ar") or "").strip()
    # Merchant-oriented observation line — statement only (no action/confidence).
    if name and statement:
        summary_ar = f"المنتج {name}: {statement}"
    elif name:
        summary_ar = f"المنتج {name} يحتاج متابعة."
    else:
        summary_ar = statement
    return {
        "id": "observations",
        "title_ar": "ملاحظات المنتجات",
        "summary_ar": summary_ar,
        "status_ar": "يتطلب انتباهاً",
        "count": count,
        "view_details_href": SECTION_OWNERSHIP_HREF_V1["observations"],
        "view_details_ar": "عرض التفاصيل",
        "empty": False,
        "empty_state_ar": "",
        "findings_preview": [],
        "owner_page": "decision_workspace",
    }


def _decisions_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    t = _teasers(summary)
    dec = t.get("decisions") if isinstance(t.get("decisions"), Mapping) else {}
    count = _as_int(dec.get("count"))
    title = str(dec.get("top_title_ar") or "").strip()
    # Only surface a decision when evidence-backed title exists — never invent.
    if count <= 0 or not title:
        return {
            "id": "decisions",
            "title_ar": "قرارات اليوم",
            "summary_ar": DECISIONS_EMPTY_AR,
            "status_ar": "أدلة غير كافية",
            "count": 0,
            "view_details_href": SECTION_OWNERSHIP_HREF_V1["decisions"],
            "view_details_ar": DECISIONS_VIEW_DETAILS_AR,
            "empty": True,
            "owner_page": "decision_workspace",
        }
    return {
        "id": "decisions",
        "title_ar": "قرارات اليوم",
        "summary_ar": title,
        "status_ar": "أولوية اليوم" if count == 1 else f"{count} قرارات",
        "count": count,
        "view_details_href": SECTION_OWNERSHIP_HREF_V1["decisions"],
        "view_details_ar": DECISIONS_VIEW_DETAILS_AR,
        "empty": False,
        "owner_page": "decision_workspace",
    }


def _health_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    t = _teasers(summary)
    health = t.get("health") if isinstance(t.get("health"), Mapping) else {}
    waiting = _as_int(health.get("abandoned_carts"))
    active = _as_int(health.get("active_carts"))
    recovered = _as_int(health.get("recovered_today"))
    no_phone = _as_int(health.get("no_phone"))
    store_ok = health.get("store_connected")
    needs = bool(health.get("needs_attention")) or waiting > 0 or no_phone > 0
    # Gate 2D — prefer domain executive summary; never restate Today's Decision.
    domain_summary = str(health.get("domain_summary_ar") or "").strip()

    href = SECTION_OWNERSHIP_HREF_V1["health"]
    if store_ok is False:
        summary_ar = "ربط المتجر يحتاج متابعة قبل الاعتماد على الملخص التشغيلي."
        status_ar = "يتطلب متابعة"
        href = "#home-setup"
        empty = False
    elif domain_summary:
        summary_ar = domain_summary
        status_ar = "يتطلب متابعة" if needs else "مستقر"
        empty = not needs and "بانتظار" in domain_summary
    elif waiting > 0 or no_phone > 0:
        # Fallback without naming the same recoverability decision.
        summary_ar = "المتجر يحتاج انتباهاً — التفاصيل في قرارات اليوم."
        status_ar = "يتطلب متابعة"
        empty = False
    elif active > 0 or recovered > 0:
        summary_ar = "حركة المتجر مستقرة — لا توجد مشكلات تشغيلية مؤثرة ظاهرة الآن."
        status_ar = "مستقر"
        empty = False
        needs = False
    else:
        summary_ar = "لا توجد مشكلات تشغيلية مؤثرة ظاهرة — بانتظار نشاط كافٍ لملخص أدق."
        status_ar = "هادئ"
        empty = True
        needs = False

    out = {
        "id": "health",
        "title_ar": "حالة المتجر",
        "summary_ar": summary_ar,
        "status_ar": status_ar,
        "view_details_href": href,
        "view_details_ar": "عرض التفاصيل",
        "empty": empty,
        "needs_attention": needs,
        "owner_page": "carts" if href == "#carts" else "settings",
    }
    if waiting > 0:
        out["count"] = waiting
    elif active > 0:
        out["count"] = active
    return out


def _carts_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    t = _teasers(summary)
    carts = t.get("carts") if isinstance(t.get("carts"), Mapping) else {}
    waiting = _as_int(carts.get("waiting") if carts.get("waiting") is not None else carts.get("count"))
    active = _as_int(carts.get("active"))
    no_phone = _as_int(carts.get("no_phone"))
    count = waiting
    # Gate 2D — short ops summary from domain layer (not a business decision).
    domain_summary = str(carts.get("domain_summary_ar") or "").strip()

    if domain_summary:
        summary_ar = domain_summary
        if waiting > 0 or no_phone > 0:
            status_ar = "يتطلب متابعة"
            empty = False
            if waiting <= 0 and no_phone > 0:
                count = no_phone
        elif active > 0:
            status_ar = "نشط"
            empty = False
            count = active
        else:
            status_ar = "لا مهام"
            empty = True
    elif waiting > 0 and no_phone > 0:
        summary_ar = "توجد سلال بانتظار المتابعة، وحالات بلا رقم."
        status_ar = "يتطلب متابعة"
        empty = False
    elif waiting > 0:
        summary_ar = "توجد سلال بانتظار المتابعة."
        status_ar = "بانتظار متابعة"
        empty = False
    elif no_phone > 0:
        summary_ar = "توجد سلال بلا رقم تواصل."
        status_ar = "بلا تواصل"
        empty = False
        count = no_phone
    elif active > 0:
        summary_ar = "حركة سلال نشطة — لا طوابير متابعة ظاهرة الآن."
        status_ar = "نشط"
        empty = False
        count = active
    else:
        summary_ar = "لا توجد سلال تحتاج متابعة حالياً."
        status_ar = "لا مهام"
        empty = True

    return {
        "id": "carts",
        "title_ar": "السلال",
        "summary_ar": summary_ar,
        "status_ar": status_ar,
        "count": count,
        "view_details_href": SECTION_OWNERSHIP_HREF_V1["carts"],
        "view_details_ar": "عرض التفاصيل",
        "empty": empty,
        "owner_page": "carts",
    }


def _communication_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    t = _teasers(summary)
    comm = t.get("communication") if isinstance(t.get("communication"), Mapping) else {}
    sent = _as_int(comm.get("sent"))
    schedules = _as_int(comm.get("schedules"))
    no_phone = _as_int(comm.get("no_phone"))
    waiting = _as_int(comm.get("waiting"))
    wa_state = str(comm.get("wa_state_key") or "").strip().lower()
    count = sent + schedules
    domain_summary = str(comm.get("domain_summary_ar") or "").strip()

    if domain_summary and (no_phone > 0 or waiting > 0 or schedules > 0):
        summary_ar = domain_summary
        status_ar = "يتطلب متابعة" if (no_phone > 0 or waiting > 0) else "نشط"
        empty = False
        count = max(count, waiting, no_phone)
    elif no_phone > 0 and waiting > 0:
        summary_ar = "متابعة معلّقة، وتوجد حالات بلا رقم."
        status_ar = "يتطلب متابعة"
        empty = False
        count = max(count, waiting, no_phone)
    elif waiting > 0 or schedules > 0:
        summary_ar = "يوجد عملاء بانتظار المتابعة."
        status_ar = "بانتظار متابعة"
        empty = False
        count = max(count, waiting, schedules)
    elif no_phone > 0:
        summary_ar = "توجد سلال بلا رقم تواصل."
        status_ar = "بلا تواصل"
        empty = False
        count = no_phone
    elif sent > 0:
        summary_ar = f"تم تسجيل {sent} إرسال تواصل اليوم — لا مهام معلّقة ظاهرة."
        status_ar = "مكتمل اليوم"
        empty = False
    elif wa_state and wa_state not in {"ready", "connected", ""}:
        summary_ar = "مسار التواصل يحتاج ضبطاً قبل الاعتماد على المتابعة الآلية."
        status_ar = "يحتاج ضبطاً"
        empty = False
        # Settings/WhatsApp owns readiness — still route Communication for status history.
    else:
        summary_ar = "لا توجد مهام تواصل حالية."
        status_ar = "لا مهام"
        empty = True

    return {
        "id": "communication",
        "title_ar": "التواصل",
        "summary_ar": summary_ar,
        "status_ar": status_ar,
        "count": count,
        "view_details_href": SECTION_OWNERSHIP_HREF_V1["communication"],
        "view_details_ar": "عرض التفاصيل",
        "empty": empty,
        "owner_page": "communication",
    }


def build_home_executive_summary_v1(
    summary: Mapping[str, Any] | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not home_executive_summary_v1_enabled(environ=environ):
        return {
            "ok": False,
            "enabled": False,
            "schema": "home_executive_summary_v1",
            "sections": [],
            "governance": dict(GOVERNANCE_V1),
        }
    src = summary if isinstance(summary, Mapping) else {}
    sections = [
        _health_section(src),
        _decisions_section(src),
        _observation_section(src),
        _carts_section(src),
        _communication_section(src),
    ]
    return {
        "ok": True,
        "enabled": True,
        "schema": "home_executive_summary_v1",
        "eyebrow_ar": "ملخص تنفيذي",
        "title_ar": "ماذا يجب أن تعرف الآن؟",
        "lede_ar": "ملخص سريع فقط — التفاصيل في صفحاتها.",
        "ownership": dict(OWNERSHIP_V1),
        "section_ownership_href": dict(SECTION_OWNERSHIP_HREF_V1),
        "governance": dict(GOVERNANCE_V1),
        "sections": sections,
        "product_intelligence": False,
        "slim_transport": home_slim_transport_v1_enabled(environ=environ),
        "ui": True,
    }


def slim_observation_package_for_home_v1(pkg: Mapping[str, Any] | None) -> dict[str, Any]:
    """Gate 1: Home must not transport ORV detail — return empty stub only."""
    del pkg  # unused — never forward findings on Home
    return {
        "ok": True,
        "enabled": True,
        "findings": [],
        "count": 0,
        "empty_state_ar": OBS_EMPTY_AR,
        "schema": "observation_reality_validation_v1_home_stripped",
        "stripped_for_home_slim_transport": True,
    }


def attach_home_executive_summary_to_summary_v1(
    summary: dict[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return summary
    if not home_executive_summary_v1_enabled(environ=environ):
        return summary
    summary["home_surface_mode"] = "executive_summary_v1"
    try:
        if "home_teaser_inputs_v1" not in summary:
            summary["home_teaser_inputs_v1"] = extract_home_teaser_inputs_v1(summary)
        if home_slim_transport_v1_enabled(environ=environ):
            summary["observation_reality_validation_v1"] = (
                slim_observation_package_for_home_v1(None)
            )
        pkg = build_home_executive_summary_v1(summary, environ=environ)
        summary["home_executive_summary_v1"] = pkg
    except Exception:  # noqa: BLE001
        summary["home_executive_summary_v1"] = {
            "ok": False,
            "enabled": True,
            "error": "attach_failed",
            "sections": [],
            "governance": dict(GOVERNANCE_V1),
            "eyebrow_ar": "ملخص تنفيذي",
            "title_ar": "ماذا يجب أن تعرف الآن؟",
            "lede_ar": "تعذّر تحميل الملخص — أعد المحاولة.",
        }
    return summary


__all__ = [
    "DECISIONS_EMPTY_AR",
    "DECISIONS_VIEW_DETAILS_AR",
    "GOVERNANCE_V1",
    "OBS_EMPTY_AR",
    "OWNERSHIP_V1",
    "SECTION_IDS_V1",
    "SECTION_OWNERSHIP_HREF_V1",
    "attach_home_executive_summary_to_summary_v1",
    "build_home_executive_summary_v1",
    "slim_observation_package_for_home_v1",
]
