# -*- coding: utf-8 -*-
"""Governed commercial imagination — evidence-grounded ideas only."""
from __future__ import annotations

from typing import Any

from services.revenue_intelligence_model_v1.contracts_v1 import (
    OBJECTIVE_LABEL_AR,
    OBJ_GROW_REVENUE,
    OBJ_IMPROVE_CUSTOMER_VALUE,
    OBJ_IMPROVE_DISCOVERY,
    OBJ_INCREASE_CONVERSION,
    OBJ_PROTECT_MARGIN,
    OBJ_PROTECT_REVENUE,
    OBJ_TEST_ACQUISITION,
)

_GENERIC_BANNED = (
    "زد التعرض",
    "حسّن التسويق",
    "شغّل إعلانات",
    "زيادة الوعي",
    "increase exposure",
    "run ads",
)


def _objective_for(sid: str) -> tuple[str, str]:
    mapping = {
        "A_discovery": (OBJ_IMPROVE_DISCOVERY, OBJECTIVE_LABEL_AR[OBJ_IMPROVE_DISCOVERY]),
        "B_high_interest_low_conversion": (
            OBJ_INCREASE_CONVERSION,
            OBJECTIVE_LABEL_AR[OBJ_INCREASE_CONVERSION],
        ),
        "C_price_sensitive": (OBJ_INCREASE_CONVERSION, OBJECTIVE_LABEL_AR[OBJ_INCREASE_CONVERSION]),
        "D_discount_destroys_value": (OBJ_PROTECT_MARGIN, OBJECTIVE_LABEL_AR[OBJ_PROTECT_MARGIN]),
        "E_bundle_cross_sell": (
            OBJ_IMPROVE_CUSTOMER_VALUE,
            OBJECTIVE_LABEL_AR[OBJ_IMPROVE_CUSTOMER_VALUE],
        ),
        "F_channel_quality": (OBJ_TEST_ACQUISITION, OBJECTIVE_LABEL_AR[OBJ_TEST_ACQUISITION]),
        "G_retention": (
            OBJ_IMPROVE_CUSTOMER_VALUE,
            OBJECTIVE_LABEL_AR[OBJ_IMPROVE_CUSTOMER_VALUE],
        ),
        "H_insufficient_evidence": ("", ""),
    }
    # Secondary grow/protect tags
    grow = {
        "A_discovery": OBJ_GROW_REVENUE,
        "C_price_sensitive": OBJ_GROW_REVENUE,
        "D_discount_destroys_value": OBJ_PROTECT_REVENUE,
    }
    primary = mapping.get(sid, ("", ""))
    return primary[0], primary[1]


