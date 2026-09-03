# -*- coding: utf-8 -*-
"""Commercial Decision Intelligence V1 — refine three missions only (lab)."""
from __future__ import annotations

from typing import Any

CDI_VERSION_V1 = "commercial_decision_intelligence_v1"

# Scenario IDs for the three refined missions
CDI_DISCOUNT = "D_discount_destroys_value"
CDI_DISCOVERY = "A_discovery"
CDI_CHANNEL = "F_channel_quality"
CDI_SCENARIO_IDS = frozenset({CDI_DISCOUNT, CDI_DISCOVERY, CDI_CHANNEL})

_GENERIC_BANNED = (
    "حسّن التسويق",
    "زد الظهور",
    "استخدم TikTok",
    "قدّم خصمًا",
    "قدم خصمًا",
    "حسّن صفحة المنتج",
    "increase exposure",
    "run ads",
)


def _pack_discount() -> dict[str, Any]:
    """
    Chosen idea: stop blanket promo now; if pressure returns, redesign as
    short hesitant-only offer — not open-ended discount.
    Sim-only contribution; no production margin claim.
    """
    return {
        "cdi_mission_key": "discount_protect",
        "what_happens_ar": (
            "عرض خصم شامل على «عطر مسائي محدود» يرفع إتمام الشراء، "
            "لكن المساهمة التجارية في بيانات المحاكاة لا تتحسن بما يكفي (تكلفة المحاكاة فقط — ليست هامش إنتاج)."
        ),
        "why_matters_commercially_ar": (
            "هذه حركة تجارية جارية الآن: الاستمرار يبادل قيمة الطلب بتحويل أعلى دون تحسّن اقتصادي كافٍ في المحاكاة."
        ),
        "commercial_move_ar": (
            "أوقف الخصم الشامل فورًا. إن عاد ضغط التحويل خلال أسبوعين، اختبر عرضًا ضيقًا لمدة 7 أيام "
            "للمترددين فقط (لا خصمًا مفتوحًا للجميع)."
        ),
        "why_this_move_ar": (
            "الإيقاف يوقف الاستنزاف الحالي. إعادة التصميم المشروط أفضل من «إيقاف فقط» لأنها تحفظ مسار تعلم محدود "
            "دون إعادة الخصم الشامل، وأفضل من توسيع العرض لأن الاقتصاد المحاكى لا يدعم التوسع."
        ),
        "what_not_ar": (
            "لا تحتفل برفع التحويل وحده. لا تدّعِ ضرر «الهامش» كحقيقة إنتاج. "
            "لا تستبدل الخصم بخصم أعمق أو أطول بلا قياس."
        ),
        "measure_ar": (
            "بعد الإيقاف: التحويل إلى شراء، إيراد المنتج، ومتوسط قيمة الطلب. "
            "المساهمة المحاكاة تُعرض كدليل مختبر فقط إن وُجدت."
        ),
        "recheck_ar": (
            "بعد 14 يومًا. أعد النظر إذا انهار الطلب بالسعر الكامل بحدة، "
            "أو إذا بقي الإيراد أضعف دون تحسّن جودة الشراء."
        ),
        "falsifier_ar": (
            "إذا انخفض الطلب بالسعر الكامل بحدة بعد الإيقاف مع بقاء الإيراد أسوأ، "
            "فرضية «الخصم الشامل مدمّر للقيمة» تضعف — أعد تصميم أهلية العرض لا التوسع الأعمى."
        ),
        "priority_why_ar": (
            "هذه المهمة أولًا لأنها تتعلق بحركة تجارية جارية قد تستنزف قيمة المبيعات الآن، "
            "بينما فرص الاكتشاف أو اختبار القناة يمكن اختبارها لاحقًا بأثر أقل استعجالًا."
        ),
        "lens_conflict_ar": (
            "التسويق يدعم استمرار العرض لأن التحويل ارتفع، لكن الأثر التجاري في المحاكاة لا يدعم التوسع به."
        ),
        "lenses_internal": {
            "marketing": "التحويل أعلى أثناء العرض — السلوك يشجع الاستمرار.",
            "advertising": "لا قرار اكتساب هنا.",
            "algorithmic": "مقارنة أيام عرض/غير عرض كافية في المحاكاة؛ التكلفة محاكاة فقط.",
            "commercial_management": "مساهمة محاكاة أسوأ + عرض جارٍ = أوقف ثم أعد التصميم بشروط.",
        },
        "commercial_objective": "PROTECT_REVENUE",
        "commercial_objective_ar": "حماية قيمة المبيعات",
        "commercial_idea_ar": (
            "أوقف الخصم الشامل الآن؛ وإن لزم لاحقًا، استبدله بعرض ضيق قصير للمترددين فقط."
        ),
        "home_why_ar": (
            "الخصم يرفع التحويل، لكن مساهمته التجارية لا تتحسن بما يكفي وفق بيانات المحاكاة."
        ),
        "home_action_ar": "أوقف الخصم الشامل الآن — لا توسّعه.",
        "home_measure_ar": "إيراد المنتج والتحويل إلى شراء ومتوسط قيمة الطلب بعد الإيقاف.",
        "home_recheck_ar": "بعد 14 يومًا، أو إذا انهار الطلب بالسعر الكامل.",
    }


