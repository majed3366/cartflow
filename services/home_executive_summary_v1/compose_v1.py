# -*- coding: utf-8 -*-
"""
Compose slim Home Executive Summary V1 payload.

Home answers: "What should the merchant know now?"
Detailed Observation / Decision / Operational / Product data stays off
the initial Home payload — only short summary + count + View Details.
"""
from __future__ import annotations

from typing import Any, Mapping

from services.home_executive_summary_v1.flag_v1 import home_executive_summary_v1_enabled

OWNERSHIP_V1 = {
    "home": "executive_summary",
    "decision_workspace": "decisions",
    "product_intelligence": "product_findings",
    "carts": "cart_operations",
    "communication": "communication",
    "settings": "configuration",
}

OBS_EMPTY_AR = "لا توجد أدلة كافية لإصدار ملاحظة مرتبطة بمنتج محدد."


def _slim_observation_finding(f: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "product_name_ar": str(f.get("product_name_ar") or "").strip(),
        "statement_ar": str(f.get("statement_ar") or "").strip(),
        "recommended_action_ar": str(f.get("recommended_action_ar") or "").strip(),
        "confidence_ar": str(f.get("confidence_ar") or "").strip(),
        "confidence_level": str(f.get("confidence_level") or "").strip(),
        "capability_id": str(f.get("capability_id") or "").strip(),
    }


def _observation_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    orv = summary.get("observation_reality_validation_v1") or {}
    findings_in = [
        f for f in list(orv.get("findings") or []) if isinstance(f, Mapping)
    ]
    # Entity-bound only — drop anything without a real product name
    findings = [
        _slim_observation_finding(f)
        for f in findings_in
        if str(f.get("product_name_ar") or "").strip()
    ]
    count = len(findings)
    if count == 0:
        return {
            "id": "observations",
            "title_ar": "ملاحظات المنتجات",
            "summary_ar": OBS_EMPTY_AR,
            "count": 0,
            "view_details_href": "#home-obs-details",
            "view_details_ar": "عرض التفاصيل",
            "empty": True,
            "empty_state_ar": OBS_EMPTY_AR,
            "findings_preview": [],
        }
    top = findings[0]
    summary_ar = f"{top['product_name_ar']}: {top['statement_ar']}"
    return {
        "id": "observations",
        "title_ar": "ملاحظات المنتجات",
        "summary_ar": summary_ar,
        "count": count,
        "view_details_href": "#home-obs-details",
        "view_details_ar": "عرض التفاصيل",
        "empty": False,
        "empty_state_ar": "",
        # Cap preview — details expand on demand in UI
        "findings_preview": findings[:2],
    }


def _decisions_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    meif = summary.get("merchant_experience_integration_v1") or {}
    pages = meif.get("pages") if isinstance(meif, Mapping) else {}
    home = (pages or {}).get("home") if isinstance(pages, Mapping) else {}
    sections = (home or {}).get("sections") if isinstance(home, Mapping) else {}
    decisions = list((sections or {}).get("merchant_decisions") or [])
    count = len(decisions)
    if count == 0:
        return {
            "id": "decisions",
            "title_ar": "قرارات اليوم",
            "summary_ar": "لا قرار قابل للتنفيذ اليوم — راجع مساحة القرار عند توفر أدلة.",
            "count": 0,
            "view_details_href": "#workspace",
            "view_details_ar": "عرض التفاصيل",
            "empty": True,
        }
    first = decisions[0] if isinstance(decisions[0], Mapping) else {}
    title = str(
        first.get("title_ar")
        or first.get("merchant_summary")
        or first.get("title")
        or "قرار جاهز للمراجعة"
    ).strip()
    return {
        "id": "decisions",
        "title_ar": "قرارات اليوم",
        "summary_ar": title,
        "count": count,
        "view_details_href": "#workspace",
        "view_details_ar": "عرض التفاصيل",
        "empty": False,
    }