def _lenses_for(sid: str) -> dict[str, Any]:
    """Internal multi-lens inputs — not shown as four long merchant sections."""
    table = {
        "A_discovery": {
            "marketing": "السلوك يقول: من يصل يشتري جيدًا — المشكلة وصول لا عرض.",
            "advertising": "لا يبرّر قناة مدفوعة محددة بعد؛ الإبراز الداخلي أولًا.",
            "algorithmic": "فجوة مشاهدات مقابل أقران + معدل إضافة/شراء قوي عند الرؤية.",
            "commercial_management": "تجربة إبراز منخفضة التكلفة وقابلة للعكس قبل أي سعر.",
            "conflict": None,
        },
        "B_high_interest_low_conversion": {
            "marketing": "اهتمام مرتفع ثم انسحاب — رسالة/تكلفة شحن مرشحة.",
            "advertising": "لا تبرير لزيادة إنفاق اكتساب قبل إصلاح الاحتكاك.",
            "algorithmic": "هيمنة تردد الشحن ضمن الهجر بحجم كافٍ.",
            "commercial_management": "تشخيص الشحن قبل الخصم يحمي الهامش المجهول.",
            "conflict": None,
        },
        "C_price_sensitive": {
            "marketing": "تردّد سعر متكرر مع اهتمام قوي.",
            "advertising": "لا قناة مطلوبة لهذه المهمة.",
            "algorithmic": "حصة تردد السعر فوق العتبة مع حجم إضافات كافٍ.",
            "commercial_management": "تجربة عرض بزمن وإيقاف؛ ممنوع uplift مخترع. هامش الإنتاج غير معروف.",
            "conflict": "إشارة تسويق تدعم عرضًا، لكن اقتصاد التكلفة غير متاح في الإنتاج → تجربة محدودة فقط.",
        },
        "D_discount_destroys_value": {
            "marketing": "الخصم يزيد الإتمام.",
            "advertising": "لا.",
            "algorithmic": "مقارنة أيام عرض/غير عرض في المحاكاة تظهر مساهمة أسوأ.",
            "commercial_management": "رفع التحويل بلا اقتصاد أفضل = قرار سيئ.",
            "conflict": "عدسة التسويق تفرح بالتحويل؛ الإدارة التجارية ترفض الاستمرار.",
        },
        "E_bundle_cross_sell": {
            "marketing": "شراء مشترك واضح في السلة.",
            "advertising": "لا اكتساب عام.",
            "algorithmic": "تزامن طلبات فوق عتبة.",
            "commercial_management": "اقتراح مكمل يرفع قيمة السلة باحتمال جيد.",
            "conflict": None,
        },
        "F_channel_quality": {
            "marketing": "جودة زيارات تختلف بين قناتين لنفس المنتج.",
            "advertising": "يبرّر تجربة اكتساب محدودة فقط لهذا المنتج — لا تعميم.",
            "algorithmic": "حجم كافٍ لكل قناة مع فرق شراء ومتوسط طلب.",
            "commercial_management": "إعادة تخصيص محدودة أفضل من شعار «شغّل قناة».",
            "conflict": None,
        },
        "G_retention": {
            "marketing": "عملاء اشتروا A يميلون لـ B لاحقًا.",
            "advertising": "ليس اكتساب زوار جدد.",
            "algorithmic": "ميل لاحق أعلى ماديًا من خط الأساس.",
            "commercial_management": "رسالة موجّهة لشريحة موجودة أرخص من اكتساب جديد.",
            "conflict": None,
        },
        "H_insufficient_evidence": {
            "marketing": "إشارات ضعيفة ومتضاربة.",
            "advertising": "لا.",
            "algorithmic": "عينة تحت العتبة.",
            "commercial_management": "أي حركة إبداعية الآن = مخاطرة بلا أساس.",
            "conflict": None,
        },
    }
    return table.get(sid, {
        "marketing": "",
        "advertising": "",
        "algorithmic": "",
        "commercial_management": "",
        "conflict": None,
    })