def _pack_discovery() -> dict[str, Any]:
    return {
        "cdi_mission_key": "discovery_merchandising",
        "what_happens_ar": (
            "المشكلة ليست أن «زيت الأرغان المركّز» لا يقنع من يراه؛ "
            "المشكلة أن عددًا قليلًا يصل إليه مقارنة بمنتجات مشابهة في متجرك."
        ),
        "why_matters_commercially_ar": (
            "من يشاهد يهتم ويشتري بمستوى جيد — ضعف الوصول يترك إيرادًا ممكنًا على الطاولة دون مشكلة سعر ظاهرة."
        ),
        "commercial_move_ar": (
            "ارفع ظهور المنتج في الصفحة الرئيسية (موضع ثابت واحد) لمدة 14 يومًا — تجربة إبراز واحدة فقط."
        ),
        "why_this_move_ar": (
            "إبراز الرئيسية يختبر فرضية الوصول مباشرة، منخفض المخاطر وقابل للعكس، "
            "ولا يفترض قناة إعلان ولا يلمس السعر. أفضل من «زد الظهور» العام لأنه موضعه ومدته محددان."
        ),
        "what_not_ar": (
            "لا تخفّض السعر. لا تقفز إلى إعلان مدفوع بلا دليل قناة لهذا المنتج. "
            "لا تغيّر عدة مواضع مرة واحدة فتضيع عزو النتيجة."
        ),
        "measure_ar": (
            "نراقب: مشاهدات مؤهلة، من يضيف للسلة، التحويل إلى شراء، وإيراد المنتج مقابل أساس الـ30 يومًا."
        ),
        "recheck_ar": (
            "بعد 14 يومًا، أو عند ارتفاع المشاهدات بنحو 40%. "
            "إذا ارتفعت المشاهدات وضعف الاهتمام أو الشراء، فرضية التوزيع تضعف."
        ),
        "falsifier_ar": (
            "إذا زادت المشاهدات وانخفضت جودة الاهتمام/الشراء، فالجمهور الجديد أضعف — "
            "ليست مشكلة نقص وصول فقط."
        ),
        "priority_why_ar": (
            "فرصة نمو قابلة للقياس وأقل استعجالًا من عرض جارٍ قد يضعف القيمة الآن؛ "
            "تأتي بعد حماية قيمة المبيعات وقبل تجارب اكتساب بلا ميزانية مؤكدة."
        ),
        "lens_conflict_ar": None,
        "lenses_internal": {
            "marketing": "من يرى يقتنع — الحاجة وصول مؤهل.",
            "advertising": "لا قناة مدفوعة مبررة من دليل هذا المنتج بعد.",
            "algorithmic": "فجوة مشاهدات مقابل أقران + اهتمام/شراء قويين عند الرؤية.",
            "commercial_management": "تجربة موضع واحد لمدة محدودة أفضل جهد/أثر.",
        },
        "commercial_objective": "IMPROVE_DISCOVERY",
        "commercial_objective_ar": "تحسين الاكتشاف",
        "commercial_idea_ar": (
            "ارفع ظهور «زيت الأرغان المركّز» في موضع واحد بالصفحة الرئيسية لمدة 14 يومًا."
        ),
        "home_why_ar": "من يصل يشتري جيدًا — لكن قليلين يصلون.",
        "home_action_ar": "إبراز في الرئيسية 14 يومًا (موضع واحد).",
        "home_measure_ar": "المشاهدات، الإضافة للسلة، الشراء، وإيراد المنتج.",
        "home_recheck_ar": "بعد 14 يومًا أو +40% مشاهدات مع ثبات الجودة.",
    }


