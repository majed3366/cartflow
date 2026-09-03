# -*- coding: utf-8 -*-
"""Commercial Decision Library V1.1 — Cross-sell, Shipping, Merchandising (lab)."""
from __future__ import annotations

from typing import Any

CDL_VERSION_V1_1 = "commercial_decision_library_v1_1"

CDL_CROSS_SELL = "E_bundle_cross_sell"
CDL_SHIPPING = "B_high_interest_low_conversion"
CDL_MERCHANDISING = "A_discovery"
CDL_SCENARIO_IDS = frozenset({CDL_CROSS_SELL, CDL_SHIPPING, CDL_MERCHANDISING})

_GENERIC_BANNED = (
    "سوّق المنتج أكثر",
    "ضع Bundle",
    "حسّن الشحن",
    "أبرز المنتج",
    "قدم شحنًا مجانيًا",
    "قدّم شحنًا مجانيًا",
    "زد الظهور",
    "حسّن التسويق",
)


def _pack_cross_sell() -> dict[str, Any]:
    """POST_PURCHASE_OFFER — co-purchase + retention; no invented bundle discount."""
    return {
        "cdl_mission_key": "cross_sell_post_purchase",
        "relationship_class": "POST_PURCHASE_OFFER",
        "what_happens_ar": (
            "عملاء «ماكينة قهوة منزلية» يشترون «حليب لوز عضوي» معه في السلة كثيرًا، "
            "ويميلون لشرائه لاحقًا بمعدل أعلى من غير مشترين الآلة — العلاقة مثبتة في المحاكاة وليست تشابه تصنيف."
        ),
        "why_matters_commercially_ar": (
            "قيمة العميل يمكن زيادتها باقتراح مكمّل موجّه بدل خصم المنتجين معًا بلا دليل."
        ),
        "commercial_move_ar": (
            "اختبر عرض المنتج المكمل بعد شراء الآلة لمدة 14 يومًا (رسالة/اقتراح بعد الشراء) — "
            "بدون خصم حزمة مفتوح على المنتجين."
        ),
        "why_this_move_ar": (
            "العلاقة زمنية وبعد الشراء أقوى من حزمة خصم عامة؛ التجربة قابلة للعكس ولا تفترض رفع إيراد مسبق."
        ),
        "what_not_ar": (
            "لا تنشئ Bundle بخصم مخترع. لا توصية لأن المنتجين «متشابهان». لا توسّع العرض قبل قياس الشراء اللاحق."
        ),
        "measure_ar": (
            "معدل شراء المكمل خلال 14 يومًا بعد شراء الآلة، وإيراد الشريحة، مقارنة بالأساس قبل التجربة."
        ),
        "recheck_ar": (
            "بعد 14 يومًا. إذا اختفت العلاقة مع عيّنة أكبر أو لم يتجاوز الشراء اللاحق الأساس، أوقف التوصية."
        ),
        "falsifier_ar": (
            "إذا ضعفت علاقة الشراء المشترك/اللاحق مع عيّنة أكبر، لا توصي ببيع متقاطع."
        ),
        "priority_why_ar": (
            "فرصة قيمة عميل قابلة للقياس وأقل استعجالًا من عرض يضعف القيمة الآن أو احتكاك شحن يوقف الشراء بعد الاهتمام."
        ),
        "lens_conflict_ar": None,
        "lenses_internal": {
            "marketing": "تكامل سلوكي واضح بين منتجين.",
            "advertising": "ليس اكتساب زوار جدد.",
            "algorithmic": "تزامن سلة + ميل لاحق أعلى من الأساس.",
            "commercial_management": "اقتراح بعد الشراء أفضل من خصم حزمة بلا اقتصاد.",
            "merchandising": "اقتراح مكمّل لا إعادة ترتيب متجر كاملة.",
        },
        "commercial_objective": "IMPROVE_CUSTOMER_VALUE",
        "commercial_objective_ar": "رفع قيمة العميل",
        "commercial_idea_ar": (
            "عرض المكمل بعد شراء الآلة لمدة 14 يومًا — بلا خصم حزمة شامل."
        ),
        "home_why_ar": "عملاء الآلة يشترون المكمل معه/بعده أكثر من المعتاد.",
        "home_action_ar": "اختبار اقتراح المكمل بعد الشراء 14 يومًا.",
        "home_measure_ar": "شراء المكمل اللاحق وإيراد الشريحة مقابل الأساس.",
        "home_recheck_ar": "بعد 14 يومًا أو إذا اختفت العلاقة.",
    }


