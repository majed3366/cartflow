# -*- coding: utf-8 -*-
"""
Commercial Action Language Contract V1.

Merchant-facing copy for the four current decision kinds only.
Does not change COL/OGL ranking, thresholds, windows, or CDC.
"""
from __future__ import annotations

from typing import Any, Mapping

CTA_ACCEPT_MISSION_AR = "اعتمد هذه المهمة"
ACCEPTED_STATE_AR = "هذه مهمتك الحالية حتى تُنفَّذ أو تتغير الأدلة."
MISSION_SHIPPING_AR = (
    "حدّد هل التردد مرتبط بتكلفة الشحن أم مدة التوصيل قبل أي تغيير في السعر."
)

FAMILY_SHIPPING = "shipping_friction"
FAMILY_PRODUCT = "product_confidence"
FAMILY_PRICE = "price_hesitation"
FAMILY_WAIT = "wait_insufficient_evidence"

CONTRACT_FAMILIES = frozenset(
    {FAMILY_SHIPPING, FAMILY_PRODUCT, FAMILY_PRICE, FAMILY_WAIT}
)

VAGUE_ACTION_OPENERS = ("راجع", "حسّن", "افصل", "راقب", "انتبه")

FORBIDDEN_WIDGET_AR = "الودجت"
FORBIDDEN_WIDGET_ALT_AR = "الودجيت"


def _norm(text: Any) -> str:
    return " ".join(str(text or "").strip().split())


def _share_pct(evidence: Mapping[str, Any] | None) -> int | None:
    if not isinstance(evidence, Mapping):
        return None
    counts = evidence.get("counts") if isinstance(evidence.get("counts"), Mapping) else {}
    share = counts.get("top_share")
    if share is None:
        return None
    try:
        return int(round(float(share) * 100))
    except (TypeError, ValueError):
        return None


def _counts(evidence: Mapping[str, Any] | None) -> tuple[int | None, int | None]:
    if not isinstance(evidence, Mapping):
        return None, None
    counts = evidence.get("counts") if isinstance(evidence.get("counts"), Mapping) else {}
    try:
        top = int(counts.get("top_count")) if counts.get("top_count") is not None else None
    except (TypeError, ValueError):
        top = None
    try:
        total = (
            int(counts.get("hesitation_total"))
            if counts.get("hesitation_total") is not None
            else None
        )
    except (TypeError, ValueError):
        total = None
    return top, total