def _pack_channel() -> dict[str, Any]:
    return {
        "cdi_mission_key": "channel_tiktok_vs_google",
        "what_happens_ar": (
            "في بيانات «حقيبة يومية خفيفة» داخل متجرك، الزيارات من TikTok تبدو أعلى جودة من Google: "
            "إضافة للسلة أعلى، وتحويل إلى شراء أوضح، بينما عينة Google أضعف في الشراء ضمن المحاكاة."
        ),
        "why_matters_commercially_ar": (
            "جودة الزيارة تغيّر عائد أي جهد اكتساب لنفس المنتج — الحجم وحده مضلّل."
        ),
        "commercial_move_ar": (
            "اختبر فرضية لمدة 14 يومًا: حصة اكتساب محدودة موجّهة لـTikTok لهذا المنتج فقط، "
            "مع مجموعة مقارنة على البحث/Google دون تغيير بقية القنوات."
        ),
        "why_this_move_ar": (
            "الفرق مقيس على هذا المنتج (زيارات، اهتمام، شراء، جودة طلب) وليس شعار فئة. "
            "التجربة محدودة الزمن والنطاق — ليست «استخدم TikTok»."
        ),
        "what_not_ar": (
            "لا تعميم «TikTok أفضل». لا اختراع ميزانية أو عائد إنفاق أو تكلفة اكتساب. "
            "لا توسيع القناة إذا ارتفع الحجم وضعف الشراء."
        ),
        "measure_ar": (
            "لكل قناة خلال الاختبار: جودة الزيارات (إضافة للسلة)، التحويل إلى شراء، "
            "متوسط قيمة الطلب، وإيراد المنتج من القناة."
        ),
        "recheck_ar": (
            "بعد 14 يومًا. أوقف التوسع فورًا إذا زاد حجم TikTok وضعفت جودة الشراء، "
            "أو إذا صغرت عينة أي قناة عن الحد الذي يمنع المقارنة."
        ),
        "falsifier_ar": (
            "إذا ارتفع حجم TikTok وانخفضت جودة الشراء/قيمة الطلب، لا توسّع القناة."
        ),
        "priority_why_ar": (
            "مهمة اختبار اكتساب مفيدة لكنها أقل استعجالًا من إيقاف عرض يضعف القيمة الآن، "
            "وأقل مباشرة من إبراز منتج يثبت جودة الشراء عند الوصول."
        ),
        "lens_conflict_ar": None,
        "lenses_internal": {
            "marketing": "جودة زيارة TikTok أعلى لهذا المنتج في العينة.",
            "advertising": "يبرّر اختبار اكتساب محدود لا حكمًا عامًا.",
            "algorithmic": "حجم كافٍ للمقارنة في المحاكاة؛ لا ميزانية/ROAS في الحقيقة.",
            "commercial_management": "اختبار reverseable أفضل من إعادة تخصيص دائمة.",
        },
        "commercial_objective": "TEST_ACQUISITION",
        "commercial_objective_ar": "اختبار اكتساب",
        "commercial_idea_ar": (
            "اختبار 14 يومًا: اكتساب محدود عبر TikTok لـ«حقيبة يومية خفيفة» مقابل مقارنة Google."
        ),
        "home_why_ar": (
            "في بيانات هذا المنتج داخل متجرك، زيارات TikTok أجود من Google وفق الاهتمام والشراء."
        ),
        "home_action_ar": "اختبار اكتساب محدود 14 يومًا — TikTok مقابل Google لهذا المنتج.",
        "home_measure_ar": "لكل قناة: الإضافة للسلة، الشراء، متوسط قيمة الطلب، والإيراد.",
        "home_recheck_ar": "بعد 14 يومًا أو إذا ضعف الشراء مع ارتفاع الحجم.",
    }


