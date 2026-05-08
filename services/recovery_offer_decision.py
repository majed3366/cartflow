# -*- coding: utf-8 -*-
"""
قرار ذكي لاقتراح العروض مقابل الطمأنة — إرشاد للتاجر فقط (لا كوبونات ولا إرسال).
جاهز لاحقاً لقواعد تاجر، CLV، ومحرك عروض ديناميكي.
"""
from __future__ import annotations

from typing import Optional, TypedDict

# عتبات سعرية تقريبية بالريال — تُضبط لاحقاً من إعدادات المتجر
_LOW_PRICE_MAX: float = 79.0
_PREMIUM_MIN: float = 750.0
_EXPENSIVE_MIN: float = 400.0


class RecoveryOfferDecision(TypedDict):
    strategy_type: str
    should_offer_discount: bool
    should_offer_free_shipping: bool
    should_offer_alternative: bool
    persuasion_mode: str
    confidence_level: str
    strategy_type_ar: str
    confidence_level_ar: str
    decision_rationale_ar: str
    persuasion_mode_ar: str


def _norm_intent(intent: str) -> str:
    k = (intent or "").strip().lower()
    return "delivery" if k == "shipping" else k


def _norm_msg(msg: str) -> str:
    t = (msg or "").strip().lower()
    for a, b in (
        ("أ", "ا"),
        ("إ", "ا"),
        ("آ", "ا"),
        ("ى", "ي"),
        ("ة", "ه"),
    ):
        t = t.replace(a, b)
    return " ".join(t.split())


def _price_objection_confidence(customer_message: str) -> str:
    """تقدير ثقة اعتراض السعر من نص الرسالة دون تغيير طبقة النية."""
    m = _norm_msg(customer_message)
    if not m:
        return "low"
    if any(
        x in m
        for x in (
            "غالي جدا",
            "مرتفع جدا",
            "مبالغ",
            "ما اقدر",
            "ما أقدر",
            "مستحيل",
            "ما عندي",
            "نسبه",
            "نسبة",
            "expensive",
        )
    ):
        return "high"
    if any(
        x in m
        for x in (
            "غالي",
            "السعر",
            "سعر",
            "خصم",
            "ارخص",
            "أرخص",
            "ارخصلي",
            "تنزيل",
        )
    ):
        return "medium"
    if len(m) < 6:
        return "low"
    return "low"


def _is_premium_category(category: str) -> bool:
    c = _norm_msg(category)
    return any(
        k in c
        for k in (
            "فاخر",
            "luxury",
            "premium",
            "ذهب",
            "الماس",
            "ساعه فاخره",
            "ساعة فاخرة",
        )
    )


def _price_band(price: Optional[float]) -> str:
    if price is None or price <= 0:
        return "unknown"
    if price < _LOW_PRICE_MAX:
        return "low"
    if price >= _PREMIUM_MIN:
        return "premium"
    if price >= _EXPENSIVE_MIN:
        return "expensive"
    return "mid"