def _pack_shipping() -> dict[str, Any]:
    """Shipping cost friction — clarify cost, not free shipping."""
    return {
        "cdl_mission_key": "shipping_cost_friction",
        "friction_class": "shipping_price_friction",
        "what_happens_ar": (
            "لـ«طقم أدوات المطبخ الفاخر»: الاهتمام بالإضافة للسلة مرتفع، لكن التحويل إلى شراء ضعيف، "
            "والاعتراض المتكرر مرتبط بتكلفة الشحن أكثر من مدة التوصيل أو السعر وحده."
        ),
        "why_matters_commercially_ar": (
            "كل سلة مهتمة تُهجر بعد ظهور تكلفة الشحن تمثّل فقدان شراء محتمل دون إثبات أن الخصم هو الحل."
        ),
        "commercial_move_ar": (
            "لمدة 14 يومًا: وضّح تكلفة الشحن وخيارته قبل خطوة الدفع النهائية لهذا المنتج/التصنيف — "
            "بلا شحن مجاني شامل ودون تغيير شركة الشحن."
        ),
        "why_this_move_ar": (
            "الدليل يشير لعدم يقين/صدمة تكلفة أكثر من بطء التوصيل؛ توضيح الرسالة يعزل الفرضية قبل أي دعم تكلفة."
        ),
        "what_not_ar": (
            "لا تقدّم شحنًا مجانيًا كخطوة أولى. لا تخفّض سعر المنتج. لا تغيّر الناقل بلا دليل. "
            "لا تعامل كل هجر سلة كمشكلة شحن."
        ),
        "measure_ar": (
            "حصة تردد الشحن ضمن الهجر، التحويل إلى شراء بعد الإضافة، إيراد المنتج — مقارنة بأساس 30 يومًا."
        ),
        "recheck_ar": (
            "بعد 14 يومًا. إذا لم يكن التردد شحنًا بثبات، أو هيمن السعر/التوصيل، أوقف فرضية تكلفة الشحن."
        ),
        "falsifier_ar": (
            "إذا لم يكن الاعتراض مرتبطًا بالشحن بثبات عبر السلات، لا توصي بتغييرات شحن."
        ),
        "priority_why_ar": (
            "احتكاك يوقف الشراء بعد اهتمام مرتفع — أقرب لتسريب إيراد نشط من فرص حزمة أو إبراز فقط، "
            "لكنه يأتي بعد إيقاف عرض يضعف القيمة الآن إن وُجد."
        ),
        "lens_conflict_ar": (
            "التسويق قد يدفع لخصم لإنقاذ التحويل، لكن الدليل التجاري يرجّح توضيح الشحن قبل الخصم."
        ),
        "lenses_internal": {
            "marketing": "اهتمام قوي ثم انسحاب عند الشحن.",
            "advertising": "لا تزيد إنفاق الاكتساب قبل إصلاح الاحتكاك.",
            "algorithmic": "هيمنة تردد الشحن على السعر والتوصيل بحجم كافٍ.",
            "commercial_management": "توضيح تكلفة أرخص وأقل مخاطرة من شحن مجاني.",
            "merchandising": "ليس مشكلة موضع منتج.",
        },
        "commercial_objective": "INCREASE_CONVERSION",
        "commercial_objective_ar": "رفع التحويل إلى شراء",
        "commercial_idea_ar": (
            "توضيح تكلفة الشحن قبل الدفع لمدة 14 يومًا — بلا شحن مجاني شامل."
        ),
        "home_why_ar": "الاعتراض على تكلفة الشحن يتكرر بعد الاهتمام القوي.",
        "home_action_ar": "وضّح تكلفة الشحن قبل الدفع 14 يومًا.",
        "home_measure_ar": "حصة تردد الشحن، الشراء بعد الإضافة، وإيراد المنتج.",
        "home_recheck_ar": "بعد 14 يومًا أو إذا لم يعد التردد شحنًا.",
    }