def decision_packs_v1() -> dict[str, dict[str, Any]]:
    return {
        CDI_DISCOUNT: _pack_discount(),
        CDI_DISCOVERY: _pack_discovery(),
        CDI_CHANNEL: _pack_channel(),
    }


def apply_cdi_to_mission_v1(m: dict[str, Any]) -> dict[str, Any]:
    sid = str(m.get("scenario_id") or "")
    if sid not in CDI_SCENARIO_IDS:
        return m
    # Only refine primary proposed / measuring clones of these scenarios — not won demos unless same sid
    pack = decision_packs_v1()[sid]
    out = dict(m)
    out["cdi_version"] = CDI_VERSION_V1
    out["cdi_refined"] = True
    out["what_happens_ar"] = pack["what_happens_ar"]
    out["why_matters_commercially_ar"] = pack["why_matters_commercially_ar"]
    out["commercial_move_ar"] = pack["commercial_move_ar"]
    out["why_this_move_ar"] = pack["why_this_move_ar"]
    out["what_not_to_do_ar"] = pack["what_not_ar"]
    out["measure_ar"] = pack["measure_ar"]
    out["recheck_ar"] = pack["recheck_ar"]
    out["falsifier_ar"] = pack["falsifier_ar"]
    out["why_prioritized_ar"] = pack["priority_why_ar"]
    out["why_now_short_ar"] = pack["priority_why_ar"]
    out["lens_conflict_ar"] = pack["lens_conflict_ar"]
    out["lenses_internal"] = pack["lenses_internal"]
    out["commercial_objective"] = pack["commercial_objective"]
    out["commercial_objective_ar"] = pack["commercial_objective_ar"]
    out["commercial_idea_ar"] = pack["commercial_idea_ar"]
    out["commercial_opportunity_ar"] = pack["what_happens_ar"]
    out["why_idea_fits_ar"] = pack["why_this_move_ar"]
    out["action_ar"] = pack["commercial_move_ar"]
    out["diagnosis_short_ar"] = pack["what_happens_ar"]
    out["home_why_ar"] = pack["home_why_ar"]
    out["home_action_ar"] = pack["home_action_ar"]
    out["home_measure_ar"] = pack["home_measure_ar"]
    out["home_recheck_ar"] = pack["home_recheck_ar"]
    # Decision contract block for Workspace
    out["decision_contract_ar"] = {
        "ما الذي يحدث؟": pack["what_happens_ar"],
        "لماذا يهم تجاريًا؟": pack["why_matters_commercially_ar"],
        "ما الحركة التجارية المقترحة؟": pack["commercial_move_ar"],
        "لماذا هذه الحركة بالذات؟": pack["why_this_move_ar"],
        "ما الذي لا ننصح به؟": pack["what_not_ar"],
        "ماذا سنقيس؟": pack["measure_ar"],
        "متى نغيّر رأينا؟": pack["recheck_ar"],
        "ما الذي يفنّد التوصية؟": pack["falsifier_ar"],
    }
    # Generic check
    idea = pack["commercial_idea_ar"] + pack["commercial_move_ar"]
    out["generic_idea_flag"] = any(g.lower() in idea.lower() for g in _GENERIC_BANNED)
    return out