def _idea_pack(sid: str, m: dict[str, Any]) -> dict[str, str]:
    name = ""
    scope = m.get("scope") or {}
    if scope.get("name_ar"):
        name = str(scope["name_ar"])
    if sid == "A_discovery":
        return {
            "commercial_opportunity_ar": f"المنتج «{name}» يُشترى جيدًا عند رؤيته لكن قلّة يكتشفونه.",
            "commercial_idea_ar": (
                f"اختبر إبراز «{name}» في الصفحة الرئيسية والتصنيف لمدة 7–14 يومًا قبل أي تعديل سعر."
            ),
            "why_idea_fits_ar": (
                "الاكتشاف ضعيف والتحويل بعد الوصول قوي — الإبراز يختبر الوصول دون افتراض قناة إعلان."
            ),
            "action_ar": "فعّل إبرازًا أوضح في الرئيسية/التصنيف لمدة محدودة وسجّل تاريخ البدء.",
            "measure_ar": "نراقب المشاهدات، الإضافة للسلة، الشراء، وإيراد المنتج مقابل أساس 30 يومًا.",
            "recheck_ar": "بعد 14 يومًا، أو عند ارتفاع المشاهدات بنحو 40% مع ثبات جودة الإضافة للسلة.",
        }
    if sid == "B_high_interest_low_conversion":
        return {
            "commercial_opportunity_ar": "اهتمام قوي لا يتحول إلى شراء بسبب احتكاك شحن ظاهر في الدليل.",
            "commercial_idea_ar": (
                "اختبر توضيح تكلفة وخيار الشحن في مسار الشراء لمدة 14 يومًا — دون خصم منتج كخطوة أولى."
            ),
            "why_idea_fits_ar": "هيمنة تردد الشحن مع إضافة مرتفعة للسلة تجعل إصلاح الوضوح أسبق من السعر.",
            "action_ar": "راجع وضوح الشحن والتوصيل عند الدفع وطبق رسالة أوضح مؤقتًا.",
            "measure_ar": "نراقب حصة تردد الشحن، الشراء بعد الإضافة، والاسترداد الناجح، وإيراد المنتج.",
            "recheck_ar": "بعد 14 يومًا أو إذا انخفضت حصة تردد الشحن تحت ربع حالات الهجر.",
        }
    if sid == "C_price_sensitive":
        return {
            "commercial_opportunity_ar": "اهتمام قوي مع تردد سعر متكرر بحجم يكفي لتجربة محدودة.",
            "commercial_idea_ar": (
                "شغّل عرضًا محدود المدة (10–14 يومًا) بسقف خصم محدد مسبقًا، مع إيقاف إذا تراجع الإيراد المقاس."
            ),
            "why_idea_fits_ar": (
                "عدسة التسويق تدعم تجربة سعر، لكن غياب تكلفة الإنتاج يمنع وعد ربح — لذلك التجربة محدودة القياس."
            ),
            "action_ar": "أطلق العرض بسقف ومدة مكتوبين، وفعّل شرط الإيقاف على الإيراد.",
            "measure_ar": "قبل/بعد: الشراء بعد الإضافة، متوسط قيمة الطلب، إيراد المنتج، حصة تردد السعر.",
            "recheck_ar": "إيقاف مبكر إذا هبط إيراد المنتج أكثر من 10% خلال 7 أيام؛ تقييم كامل يوم 14.",
        }
    if sid == "D_discount_destroys_value":
        return {
            "commercial_opportunity_ar": "الخصم الحالي يُظهر تحويلًا أعلى لكن اقتصادًا أضعف في المحاكاة.",
            "commercial_idea_ar": "أوقف الخصم الحالي أو استبدله بعرض لا يخفض المساهمة المحاكاة تحت عتبة مقبولة.",
            "why_idea_fits_ar": "الفرح بالتحويل وحده مضلّل؛ الإدارة التجارية تفرض إيقاف تدمير القيمة.",
            "action_ar": "أوقف العرض الجاري فورًا أو أعد تصميمه ثم راقب أسبوعين.",
            "measure_ar": "بعد الإيقاف: التحويل إلى شراء، الإيراد، والمساهمة المحاكاة إن وُجدت.",
            "recheck_ar": "بعد 14 يومًا من الإيقاف؛ أعد الفتح إذا عاد ضغط التحويل دون تحسن إيراد.",
        }
    if sid == "E_bundle_cross_sell":
        return {
            "commercial_opportunity_ar": "علاقة شراء مشتركة قوية بين منتجين في السلة.",
            "commercial_idea_ar": "اختبر اقتراح المنتج المكمل عند سلة/شراء المنتج الأساسي لمدة 14 يومًا.",
            "why_idea_fits_ar": "الارتباط مثبت في طلبات حقيقية بالمحاكاة — ليس تشابه تصنيف فقط.",
            "action_ar": "أظهر اقتراح المكمل في السلة أو بعد الشراء لمدة أسبوعين.",
            "measure_ar": "معدل السلات المشتركة، متوسط قيمة الطلب للزوج، وإيراد الزوج مقابل الأساس.",
            "recheck_ar": "بعد 14 يومًا أو إذا لم تزد الحزم بشكل مادي → غير حاسم.",
        }
    if sid == "F_channel_quality":
        return {
            "commercial_opportunity_ar": f"جودة زيارات «{name}» أعلى على TikTok منها على البحث ضمن العينة.",
            "commercial_idea_ar": (
                f"اختبر حصة اكتساب محدودة لـ«{name}» عبر TikTok مقابل مجموعة مقارنة على البحث — بلا تعميم على الفئة."
            ),
            "why_idea_fits_ar": "الفرق يشمل الزيارات والإضافة والشراء ومتوسط الطلب لهذا المنتج فقط.",
            "action_ar": "شغّل تجربة محدودة المدة/الميزانية مع مجموعة مقارنة، وسجّل القناتين.",
            "measure_ar": "لكل قناة: الإضافة للسلة، الشراء، متوسط قيمة الطلب، والإيراد.",
            "recheck_ar": "بعد 14 يومًا أو إذا صغرت عينة أي قناة تحت العتبة — أوقف التوصية.",
        }
    if sid == "G_retention":
        return {
            "commercial_opportunity_ar": "مشترو المنتج الأساسي لديهم ميل أعلى لشراء المكمل لاحقًا.",
            "commercial_idea_ar": "اختبر عرض المنتج المكمل لعملاء اشتروا الأساسي بعد الشراء — لا كحملة زوار جدد.",
            "why_idea_fits_ar": "العلاقة زمنية بعد الشراء؛ تصنيفها احتفاظ/قيمة عميل لا اكتساب.",
            "action_ar": "أرسل اقتراحًا موجّهًا لشريحة مشترين الأساسي لمدة 14–21 يومًا.",
            "measure_ar": "معدل شراء المكمل اللاحق وإيراد الشريحة — دون خلط مع زيارات جديدة.",
            "recheck_ar": "بعد 21 يومًا؛ إذا لم يتجاوز الميل خط الأساس بفارق مادي → أوقف.",
        }
    # H insufficient — no creative action
    return {
        "commercial_opportunity_ar": "لا فرصة مؤهلة بعد.",
        "commercial_idea_ar": "لا فكرة تجارية — الدليل غير كافٍ.",
        "why_idea_fits_ar": "توليد حركة إبداعية بلا عتبة يخرق قانون الدليل.",
        "action_ar": "لا إجراء تجاري. اجمع مشاهدات وإضافات أوضح لأسباب التردد.",
        "measure_ar": "بلوغ عتبة المشاهدات والإضافات المتفق عليها قبل إعادة النظر.",
        "recheck_ar": "عند بلوغ العتبة أو بعد دورة 30 يومًا إضافية.",
    }