def decide_recovery_offer_strategy(
    intent: str,
    product_price: Optional[float],
    product_category: str,
    customer_message: str = "",
    *,
    has_cheaper_alternative: bool = False,
) -> RecoveryOfferDecision:
    """
    يقرر نوع المسار: طمأنة، بديل، أو السماح باقتراح خصم ناعم (للتاجر يدوياً فقط).
    """
    eff = _norm_intent(intent)
    msg = _norm_msg(customer_message)
    band = _price_band(product_price)
    premium_cat = _is_premium_category(product_category or "")
    conf = _price_objection_confidence(customer_message) if eff == "price" else "medium"

    if eff == "ready_to_buy":
        return {
            "strategy_type": "checkout_push",
            "should_offer_discount": False,
            "should_offer_free_shipping": False,
            "should_offer_alternative": False,
            "persuasion_mode": "checkout_push",
            "confidence_level": "high",
            "strategy_type_ar": "دفع نحو إكمال الطلب",
            "confidence_level_ar": "مرتفع",
            "decision_rationale_ar": "نية الشراء جاهزة — ركّز على رابط الدفع دون تشتيت بعروض جانبية.",
            "persuasion_mode_ar": "دفع لطيف لإكمال الطلب",
        }

    if eff == "delivery":
        ship_cost = any(
            x in msg for x in ("شحن", "توصيل", "مجاني", "رسوم", "shipping", "delivery")
        )
        free_ok = ship_cost and ("مجاني" in msg or "رسوم" in msg or "سعر الشحن" in msg)
        return {
            "strategy_type": "delivery_reassurance",
            "should_offer_discount": False,
            "should_offer_free_shipping": bool(free_ok),
            "should_offer_alternative": False,
            "persuasion_mode": "value_framing",
            "confidence_level": "medium",
            "strategy_type_ar": "طمأنة التوصيل",
            "confidence_level_ar": "متوسط",
            "decision_rationale_ar": "استفسار لوجستي — طمأن على السرعة والوضوح؛ لا تتسرع بعروض مجانية غير مدروسة.",
            "persuasion_mode_ar": "تأطير قيمة الخدمة",
        }

    if eff == "quality":
        return {
            "strategy_type": "trust_proof",
            "should_offer_discount": False,
            "should_offer_free_shipping": False,
            "should_offer_alternative": False,
            "persuasion_mode": "social_proof",
            "confidence_level": "medium",
            "strategy_type_ar": "تعزيز ثقة بالجودة",
            "confidence_level_ar": "متوسط",
            "decision_rationale_ar": "سؤال جودة — اجتماعي خفيف وأصالة بدل خصومات تلطّخ الهامش.",
            "persuasion_mode_ar": "إثبات اجتماعي",
        }

    if eff == "warranty":
        return {
            "strategy_type": "warranty_trust",
            "should_offer_discount": False,
            "should_offer_free_shipping": False,
            "should_offer_alternative": False,
            "persuasion_mode": "value_framing",
            "confidence_level": "medium",
            "strategy_type_ar": "شرح الضمان",
            "confidence_level_ar": "متوسط",
            "decision_rationale_ar": "طلب ضمان — بناء ثقة باختصار دون إغراء سعري مباشر.",
            "persuasion_mode_ar": "تأطير قيمة المخاطر المنخفضة",
        }

    if eff != "price":
        return {
            "strategy_type": "balanced_guidance",
            "should_offer_discount": False,
            "should_offer_free_shipping": False,
            "should_offer_alternative": False,
            "persuasion_mode": "value_framing",
            "confidence_level": "low",
            "strategy_type_ar": "إرشاد متوازن",
            "confidence_level_ar": "منخفض",
            "decision_rationale_ar": "لا اعتراض سعر واضح — حافظ على خط دافئ دون عروض مفرطة.",
            "persuasion_mode_ar": "تأطير قيمة عام",
        }

    # --- اعتراض سعر ---
    if band in ("premium",) or premium_cat:
        return {
            "strategy_type": "value_framing_premium",
            "should_offer_discount": False,
            "should_offer_free_shipping": False,
            "should_offer_alternative": False,
            "persuasion_mode": "value_framing",
            "confidence_level": conf,
            "strategy_type_ar": "منتج مميز — تأكيد القيمة",
            "confidence_level_ar": {"high": "مرتفع", "medium": "متوسط", "low": "منخفض"}[
                conf
            ],
            "decision_rationale_ar": "فئة أو سعر مرتبط بقيمة عالية — تجنّب خصومات عدوانية تحطّم الهامش.",
            "persuasion_mode_ar": "تأطير القيمة",
        }

    if band == "expensive":
        # سعر مرتفع دون وسم «فاخر» صريح: طمأنة أولاً
        alt_ok = has_cheaper_alternative and conf in ("medium", "high")
        return {
            "strategy_type": "alternative_first" if alt_ok else "reassurance_only",
            "should_offer_discount": False,
            "should_offer_free_shipping": False,
            "should_offer_alternative": alt_ok,
            "persuasion_mode": "alternative_product" if alt_ok else "value_framing",
            "confidence_level": conf,
            "strategy_type_ar": (
                "اقتراح بديل قبل أي خصم"
                if alt_ok
                else "تهدئة اعتراض — بدون خصم مباشر"
            ),
            "confidence_level_ar": {"high": "مرتفع", "medium": "متوسط", "low": "منخفض"}[
                conf
            ],
            "decision_rationale_ar": (
                "سلة بقيمة مرتفعة: الأصلح البديل الأرخص إن وُجد، مع عدم المغامرة بخصم مباشر."
                if alt_ok
                else "سلة بقيمة مرتفعة: ركّز على الثقة والقيمة قبل أي كلام خصم."
            ),
            "persuasion_mode_ar": (
                "منتج بديل" if alt_ok else "تأطير قيمة وهدوء"
            ),
        }

    if band == "low":
        return {
            "strategy_type": "reassurance_only",
            "should_offer_discount": False,
            "should_offer_free_shipping": False,
            "should_offer_alternative": has_cheaper_alternative and conf != "low",
            "persuasion_mode": (
                "alternative_product"
                if has_cheaper_alternative and conf != "low"
                else "value_framing"
            ),
            "confidence_level": conf,
            "strategy_type_ar": (
                "تهدئة بدون خصم غير ضروري"
                if conf == "low"
                else "بديل أوضح أكثر من خصم على سعر منخفض أصلاً"
            ),
            "confidence_level_ar": {"high": "مرتفع", "medium": "متوسط", "low": "منخفض"}[
                conf
            ],
            "decision_rationale_ar": (
                "سعر السلة منخفض — لا يُنصح بخصم مباشر يضغط الهامش؛ ركّز على اللياقة والقيمة."
            ),
            "persuasion_mode_ar": (
                "منتج بديل"
                if has_cheaper_alternative and conf != "low"
                else "تأطير قيمة بسيط"
            ),
        }

    # mid band
    if conf == "low":
        return {
            "strategy_type": "reassurance_only",
            "should_offer_discount": False,
            "should_offer_free_shipping": False,
            "should_offer_alternative": False,
            "persuasion_mode": "value_framing",
            "confidence_level": "low",
            "strategy_type_ar": "تهدئة اعتراض",
            "confidence_level_ar": "منخفض",
            "decision_rationale_ar": "إشارة سعر ضعيفة — اكتفِ بطمأنة خفيفة دون إغراق بعروض.",
            "persuasion_mode_ar": "تأطير قيمة لطيف",
        }

    if has_cheaper_alternative and conf in ("medium", "high"):
        return {
            "strategy_type": "alternative_first",
            "should_offer_discount": False,
            "should_offer_free_shipping": False,
            "should_offer_alternative": True,
            "persuasion_mode": "alternative_product",
            "confidence_level": conf,
            "strategy_type_ar": "اقتراح بديل",
            "confidence_level_ar": "مرتفع" if conf == "high" else "متوسط",
            "decision_rationale_ar": "جاهز بديل أرخص في السلة — يفضّل على كلام خصم في هذه اللحظة.",
            "persuasion_mode_ar": "منتج بديل",
        }

    if conf == "high":
        return {
            "strategy_type": "soft_discount_path",
            "should_offer_discount": True,
            "should_offer_free_shipping": False,
            "should_offer_alternative": False,
            "persuasion_mode": "soft_offer",
            "confidence_level": "high",
            "strategy_type_ar": "مسار عرض ناعم (يدوي فقط)",
            "confidence_level_ar": "مرتفع",
            "decision_rationale_ar": "ضغط سعر أوضح — يمكن اقتراح عرض يدوي لطيف بعد أن تتأكد من هوامشك؛ لا يُطبَّق تلقائياً.",
            "persuasion_mode_ar": "عرض ناعم",
        }

    return {
        "strategy_type": "soft_offer_window",
        "should_offer_discount": False,
        "should_offer_free_shipping": False,
        "should_offer_alternative": False,
        "persuasion_mode": "soft_offer",
        "confidence_level": "medium",
        "strategy_type_ar": "مساحة إقناع — بلا خصم متهور",
        "confidence_level_ar": "متوسط",
        "decision_rationale_ar": "اعتراض متوسط — حافظ على احترافية؛ خصم اختياري يدوي بحذر إن رأيت فرصة.",
        "persuasion_mode_ar": "عرض ناعم محتمل",
    }
