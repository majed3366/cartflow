# -*- coding: utf-8 -*-
"""Merchant language: commercial first, numbers as evidence second."""
from __future__ import annotations

import re
from typing import Any

from services.revenue_intelligence_model_v1.contracts_v1 import BANNED_PRIMARY_ABBREVIATIONS

_REPLACEMENTS = (
    (r"\bATC rate\b", "معدل الإضافة للسلة"),
    (r"\bATC\b", "الإضافة للسلة"),
    (r"\bAOV\b", "متوسط قيمة الطلب"),
    (r"\bCTR\b", "معدل النقر"),
    (r"\bCVR\b", "معدل التحويل إلى شراء"),
    (r"\bROAS\b", "عائد الإنفاق الإعلاني"),
    (r"\bCAC\b", "تكلفة اكتساب العميل"),
)


def humanize_merchant_text_ar(text: str) -> str:
    s = str(text or "")
    for pat, rep in _REPLACEMENTS:
        s = re.sub(pat, rep, s)
    return s


def humanize_evidence_list_ar(items: list[Any] | None) -> list[str]:
    out: list[str] = []
    for it in items or []:
        t = humanize_merchant_text_ar(str(it))
        t = t.replace("معدل إضافة للسلة", "من يشاهد يضيف للسلة بمعدل")
        out.append(t)
    return out


def count_banned_abbreviations(*texts: str) -> int:
    n = 0
    for t in texts:
        s = str(t or "")
        for abbr in BANNED_PRIMARY_ABBREVIATIONS:
            n += len(re.findall(rf"\b{abbr}\b", s))
    return n


def commercial_state_for_product_v1(row: dict[str, Any]) -> dict[str, Any]:
    roles = row.get("scenario_roles") or []
    views = int((row.get("discovery") or {}).get("views") or 0)
    atc_rate = float((row.get("interest") or {}).get("atc_rate") or 0)
    purch = float((row.get("conversion") or {}).get("purchase_rate_of_atc") or 0)
    hes = row.get("hesitation") or {}
    top = hes.get("top") or "none"
    hes_ar = {
        "price": "سعر",
        "shipping": "شحن",
        "delivery": "توصيل",
        "other": "أخرى",
        "none": "غير واضح",
    }.get(str(top), str(top))

    discovery = "ضعيف" if views < 800 else "متوسط" if views < 2000 else "قوي"
    interest = "قوي" if atc_rate >= 0.20 else "متوسط" if atc_rate >= 0.12 else "ضعيف"
    conversion = "جيد" if purch >= 0.30 else "متوسط" if purch >= 0.18 else "ضعيف"
    revenue = row.get("revenue_contribution") or {}
    rev_val = float(revenue.get("revenue") or 0)
    revenue_state = "ملموس" if rev_val >= 20000 else "محدود" if rev_val >= 5000 else "ضعيف"

    opportunity = row.get("commercial_answer_ar") or ""
    if "H_insufficient_evidence" in roles:
        opportunity = "الدليل غير كافٍ"
        discovery, interest, conversion = "غير كافٍ", "غير كافٍ", "غير كافٍ"

    return {
        "product_id": row.get("product_id"),
        "name_ar": row.get("name_ar"),
        "category": row.get("category"),
        "states": {
            "الاكتشاف": discovery,
            "الاهتمام": interest,
            "التحويل": conversion,
            "الإيراد": revenue_state,
            "الاحتكاك": hes_ar,
            "الفرصة الحالية": opportunity,
        },
        "supporting_evidence": {
            "مشاهدات": views,
            "إضافات_للسلة": (row.get("interest") or {}).get("atc"),
            "مشتريات": (row.get("conversion") or {}).get("purchases"),
            "إيراد_ر_س": revenue.get("revenue"),
            "متوسط_قيمة_الطلب": revenue.get("aov"),
            "أفضل_قناة_جودة": row.get("channel_quality_best"),
            "علاقة_احتفاظ": bool(row.get("retention_relationship")),
        },
        "commercial_question_ar": row.get("commercial_question_ar"),
    }


def apply_merchant_language_to_mission_v1(m: dict[str, Any]) -> dict[str, Any]:
    out = dict(m)
    for key in (
        "mission_ar",
        "title_ar",
        "why_matters_ar",
        "diagnosis_ar",
        "diagnosis_short_ar",
        "commercial_opportunity_ar",
        "commercial_idea_ar",
        "why_idea_fits_ar",
        "action_ar",
        "measure_ar",
        "recheck_ar",
        "what_not_to_do_ar",
        "why_prioritized_ar",
        "home_why_ar",
        "home_action_ar",
        "home_measure_ar",
        "home_recheck_ar",
        "why_now_short_ar",
        "lens_conflict_ar",
    ):
        if key in out and out[key]:
            out[key] = humanize_merchant_text_ar(str(out[key]))
    out["evidence_ar"] = humanize_evidence_list_ar(out.get("evidence_ar"))
    alts = out.get("alternatives_ar") or []
    out["alternatives_ar"] = [humanize_merchant_text_ar(a) for a in alts]
    sid = str(out.get("scenario_id") or "")
    if sid == "E_bundle_cross_sell":
        out["mission_ar"] = "اقتراح منتج مكمل مع مشتريات المنتج الأساسي"
        out["title_ar"] = out["mission_ar"]
    if sid == "G_retention":
        out["mission_ar"] = "عرض المكمل لعملاء اشتروا الأساسي"
        out["title_ar"] = out["mission_ar"]
    return out


__all__ = [
    "apply_merchant_language_to_mission_v1",
    "commercial_state_for_product_v1",
    "count_banned_abbreviations",
    "humanize_evidence_list_ar",
    "humanize_merchant_text_ar",
]