def _pack_merchandising() -> dict[str, Any]:
    """Placement/discovery — ONE category placement experiment."""
    return {
        "cdl_mission_key": "merchandising_category_placement",
        "placement_class": "PLACEMENT_PROBLEM",
        "what_happens_ar": (
            "المشكلة ليست أن «زيت الأرغان المركّز» منتج ضعيف: من يراه يهتم ويشتري بمستوى جيد. "
            "المشكلة اكتشاف/موضع — عدد قليل يصل إليه مقارنة بمنتجات مشابهة في متجرك."
        ),
        "why_matters_commercially_ar": (
            "ضعف الموضع يترك تحويلًا جيدًا غير مستغل دون الحاجة لخفض السعر."
        ),
        "commercial_move_ar": (
            "ارفع ترتيب «زيت الأرغان المركّز» داخل صفحة تصنيف «عناية» إلى أعلى القائمة لمدة 14 يومًا — "
            "تجربة موضع واحدة فقط (بدون تغيير السعر أو عدة مواضع معًا)."
        ),
        "why_this_move_ar": (
            "موضع التصنيف يختبر فرضية الاكتشاف حيث يتصفح المشترون الفئة؛ محدد المكان والمدة ومعيار النجاح."
        ),
        "what_not_ar": (
            "لا تقل «زيادة الظهور» بلا موضع. لا تخفّض السعر. لا تغيّر الرئيسية والتصنيف والتوصيات دفعة واحدة."
        ),
        "measure_ar": (
            "نجاح التجربة: ارتفاع مشاهدات التصنيف للمنتج مع ثبات جودة الاهتمام والشراء وإيراد المنتج مقابل الأساس."
        ),
        "recheck_ar": (
            "بعد 14 يومًا. إذا ارتفع الظهور وضعف الاهتمام/الشراء، فرضية الموضع تضعف."
        ),
        "falsifier_ar": (
            "إذا زاد التعرض ولم تتحسن جودة الاهتمام أو الشراء، فرضية الموضع/الاكتشاف تضعف."
        ),
        "priority_why_ar": (
            "فرصة نمو قابلة للعكس عبر موضع واحد؛ أقل استعجالًا من تسريب شحن أو عرض يضعف القيمة."
        ),
        "lens_conflict_ar": None,
        "lenses_internal": {
            "marketing": "الإقناع عند الرؤية جيد — الحاجة وصول.",
            "advertising": "لا إعلان مدفوع مطلوب من هذا الدليل.",
            "algorithmic": "فجوة مشاهدات + تحويل جيد عند الرؤية.",
            "commercial_management": "تجربة ترتيب تصنيف منخفضة المخاطر.",
            "merchandising": "موضع التصنيف هو الرافعة المناسبة.",
        },
        "commercial_objective": "IMPROVE_DISCOVERY",
        "commercial_objective_ar": "تحسين الاكتشاف عبر الموضع",
        "commercial_idea_ar": (
            "رفع ترتيب الأرغان في تصنيف «عناية» لمدة 14 يومًا — موضع واحد."
        ),
        "home_why_ar": "من يراه يشتري جيدًا — الوصول عبر التصنيف ضعيف.",
        "home_action_ar": "أعلى في تصنيف عناية لمدة 14 يومًا.",
        "home_measure_ar": "مشاهدات، اهتمام، شراء، وإيراد المنتج.",
        "home_recheck_ar": "بعد 14 يومًا أو إذا ضعف الشراء مع ارتفاع الظهور.",
    }


def decision_packs_v1_1() -> dict[str, dict[str, Any]]:
    return {
        CDL_CROSS_SELL: _pack_cross_sell(),
        CDL_SHIPPING: _pack_shipping(),
        CDL_MERCHANDISING: _pack_merchandising(),
    }


def apply_cdl_to_mission_v1_1(m: dict[str, Any]) -> dict[str, Any]:
    sid = str(m.get("scenario_id") or "")
    if sid not in CDL_SCENARIO_IDS:
        return m
    pack = decision_packs_v1_1()[sid]
    out = dict(m)
    out["cdl_version"] = CDL_VERSION_V1_1
    out["cdl_refined"] = True
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
    if pack.get("relationship_class"):
        out["relationship_class"] = pack["relationship_class"]
    if pack.get("friction_class"):
        out["friction_class"] = pack["friction_class"]
    if pack.get("placement_class"):
        out["placement_class"] = pack["placement_class"]
    out["decision_contract_ar"] = {
        "ما الذي يحدث؟": pack["what_happens_ar"],
        "لماذا يهم؟": pack["why_matters_commercially_ar"],
        "الحركة التجارية": pack["commercial_move_ar"],
        "لماذا هذه الحركة؟": pack["why_this_move_ar"],
        "ما الذي لا ننصح به؟": pack["what_not_ar"],
        "ماذا سنقيس؟": pack["measure_ar"],
        "متى نعيد النظر؟": pack["recheck_ar"],
        "ما الذي يفنّد التوصية؟": pack["falsifier_ar"],
    }
    idea = pack["commercial_idea_ar"] + pack["commercial_move_ar"]
    out["generic_idea_flag"] = any(g in idea for g in _GENERIC_BANNED)
    # Natural titles
    if sid == CDL_CROSS_SELL:
        out["mission_ar"] = "عرض المكمل بعد شراء الآلة — بلا خصم حزمة"
        out["title_ar"] = out["mission_ar"]
    if sid == CDL_SHIPPING:
        out["mission_ar"] = "توضيح تكلفة الشحن — طقم أدوات المطبخ الفاخر"
        out["title_ar"] = out["mission_ar"]
    if sid == CDL_MERCHANDISING:
        out["mission_ar"] = "رفع ترتيب الأرغان في تصنيف عناية"
        out["title_ar"] = out["mission_ar"]
    return out