def apply_cdi_overlay_v1(missions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [apply_cdi_to_mission_v1(m) for m in missions]


def cdi_home_pick_v1(missions: list[dict[str, Any]]) -> dict[str, Any]:
    """Home: primary discount, secondary discovery + channel (the three CDI missions)."""

    def _base(m: dict[str, Any]) -> bool:
        oid = str(m.get("opportunity_id") or "")
        if oid.endswith(("_measuring", "_active", "_fail")) or "measurement_won" in oid:
            return False
        return m.get("status") == "proposed"

    by = {m.get("scenario_id"): m for m in missions if _base(m) and m.get("scenario_id") in CDI_SCENARIO_IDS}
    primary = by.get(CDI_DISCOUNT)
    secondary = [m for sid in (CDI_DISCOVERY, CDI_CHANNEL) if (m := by.get(sid))]
    return {
        "question_ar": "أين توجد أهم فرصة إيراد الآن؟",
        "primary_mission": primary,
        "secondary_opportunities": secondary[:2],
        "secondary_count": min(2, len(secondary)),
        "priority_economics_ar": (
            "أولًا إيقاف/إعادة تصميم الخصم لأنه عرض جارٍ قد يضعف القيمة الآن؛ "
            "ثم اكتشاف الأرغان كتجربة إبراز قابلة للعكس؛ "
            "ثم اختبار TikTok مقابل Google كقرار اكتساب محدود بلا ميزانية مخترعة."
        ),
    }


def cdi_workspace_missions_v1(missions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ordered Workspace depth for the three CDI missions."""
    out: list[dict[str, Any]] = []
    for sid in (CDI_DISCOUNT, CDI_DISCOVERY, CDI_CHANNEL):
        for m in missions:
            oid = str(m.get("opportunity_id") or "")
            if m.get("scenario_id") != sid:
                continue
            if m.get("status") != "proposed":
                continue
            if oid.endswith(("_measuring", "_active", "_fail")):
                continue
            out.append(m)
            break
    return out


def audit_cdi_generic_and_abbrev(missions: list[dict[str, Any]]) -> dict[str, Any]:
    import re

    banned = ("ATC", "AOV", "CTR", "CVR", "ROAS", "CAC")
    generic = 0
    abbrev = 0
    falsifier_scenarios: set[str] = set()
    for m in missions:
        if not m.get("cdi_refined"):
            continue
        if m.get("generic_idea_flag"):
            generic += 1
        if m.get("falsifier_ar") and m.get("status") == "proposed":
            oid = str(m.get("opportunity_id") or "")
            if oid.endswith(("_measuring", "_active", "_fail")):
                continue
            falsifier_scenarios.add(str(m.get("scenario_id") or ""))
        texts = [
            m.get("home_why_ar"),
            m.get("home_action_ar"),
            m.get("commercial_idea_ar"),
            m.get("commercial_move_ar"),
            m.get("what_happens_ar"),
            m.get("why_prioritized_ar"),
        ]
        blob = " ".join(str(t or "") for t in texts)
        for a in banned:
            abbrev += len(re.findall(rf"\b{a}\b", blob))
    return {
        "generic_advice_count": generic,
        "primary_tech_abbrev_count": abbrev,
        "falsifier_count": len(falsifier_scenarios),
    }


__all__ = [
    "CDI_CHANNEL",
    "CDI_DISCOVERY",
    "CDI_DISCOUNT",
    "CDI_SCENARIO_IDS",
    "CDI_VERSION_V1",
    "apply_cdi_overlay_v1",
    "audit_cdi_generic_and_abbrev",
    "cdi_home_pick_v1",
    "cdi_workspace_missions_v1",
    "decision_packs_v1",
]