def contract_for_family_v1(
    family: str,
    *,
    evidence: Mapping[str, Any] | None = None,
    reason_label_ar: str = "",
) -> dict[str, str] | None:
    """Return the eight-field merchant contract for one governed family."""
    kind = str(family or "").strip()
    if kind not in CONTRACT_FAMILIES:
        return None
    top, total = _counts(evidence)
    share = _share_pct(evidence)
    label = _norm(reason_label_ar) or "هذا السبب"

    if kind == FAMILY_SHIPPING:
        if top is not None and total and share is not None:
            evidence_ar = (
                f"أسباب التردد المرتبطة بالشحن هي الأعلى الآن: {top} من {total} "
                f"({share}٪). هذا نمط ارتباط في سجل أسباب المتجر، لا إثبات سبب جذري."
            )
            measure_ar = (
                f"حصة أسباب الشحن من إجمالي أسباب التردد خلال نافذة المراقبة الحالية "
                f"(7 أيام — الآن {share}٪)."
            )
        else:
            evidence_ar = (
                "الشحن هو أقوى نمط تردد مسجّل في المتجر حالياً. "
                "هذا ارتباط في أسباب العملاء، لا إثبات أن التكلفة أو المدة هي السبب."
            )
            measure_ar = (
                "حصة أسباب الشحن من إجمالي أسباب التردد خلال نافذة المراقبة الحالية (7 أيام)."
            )
        return {
            "situation_ar": "أقوى تردد مسجّل الآن مرتبط بالشحن.",
            "evidence_ar": evidence_ar,
            "diagnosis_ar": (
                "لا يتضح بعد هل التردد الأقوى مرتبط بتكلفة الشحن أم بمدة التوصيل."
            ),
            "mission_ar": MISSION_SHIPPING_AR,
            "action_ar": (
                "افتح أسباب التردد في سياسة الاسترجاع، وتأكد أن العميل يستطيع الاختيار بين "
                "«تكلفة الشحن مرتفعة» و«مدة التوصيل طويلة»."
            ),
            "dont_ar": (
                "لا تخفّض الشحن ولا تجعله مجانياً قبل أن يتضح هل المشكلة التكلفة أم المدة."
            ),
            "measure_ar": measure_ar,
            "recheck_ar": (
                "بعد بلوغ حد الكفاية المعتمد للعينة الحالية، أو عند انخفاض واضح في حصة الشحن."
            ),
            "cta_ar": CTA_ACCEPT_MISSION_AR,
        }

    if kind == FAMILY_PRODUCT:
        if top is not None and total and share is not None:
            evidence_ar = (
                f"أسباب التردد المرتبطة بثقة المنتج («{label}») هي الأعلى الآن: "
                f"{top} من {total} ({share}٪). لا إثبات هنا على ضعف الظهور أو الإعلان."
            )
            measure_ar = (
                f"حصة أسباب ثقة المنتج («{label}») خلال 7 أيام (الآن {share}٪)."
            )
        else:
            evidence_ar = (
                "أسباب التردد تتركّز حول ثقة المنتج (جودة أو ضمان) في سجل المتجر. "
                "لا دليل تعرّض أو إعلان هنا."
            )
            measure_ar = "حصة أسباب ثقة المنتج خلال نافذة المراقبة الحالية (7 أيام)."
        return {
            "situation_ar": "العملاء يترددون حول وضوح جودة المنتج أو ضمانه قبل الشراء.",
            "evidence_ar": evidence_ar,
            "diagnosis_ar": (
                "الخطوة التالية هي توضيح ما يثبت المنتج مما هو صحيح عندك، "
                "لا اختراع تقييمات أو شهادات."
            ),
            "mission_ar": "أظهر إثبات الجودة أو الضمان القائم قبل تغيير السعر أو الظهور.",
            "action_ar": (
                "أظهر في صفحة المنتج ما يثبت الجودة أو الضمان مما هو قائم فعلاً "
                "(مثل مدة الضمان أو ما يشمله المنتج) — بلا تقييمات أو شهادات غير موجودة."
            ),
            "dont_ar": (
                "لا تخفّض السعر، ولا تعلن المنتج، ولا تختلق إثباتات ثقة غير موجودة."
            ),
            "measure_ar": measure_ar,
            "recheck_ar": (
                "بعد بلوغ حد الكفاية المعتمد، أو عند انخفاض واضح في حصة أسباب ثقة المنتج."
            ),
            "cta_ar": CTA_ACCEPT_MISSION_AR,
        }

    if kind == FAMILY_PRICE:
        if top is not None and total and share is not None:
            evidence_ar = (
                f"السعر هو أعلى سبب تردد الآن: {top} من {total} ({share}٪). "
                "هذا لا يثبت أن الخصم يرفع الإيراد."
            )
            measure_ar = f"حصة سبب السعر خلال 7 أيام (الآن {share}٪)."
        else:
            evidence_ar = (
                "السعر هو أقوى سبب تردد مسجّل حالياً. التكرار لا يعني أن الخصم هو الحل."
            )
            measure_ar = "حصة سبب السعر خلال نافذة المراقبة الحالية (7 أيام)."
        return {
            "situation_ar": "العملاء يترددون عند السعر قبل إتمام الشراء.",
            "evidence_ar": evidence_ar,
            "diagnosis_ar": (
                "المطلوب الآن توضيح القيمة مقابل السعر الحالي، لا تخفيض السعر تلقائياً."
            ),
            "mission_ar": "وضّح قيمة العرض مقابل السعر الحالي قبل أي خصم.",
            "action_ar": (
                "بيّن في صفحة المنتج ماذا يحصل عليه العميل مقابل السعر الحالي "
                "قبل أي تخفيض — ثم نعيد قراءة حصة سبب السعر."
            ),
            "dont_ar": (
                "لا تطلق خصماً عاماً ولا تخفّض السعر لأن السعر تكرر كسبب تردد."
            ),
            "measure_ar": measure_ar,
            "recheck_ar": (
                "بعد بلوغ حد الكفاية المعتمد، أو عند انخفاض واضح في حصة سبب السعر."
            ),
            "cta_ar": CTA_ACCEPT_MISSION_AR,
        }

    return {
        "situation_ar": "الأدلة الحالية لا تكفي لتوصية بتغيير تجاري.",
        "evidence_ar": (
            f"عيّنة أسباب التردد الحالية ({total}) لم تستوفِ حد الكفاية المعتمد، "
            "أو لا يوجد سبب واحد مهيمن."
            if total is not None
            else "عيّنة أسباب التردد لم تستوفِ حد الكفاية المعتمد، أو لا يوجد سبب مهيمن."
        ),
        "diagnosis_ar": (
            "CartFlow يرفض التوصية بتغيير سعر أو شحن أو عرض لأن القرار على عيّنة غير كافية "
            "يوجّه المتجر في الاتجاه الخطأ."
        ),
        "mission_ar": "لا تغيّر سعراً أو شحناً أو عرضاً حتى تكفي العيّنة.",
        "action_ar": (
            "أبقِ السعر والشحن والعرض كما هي، وواصل تسجيل أسباب تردد العملاء "
            "حتى يظهر سبب واحد بوضوح كافٍ."
        ),
        "dont_ar": "لا تغيّر سعراً أو شحناً أو عرضاً بناءً على عيّنة غير كافية.",
        "measure_ar": (
            "عدد أسباب التردد المسجّلة، وما إذا ظهر سبب واحد مهيمن ضمن حد الكفاية المعتمد."
        ),
        "recheck_ar": (
            "عندما تصل العيّنة إلى حد الكفاية المعتمد ويظهر سبب واحد مهيمن."
        ),
        "cta_ar": CTA_ACCEPT_MISSION_AR,
    }


def starts_with_vague_opener(text: str) -> bool:
    raw = _norm(text)
    return any(raw.startswith(op) for op in VAGUE_ACTION_OPENERS)


__all__ = [
    "ACCEPTED_STATE_AR",
    "CTA_ACCEPT_MISSION_AR",
    "CONTRACT_FAMILIES",
    "FAMILY_PRICE",
    "FAMILY_PRODUCT",
    "FAMILY_SHIPPING",
    "FAMILY_WAIT",
    "MISSION_SHIPPING_AR",
    "FORBIDDEN_WIDGET_ALT_AR",
    "FORBIDDEN_WIDGET_AR",
    "VAGUE_ACTION_OPENERS",
    "contract_for_family_v1",
    "starts_with_vague_opener",
]