def apply_cdl_overlay_v1_1(missions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [apply_cdl_to_mission_v1_1(m) for m in missions]


def cdl_home_pick_v1_1(missions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Home: keep discount primary when present (active leakage),
    secondary = shipping + merchandising OR cross-sell — new families compete.
    """
    from services.commercial_decision_intelligence_v1 import CDI_DISCOUNT

    def _base(m: dict[str, Any]) -> bool:
        oid = str(m.get("opportunity_id") or "")
        if oid.endswith(("_measuring", "_active", "_fail")) or "measurement_won" in oid:
            return False
        return m.get("status") == "proposed"

    by = {m.get("scenario_id"): m for m in missions if _base(m)}
    primary = by.get(CDI_DISCOUNT) or by.get(CDL_SHIPPING)
    # New families compete as secondary: shipping + merchandising (cross-sell in missions list)
    secondary: list[dict[str, Any]] = []
    for sid in (CDL_SHIPPING, CDL_MERCHANDISING, CDL_CROSS_SELL):
        if primary and sid == primary.get("scenario_id"):
            continue
        if sid in by and len(secondary) < 2:
            secondary.append(by[sid])
    return {
        "question_ar": "أين توجد أهم فرصة إيراد الآن؟",
        "primary_mission": primary,
        "secondary_opportunities": secondary,
        "secondary_count": len(secondary),
        "priority_economics_ar": (
            "أولًا حماية قيمة المبيعات من خصم جارٍ إن وُجد؛ "
            "ثم احتكاك الشحن لأنه يوقف شراءً بعد اهتمام مرتفع؛ "
            "ثم موضع الأرغان في التصنيف؛ وفرص الحزمة/المكمل تُدار كمهمة قابلة للقياس أقل استعجالًا."
        ),
    }


def cdl_workspace_missions_v1_1(missions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for sid in (CDL_CROSS_SELL, CDL_SHIPPING, CDL_MERCHANDISING):
        for m in missions:
            oid = str(m.get("opportunity_id") or "")
            if m.get("scenario_id") != sid or m.get("status") != "proposed":
                continue
            if oid.endswith(("_measuring", "_active", "_fail")):
                continue
            out.append(m)
            break
    return out


def audit_cdl_v1_1(missions: list[dict[str, Any]]) -> dict[str, Any]:
    import re

    banned = ("ATC", "AOV", "CTR", "CVR", "ROAS", "CAC")
    generic = 0
    abbrev = 0
    falsifiers: set[str] = set()
    for m in missions:
        if not m.get("cdl_refined"):
            continue
        if m.get("generic_idea_flag"):
            generic += 1
        oid = str(m.get("opportunity_id") or "")
        if (
            m.get("falsifier_ar")
            and m.get("status") == "proposed"
            and not oid.endswith(("_measuring", "_active", "_fail"))
        ):
            falsifiers.add(str(m.get("scenario_id")))
        blob = " ".join(
            str(m.get(k) or "")
            for k in (
                "home_why_ar",
                "home_action_ar",
                "commercial_idea_ar",
                "commercial_move_ar",
                "what_happens_ar",
            )
        )
        for a in banned:
            abbrev += len(re.findall(rf"\b{a}\b", blob))
    return {
        "generic_advice_count": generic,
        "primary_tech_abbrev_count": abbrev,
        "falsifier_count": len(falsifiers),
    }


__all__ = [
    "CDL_CROSS_SELL",
    "CDL_MERCHANDISING",
    "CDL_SCENARIO_IDS",
    "CDL_SHIPPING",
    "CDL_VERSION_V1_1",
    "apply_cdl_overlay_v1_1",
    "audit_cdl_v1_1",
    "cdl_home_pick_v1_1",
    "cdl_workspace_missions_v1_1",
    "decision_packs_v1_1",
]
