# -*- coding: utf-8 -*-
"""
Compose slim Home Executive Summary V1 payload (Gate 1 — Home Slim Transport).

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

SECTION_IDS_V1 = (
    "health",
    "decisions",
    "observations",
    "carts",
    "communication",
)

OBS_EMPTY_AR = "لا توجد أدلة كافية لإصدار ملاحظة مرتبطة بمنتج محدد."

GOVERNANCE_V1 = {
    "sprint": "home_stabilization_v1",
    "gate": "gate_1_home_slim_transport",
    "single_owner": "home_executive_summary_v1",
    "single_data_source": "home_teaser_inputs_v1",
    "single_render_path": "maApplyHomeExecutiveSummaryV1",
    "sections": list(SECTION_IDS_V1),
    "product_intelligence": False,
}


def _teasers(summary: Mapping[str, Any]) -> dict[str, Any]:
    raw = summary.get("home_teaser_inputs_v1")
    if isinstance(raw, Mapping) and raw.get("schema") == "home_teaser_inputs_v1":
        return dict(raw)
    return extract_home_teaser_inputs_v1(summary)


def _observation_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    t = _teasers(summary)
    obs = t.get("observations") if isinstance(t.get("observations"), Mapping) else {}
    count = int(obs.get("count") or 0)
    top = obs.get("top") if isinstance(obs.get("top"), Mapping) else None
    if count <= 0 or not top:
        return {
            "id": "observations",
            "title_ar": "ملاحظات المنتجات",
            "summary_ar": OBS_EMPTY_AR,
            "status_ar": "أدلة غير كافية",
            "count": 0,
            "view_details_href": "#workspace",
            "view_details_ar": "عرض التفاصيل",
            "empty": True,
            "empty_state_ar": OBS_EMPTY_AR,
            "findings_preview": [],
        }
    name = str(top.get("product_name_ar") or "").strip()
    statement = str(top.get("statement_ar") or "").strip()
    summary_ar = f"{name}: {statement}" if name else statement
    return {
        "id": "observations",
        "title_ar": "ملاحظات المنتجات",
        "summary_ar": summary_ar,
        "status_ar": "متوفر",
        "count": count,
        "view_details_href": "#workspace",
        "view_details_ar": "عرض التفاصيل",
        "empty": False,
        "empty_state_ar": "",
        # Gate 1: no PI preview cards on Home
        "findings_preview": [],
    }


def _decisions_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    t = _teasers(summary)
    dec = t.get("decisions") if isinstance(t.get("decisions"), Mapping) else {}
    count = int(dec.get("count") or 0)
    title = str(dec.get("top_title_ar") or "").strip()
    if count == 0:
        return {
            "id": "decisions",
            "title_ar": "قرارات اليوم",
            "summary_ar": "لا قرار قابل للتنفيذ اليوم — راجع مساحة القرار عند توفر أدلة.",
            "status_ar": "لا قرار",
            "count": 0,
            "view_details_href": "#workspace",
            "view_details_ar": "عرض التفاصيل",
            "empty": True,
        }
    return {
        "id": "decisions",
        "title_ar": "قرارات اليوم",
        "summary_ar": title or "قرار جاهز للمراجعة",
        "status_ar": "جاهز للمراجعة",
        "count": count,
        "view_details_href": "#workspace",
        "view_details_ar": "عرض التفاصيل",
        "empty": False,
    }


def _health_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    t = _teasers(summary)
    health = t.get("health") if isinstance(t.get("health"), Mapping) else {}
    watching = bool(health.get("watching")) or int(health.get("abandoned_carts") or 0) > 0
    if watching:
        summary_ar = "CartFlow يراقب متجرك — ركّز على القرار الأهم اليوم."
        status_ar = "مراقبة"
    else:
        summary_ar = "لا نشاط كافٍ بعد لملخص تشغيلي — استمر في جمع الأدلة."
        status_ar = "بانتظار أدلة"
    return {
        "id": "health",
        "title_ar": "صحة العمل",
        "summary_ar": summary_ar,
        "status_ar": status_ar,
        "view_details_href": "#carts",
        "view_details_ar": "عرض التفاصيل",
        "empty": not watching,
    }


def _carts_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    t = _teasers(summary)
    carts = t.get("carts") if isinstance(t.get("carts"), Mapping) else {}
    count = int(carts.get("count") or 0)
    if count > 0:
        summary_ar = f"{count} سلة مسجّلة — التفاصيل في صفحة السلال."
        status_ar = "نشط"
        empty = False
    else:
        summary_ar = "لا سلات مسجّلة بعد — راقب عند توفر نشاط."
        status_ar = "فارغ"
        empty = True
    return {
        "id": "carts",
        "title_ar": "السلال",
        "summary_ar": summary_ar,
        "status_ar": status_ar,
        "count": count,
        "view_details_href": "#carts",
        "view_details_ar": "عرض التفاصيل",
        "empty": empty,
    }


def _communication_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    t = _teasers(summary)
    comm = t.get("communication") if isinstance(t.get("communication"), Mapping) else {}
    sent = int(comm.get("sent") or 0)
    schedules = int(comm.get("schedules") or 0)
    count = sent + schedules
    activity = bool(comm.get("activity")) or count > 0
    if activity:
        summary_ar = f"نشاط تواصل: {sent} إرسال و{schedules} جدولة."
        status_ar = "نشط"
        empty = False
    else:
        summary_ar = "لا نشاط تواصل تشغيلي مسجّل بعد."
        status_ar = "بانتظار"
        empty = True
    return {
        "id": "communication",
        "title_ar": "التواصل",
        "summary_ar": summary_ar,
        "status_ar": status_ar,
        "count": count,
        "view_details_href": "#communication",
        "view_details_ar": "عرض التفاصيل",
        "empty": empty,
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
    "GOVERNANCE_V1",
    "OBS_EMPTY_AR",
    "OWNERSHIP_V1",
    "SECTION_IDS_V1",
    "attach_home_executive_summary_to_summary_v1",
    "build_home_executive_summary_v1",
    "slim_observation_package_for_home_v1",
]