def apply_commercial_imagination_v1(m: dict[str, Any]) -> dict[str, Any]:
    sid = str(m.get("scenario_id") or "")
    out = dict(m)
    obj_code, obj_ar = _objective_for(sid)
    lenses = _lenses_for(sid)
    pack = _idea_pack(sid, m)

    # Evidence safety: insufficient never gets creative action
    if m.get("status") == "insufficient_evidence" or sid == "H_insufficient_evidence":
        pack = _idea_pack("H_insufficient_evidence", m)
        obj_code, obj_ar = "", ""

    # Detect generic ideas
    idea = pack["commercial_idea_ar"]
    generic = any(g.lower() in idea.lower() for g in _GENERIC_BANNED)
    if generic and sid != "H_insufficient_evidence":
        # force fail-safe rewrite
        pack["commercial_idea_ar"] = "راجع الدليل قبل أي حركة — الفكرة العامة مرفوضة."

    out.update(
        {
            "commercial_objective": obj_code,
            "commercial_objective_ar": obj_ar,
            "commercial_opportunity_ar": pack["commercial_opportunity_ar"],
            "commercial_idea_ar": pack["commercial_idea_ar"],
            "why_idea_fits_ar": pack["why_idea_fits_ar"],
            "action_ar": pack["action_ar"],
            "measure_ar": pack["measure_ar"],
            "recheck_ar": pack["recheck_ar"],
            "lenses_internal": lenses,
            "lens_conflict_ar": lenses.get("conflict"),
            "generic_idea_flag": generic,
            # Keep diagnosis short for workspace
            "diagnosis_short_ar": _short_diagnosis(sid, m),
            "what_not_to_do_ar": _what_not(sid, m.get("what_not_to_do_ar") or ""),
            "why_now_short_ar": (m.get("why_prioritized_ar") or "")[:180],
        }
    )
    # Home brevity fields
    out["home_why_ar"] = _home_why(sid)
    out["home_action_ar"] = pack["action_ar"]
    out["home_measure_ar"] = pack["measure_ar"]
    out["home_recheck_ar"] = pack["recheck_ar"]
    return out


