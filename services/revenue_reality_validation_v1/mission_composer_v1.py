# -*- coding: utf-8 -*-
"""Transform qualified opportunities into Revenue Missions."""
from __future__ import annotations

from typing import Any

from services.revenue_reality_validation_v1.contracts_v1 import (
    MISSION_STATUS_INSUFFICIENT,
    empty_mission_v1,
    validate_mission_v1,
)

_MISSION_TITLES = {
    "A_discovery": "زيادة اكتشاف المنتج",
    "B_high_interest_low_conversion": "معالجة احتكاك الشحن بعد الاهتمام",
    "C_price_sensitive": "اختبار عرض محدود للمنتج",
    "D_discount_destroys_value": "إيقاف أو إعادة تصميم الخصم",
    "E_bundle_cross_sell": "فرصة حزمة / بيع متقاطع",
    "F_channel_quality": "اختبار جودة قناة اكتساب",
    "G_retention": "احتفاظ / Cross-sell لعملاء حاليين",
    "H_insufficient_evidence": "دليل غير كافٍ — لا توصية",
}


def compose_missions_v1(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missions: list[dict[str, Any]] = []
    for o in opportunities:
        if not isinstance(o, dict):
            continue
        sid = str(o.get("scenario_id") or "")
        scope = o.get("scope") or {}
        name = scope.get("name_ar") or scope.get("id") or ""
        title_base = _MISSION_TITLES.get(sid, "مهمة إيراد")
        title = f"{title_base}" + (f" — {name}" if name and sid != "E_bundle_cross_sell" else "")
        if sid == "E_bundle_cross_sell":
            title = "Cross-sell B لعملاء / سلات A"
        if sid == "G_retention":
            title = "Cross-sell B لعملاء A"
        if sid == "F_channel_quality":
            title = f"اختبار TikTok مقابل Google — {name}" if name else title_base

        m = empty_mission_v1()
        m.update(
            {
                "ok": True,
                "mission_id": f"mission_{o.get('opportunity_id')}",
                "opportunity_id": o.get("opportunity_id"),
                "title_ar": title,
                "mission_ar": title,
                "why_matters_ar": o.get("why") or o.get("commercial_opportunity") or "",
                "evidence_ar": list(o.get("evidence") or []),
                "diagnosis_ar": o.get("diagnosis") or "",
                "commercial_idea_ar": o.get("commercial_opportunity") or "",
                "action_ar": o.get("recommended_action") or "",
                "measure_ar": o.get("measurement_plan") or "",
                "recheck_ar": o.get("recheck_condition") or "",
                "status": o.get("status") or MISSION_STATUS_INSUFFICIENT,
                "confidence": o.get("confidence") or "insufficient",
                "scenario_id": sid,
                "what_not_to_do_ar": _what_not_to_do(sid, o),
                "alternatives_ar": _alternatives(sid),
                "falsifiers": list(o.get("falsifiers") or []),
                "scope": scope,
                "simulation_only": True,
            }
        )
        errs = validate_mission_v1(m)
        # Insufficient missions still valid if they explain refusal
        if sid == "H_insufficient_evidence":
            m["ok"] = True
            m["validation_errors"] = []
        else:
            m["ok"] = not errs
            m["validation_errors"] = errs
        missions.append(m)
    return missions


def _what_not_to_do(sid: str, o: dict[str, Any]) -> str:
    mapping = {
        "A_discovery": "لا تفترض قناة إعلان محددة؛ لا تخفّض السعر كخطوة أولى من مشاهدات منخفضة وحدها.",
        "B_high_interest_low_conversion": "لا تقدّم خصمًا فوريًا من ATC مرتفع؛ لا تتجاهل دليل الشحن.",
        "C_price_sensitive": "لا تخترع uplift متوقع؛ لا تقارن بسعر سوق خارجي بلا مصدر محكوم.",
        "D_discount_destroys_value": "لا تحتفل برفع التحويل مع تجاهل اقتصاد الإيراد/المساهمة.",
        "E_bundle_cross_sell": "لا تقترح حزمة من تشابه التصنيف وحده بلا علاقة شراء.",
        "F_channel_quality": "لا توصية عامة «شغّل TikTok»؛ لا تعيد تخصيص إنفاقًا بعينة صغيرة.",
        "G_retention": "لا تعامل الشريحة كاكتساب جديد.",
        "H_insufficient_evidence": "لا إجراء تجاري حتى تكتمل العتبات.",
    }
    return mapping.get(sid, "لا توصية بلا دليل؛ لا ادّعاء إيراد بلا قياس.")


def _alternatives(sid: str) -> list[str]:
    mapping = {
        "A_discovery": [
            "جودة زيارات ضعيفة إذا ارتفعت المشاهدات وانخفض ATC",
            "مشكلة عرض نادرة إذا بقي التحويل ضعيفًا بعد زيادة الاكتشاف",
        ],
        "B_high_interest_low_conversion": [
            "حساسية سعر إذا هيمن تردد السعر",
            "مشكلة ثقة منتج إذا ظهرت إشارات جودة/مراجعات لاحقًا",
            "دليل غير كافٍ إذا كانت ترددات الشحن ضعيفة",
        ],
        "C_price_sensitive": [
            "احتكاك شحن إذا انقلبت هيمنة التردد",
            "مشكلة ثقة إذا بقي التحويل ضعيفًا بعد تجربة العرض",
        ],
        "D_discount_destroys_value": [
            "عرض بهيكل مختلف قد يحافظ على المساهمة",
            "بدون تكلفة: لا حكم ربح — فجوة هامش",
        ],
        "E_bundle_cross_sell": ["تزامن موسمي عابر", "عينة صغيرة مضللة"],
        "F_channel_quality": ["تغيّر جودة القناة بمرور الوقت", "عينة غير متوازنة"],
        "G_retention": ["شراء لاحق عضوي بلا حاجة لحملة", "تشبع الشريحة"],
        "H_insufficient_evidence": ["أي فرضية تجارية مبكرة"],
    }
    return mapping.get(sid, [])


def primary_home_mission_v1(missions: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Executive Home: one primary mission needing decision."""
    proposed = [
        m
        for m in missions
        if m.get("status") == "proposed"
        and m.get("scenario_id") != "H_insufficient_evidence"
        and m.get("ok")
    ]
    # Prefer discovery as the clearest "revenue opportunity now"
    for prefer in ("A_discovery", "B_high_interest_low_conversion", "C_price_sensitive"):
        for m in proposed:
            if m.get("scenario_id") == prefer and not str(m.get("opportunity_id") or "").endswith(
                ("_measuring", "_fail")
            ):
                return m
    return proposed[0] if proposed else None


def missions_by_bucket_v1(missions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets = {
        "needs_decision": [],
        "active": [],
        "measuring": [],
        "completed": [],
        "insufficient": [],
    }
    for m in missions:
        st = m.get("status")
        if st == "proposed":
            buckets["needs_decision"].append(m)
        elif st == "active":
            buckets["active"].append(m)
        elif st == "measuring":
            buckets["measuring"].append(m)
        elif st in ("won", "lost", "inconclusive"):
            buckets["completed"].append(m)
        elif st == "insufficient_evidence":
            buckets["insufficient"].append(m)
    return buckets


__all__ = [
    "compose_missions_v1",
    "missions_by_bucket_v1",
    "primary_home_mission_v1",
]