def _health_section(summary: Mapping[str, Any]) -> dict[str, Any]:
    meif = summary.get("merchant_experience_integration_v1") or {}
    pages = meif.get("pages") if isinstance(meif, Mapping) else {}
    home = (pages or {}).get("home") if isinstance(pages, Mapping) else {}
    ops = (home or {}).get("operational_truth") if isinstance(home, Mapping) else {}
    ops = ops if isinstance(ops, Mapping) else {}
    watching = bool(ops.get("has_durable_carts")) or int(ops.get("abandoned_carts") or 0) > 0
    if watching:
        summary_ar = "CartFlow يراقب متجرك — ركّز على القرار الأهم اليوم."
    else:
        summary_ar = "لا نشاط كافٍ بعد لملخص تشغيلي — استمر في جمع الأدلة."
    return {
        "id": "health",
        "title_ar": "صحة العمل",
        "summary_ar": summary_ar,
        "count": None,
        "view_details_href": "#carts",
        "view_details_ar": "عرض التفاصيل",
        "empty": not watching,
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
        }
    src = summary if isinstance(summary, Mapping) else {}
    sections = [
        _health_section(src),
        _decisions_section(src),
        _observation_section(src),
    ]
    return {
        "ok": True,
        "enabled": True,
        "schema": "home_executive_summary_v1",
        "eyebrow_ar": "ملخص تنفيذي",
        "title_ar": "ماذا يجب أن تعرف الآن؟",
        "lede_ar": "ملخص سريع فقط — التفاصيل في صفحاتها.",
        "ownership": dict(OWNERSHIP_V1),
        "sections": sections,
        "product_intelligence": False,
        "ui": True,
    }


def slim_observation_package_for_home_v1(pkg: Mapping[str, Any] | None) -> dict[str, Any]:
    """Strip technical/detail fields from ORV before Home summary transport."""
    if not isinstance(pkg, Mapping):
        return {
            "ok": False,
            "enabled": False,
            "findings": [],
            "empty_state_ar": OBS_EMPTY_AR,
        }
    findings = []
    for f in list(pkg.get("findings") or []):
        if not isinstance(f, Mapping):
            continue
        name = str(f.get("product_name_ar") or "").strip()
        if not name:
            continue
        findings.append(
            {
                "product_name_ar": name,
                "statement_ar": str(f.get("statement_ar") or "").strip(),
                "recommended_action_ar": str(
                    f.get("recommended_action_ar") or ""
                ).strip(),
                "confidence_ar": str(f.get("confidence_ar") or "").strip(),
                "confidence_level": str(f.get("confidence_level") or "").strip(),
                "capability_id": str(f.get("capability_id") or "").strip(),
            }
        )
    out = {
        "ok": bool(pkg.get("ok")),
        "enabled": bool(pkg.get("enabled")),
        "schema": "observation_reality_validation_v1_home_slim",
        "store_slug": pkg.get("store_slug"),
        "findings": findings,
        "count": len(findings),
        "empty_state_ar": OBS_EMPTY_AR if not findings else "",
        "title_ar": "ملاحظات المنتجات",
        "temporary": True,
        "ui": True,
        "product_intelligence": False,
    }
    return out


def attach_home_executive_summary_to_summary_v1(
    summary: dict[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return summary
    if not home_executive_summary_v1_enabled(environ=environ):
        return summary
    try:
        # Slim ORV for Home transport (drop evidence_details / diagnostics)
        if isinstance(summary.get("observation_reality_validation_v1"), dict):
            summary["observation_reality_validation_v1"] = (
                slim_observation_package_for_home_v1(
                    summary["observation_reality_validation_v1"]
                )
            )
        pkg = build_home_executive_summary_v1(summary, environ=environ)
        summary["home_executive_summary_v1"] = pkg
        # Signal client to prefer executive summary painter
        summary["home_surface_mode"] = "executive_summary_v1"
    except Exception:  # noqa: BLE001
        summary["home_executive_summary_v1"] = {
            "ok": False,
            "enabled": True,
            "error": "attach_failed",
            "sections": [],
        }
    return summary


__all__ = [
    "OBS_EMPTY_AR",
    "OWNERSHIP_V1",
    "attach_home_executive_summary_to_summary_v1",
    "build_home_executive_summary_v1",
    "slim_observation_package_for_home_v1",
]