def _short_diagnosis(sid: str, m: dict[str, Any]) -> str:
    d = {
        "A_discovery": "فرصة اكتشاف/توزيع — لا مشكلة سعر فورية من هذا الدليل.",
        "B_high_interest_low_conversion": "احتكاك بعد الاهتمام مرتبط بالشحن أكثر من السعر.",
        "C_price_sensitive": "حساسية سعر مدعومة بحجم كافٍ لتجربة عرض محدودة.",
        "D_discount_destroys_value": "رفع التحويل بالخصم يضعف الاقتصاد المحاكى.",
        "E_bundle_cross_sell": "علاقة شراء تكميلية تدعم اقتراحًا متقاطعًا.",
        "F_channel_quality": "فرق جودة قناة لهذا المنتج ضمن العينة — بلا تعميم فئة.",
        "G_retention": "ميل لاحق أعلى لدى مشترين حاليين — احتفاظ لا اكتساب.",
        "H_insufficient_evidence": "دليل غير كافٍ — يُرفض أي إجراء تجاري.",
    }
    return d.get(sid) or (m.get("diagnosis_ar") or "")[:120]


def _home_why(sid: str) -> str:
    d = {
        "A_discovery": "من يصل يشتري جيدًا، لكن قليلين يصلون مقارنة بمنتجات مشابهة في متجرك.",
        "B_high_interest_low_conversion": "الاهتمام مرتفع والشراء ضعيف مع إشارة شحن واضحة.",
        "C_price_sensitive": "تردّد السعر متكرر بما يكفي لتجربة عرض قصيرة قابلة للإيقاف.",
        "D_discount_destroys_value": "العرض يرفع الإتمام ويضعف القيمة المحاكاة في الوقت نفسه.",
        "E_bundle_cross_sell": "المنتجان يُشتريان معًا بوضوح — فرصة قيمة سلة.",
        "F_channel_quality": "قناة تعطيك زيارات أجود من أخرى لنفس المنتج.",
        "G_retention": "عملاء اشتروا مرة لديهم ميل أعلى لمنتج مكمل لاحقًا.",
        "H_insufficient_evidence": "العينة أصغر من أن تبرّر أي حركة.",
    }
    return d.get(sid, "الفرصة مبنية على دليل المتجر الحالي.")


def _what_not(sid: str, existing: str) -> str:
    # Prefer commercial language without ATC abbreviation
    cleaned = (existing or "").replace("ATC", "الإضافة للسلة").replace("AOV", "متوسط قيمة الطلب")
    mapping = {
        "A_discovery": "لا تفترض قناة إعلان محددة، ولا تخفّض السعر كخطوة أولى من ضعف الوصول وحده.",
        "B_high_interest_low_conversion": "لا تقدّم خصمًا فوريًا لأن الإضافة للسلة مرتفعة؛ لا تتجاهل دليل الشحن.",
        "C_price_sensitive": "لا تخترع رفع إيراد متوقع؛ لا تقارن بسعر سوق خارجي بلا مصدر محكوم.",
        "D_discount_destroys_value": "لا تحتفل برفع التحويل مع تجاهل اقتصاد الإيراد.",
        "E_bundle_cross_sell": "لا تقترح حزمة من تشابه التصنيف وحده.",
        "F_channel_quality": "لا توصية عامة «شغّل TikTok»؛ لا تعيد تخصيص إنفاقًا بعينة صغيرة.",
        "G_retention": "لا تعامل الشريحة كحملة اكتساب لزوار جدد.",
        "H_insufficient_evidence": "لا إجراء تجاري حتى تكتمل العتبات.",
    }
    return mapping.get(sid) or cleaned


__all__ = ["apply_commercial_imagination_v1"]
