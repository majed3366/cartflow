# -*- coding: utf-8 -*-
"""
محرّك قرار أساسي للاسترجاع — نسخة Layer D.2 (بدون إرسال واتساب بعد).
"""
from __future__ import annotations

from typing import TypedDict


class RecoveryActionResult(TypedDict):
    action: str
    message: str


def decide_recovery_action(reason_tag: str | None) -> RecoveryActionResult:
    """
    يحوّل وسم السبب المحفوظ إلى إجراء مقترح ونص متابعة (واتساب لاحقاً).
    """
    key = (reason_tag or "").strip().lower()

    mapping: dict[str, RecoveryActionResult] = {
        "price_high": {
            "action": "offer_alternative",
            "message": (
                "واضح إن السعر مهم لك 👌\n"
                "في خيار قريب بنفس الفكرة لكن بسعر أقل، ممكن يكون أنسب لك 👍\n"
                "تحب أرسله لك؟"
            ),
        },
        "quality": {
            "action": "show_social_proof",
            "message": (
                "واضح إن الجودة تهمك 👍\n"
                "المنتج عليه تجارب ممتازة، وكثير يمدحونه من ناحية الاستخدام\n"
                "إذا تحب أشاركك أبرز المميزات؟"
            ),
        },
        "shipping": {
            "action": "highlight_shipping",
            "message": (
                "أتفهمك 👍 تكلفة الشحن تفرق\n"
                "أحيانًا يكون فيه خيارات أفضل أو عروض على الشحن\n"
                "تحب أشوف لك الأنسب لك؟"
            ),
        },
        "delivery": {
            "action": "reassure_delivery",
            "message": (
                "صحيح 👍 التوصيل مهم\n"
                "غالبًا نوصل خلال فترة مناسبة، وأقدر أتأكد لك من الوقت المتوقع لمدينتك\n"
                "تحب أشيّك لك الآن؟"
            ),
        },
        "warranty": {
            "action": "reassure_warranty",
            "message": "المنتج عليه ضمان 👍 يضمن لك راحة الاستخدام",
        },
        "other": {
            "action": "generic_followup",
            "message": "حسّينا إنك متردد 👌 إذا حاب نساعدك نكمل الطلب احنا جاهزين",
        },
    }

    return mapping.get(
        key,
        {
            "action": "default",
            "message": "لاحظنا إنك مهتم 👌 حاب نساعدك تكمل الطلب؟",
        },
    )


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

    for _tag in (
        "price_high",
        "quality",
        "unknown_tag",
        "",
    ):
        _r: RecoveryActionResult = decide_recovery_action(_tag)
        print(_tag, "->", _r)
