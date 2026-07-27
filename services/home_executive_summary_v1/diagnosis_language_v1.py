# -*- coding: utf-8 -*-
"""
Home Diagnosis Language V1.

Transforms Home executive cards from event summary → diagnostic brief:

  Observation (status chip) → Diagnosis → Recommendation

Never Observation → Recommendation.
Never invent a cause. Insufficient evidence must be explicit.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

# Diagnosis openers — never lead with Review / Go / Open.
BELIEVES_AR = "يعتقد CartFlow أن"
STRONGEST_EVIDENCE_AR = "أقوى الأدلة تشير إلى"
EVIDENCE_SUGGESTS_AR = "تشير الأدلة إلى"

DIAG_INSUFFICIENT_AR = (
    "لا يستطيع CartFlow بعد تحديد السبب التشغيلي بثقة كافية."
)
REC_CONTINUE_EVIDENCE_AR = "واصل جمع الأدلة."

REC_COMMUNICATION_AR = "راجع التواصل."
REC_PURCHASE_JOURNEY_AR = "راجع رحلة الشراء."
REC_SETTINGS_AR = "راجع الإعدادات."
REC_NO_URGENT_AR = "لا إجراء عاجل مطلوب الآن."

# Forbidden merchant-facing openers (imperative routing before diagnosis).
_FORBIDDEN_OPENERS_AR = (
    "راجع ",
    "راجع",
    "اذهب ",
    "افتح ",
    "اضبط ",
)


def _norm(text: Any) -> str:
    return " ".join(str(text or "").strip().split())


def _product_short(name: str) -> str:
    t = _norm(name)
    if not t:
        return ""
    return t.split("—")[0].strip() or t


def _starts_with_forbidden_opener(text: str) -> bool:
    t = _norm(text)
    return any(t.startswith(p) for p in _FORBIDDEN_OPENERS_AR)


def _compose_body(diagnosis_ar: str, recommendation_ar: str) -> str:
    d = _norm(diagnosis_ar)
    r = _norm(recommendation_ar)
    if d and r:
        return f"{d}\n{r}"
    return d or r


def _as_int(v: Any) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


def _teaser_counts(summary: Mapping[str, Any] | None) -> dict[str, int]:
    src = summary if isinstance(summary, Mapping) else {}
    t = src.get("home_teaser_inputs_v1")
    if not isinstance(t, Mapping):
        return {"no_phone": 0, "waiting": 0, "schedules": 0}
    health = t.get("health") if isinstance(t.get("health"), Mapping) else {}
    carts = t.get("carts") if isinstance(t.get("carts"), Mapping) else {}
    comm = t.get("communication") if isinstance(t.get("communication"), Mapping) else {}
    no_phone = max(
        _as_int(health.get("no_phone")),
        _as_int(carts.get("no_phone")),
        _as_int(comm.get("no_phone")),
    )
    waiting = max(
        _as_int(health.get("abandoned_carts")),
        _as_int(carts.get("waiting")),
        _as_int(comm.get("waiting")),
    )
    schedules = _as_int(comm.get("schedules"))
    return {"no_phone": no_phone, "waiting": waiting, "schedules": schedules}


def _contact_blocked_evidence(text: str, *, no_phone: int) -> bool:
    t = _norm(text)
    if no_phone > 0:
        return True
    return any(
        k in t
        for k in (
            "نقص معلومات التواصل",
            "معلومات التواصل",
            "معلومات تواصل",
            "بلا رقم",
            "رقم الهاتف",
            "مقيدة",
        )
    )


def _health_diagnosis(
    sec: Mapping[str, Any], *, no_phone: int, store_ok: Any
) -> tuple[str, str]:
    text = _norm(sec.get("summary_ar"))
    status = _norm(sec.get("status_ar"))
    if store_ok is False or "جاهزية" in text or "الربط" in text:
        return (
            f"{BELIEVES_AR} جاهزية المتجر غير مكتملة لأن الربط غير مكتمل.",
            REC_SETTINGS_AR,
        )
    if _contact_blocked_evidence(text, no_phone=no_phone) or (
        no_phone > 0 and ("عاجل" in status or "متابعة" in status or "مقيدة" in text)
    ):
        return (
            f"{BELIEVES_AR} متابعة العملاء مقيدة لأن كثيراً من السلال "
            "لا تحتوي معلومات تواصل قابلة للاستخدام.",
            REC_COMMUNICATION_AR,
        )
    if sec.get("empty") or status in {"مستقر", "أدلة غير كافية"}:
        if status == "أدلة غير كافية" or "غير كافية" in text:
            return DIAG_INSUFFICIENT_AR, REC_CONTINUE_EVIDENCE_AR
        if "مستقر" in text or status == "مستقر" or "لا توجد مشكلات" in text:
            return (
                f"{STRONGEST_EVIDENCE_AR} أن المتجر يعمل دون مشكلة تشغيلية ظاهرة.",
                REC_NO_URGENT_AR,
            )
    if sec.get("needs_attention") or status in {"يحتاج تدخلاً عاجلاً", "يتطلب متابعة"}:
        # Attention without a governed cause — never invent one.
        return DIAG_INSUFFICIENT_AR, REC_CONTINUE_EVIDENCE_AR
    return DIAG_INSUFFICIENT_AR, REC_CONTINUE_EVIDENCE_AR


def _decisions_diagnosis(sec: Mapping[str, Any]) -> tuple[str, str]:
    text = _norm(sec.get("summary_ar"))
    subject = _product_short(
        str(sec.get("subject_ar") or sec.get("product_name_ar") or "")
    )
    if sec.get("empty") or not text or "لا توجد أولوية" in text:
        return DIAG_INSUFFICIENT_AR, REC_CONTINUE_EVIDENCE_AR

    # Shipping friction — only when evidence language is already present.
    if any(k in text for k in ("شحن", "تكلفة الشحن", "shipping")):
        if subject:
            diag = (
                f"{BELIEVES_AR} أكبر فرصة مبيعات ضائعة اليوم هي {subject} "
                "لأن العملاء يغادرون عند الشحن."
            )
        else:
            diag = (
                f"{EVIDENCE_SUGGESTS_AR} أن الشحن يضعف إتمام الشراء لدى العملاء."
            )
        return diag, REC_PURCHASE_JOURNEY_AR

    # Interest / conversion / purchase journey — product-named when known.
    if subject:
        diag = (
            f"{BELIEVES_AR} أكبر فرصة مبيعات ضائعة اليوم هي {subject} "
            "لأن العملاء يغادرون مراراً قبل إتمام الشراء."
        )
        return diag, REC_PURCHASE_JOURNEY_AR

    if _starts_with_forbidden_opener(text) or any(
        k in text for k in ("مسار التحويل", "إتمام الشراء", "تحويل", "اهتمام")
    ):
        return (
            f"{EVIDENCE_SUGGESTS_AR} أن أكبر فرصة مبيعات ضائعة اليوم "
            "هي العملاء الذين يغادرون قبل إتمام الشراء.",
            REC_PURCHASE_JOURNEY_AR,
        )

    # Unknown cause — do not restate an imperative action as diagnosis.
    return DIAG_INSUFFICIENT_AR, REC_CONTINUE_EVIDENCE_AR


def _product_diagnosis(sec: Mapping[str, Any]) -> tuple[str, str]:
    items = sec.get("items") if isinstance(sec.get("items"), list) else []
    lead = items[0] if items and isinstance(items[0], Mapping) else {}
    kind = _norm(lead.get("situation_kind") or sec.get("situation_kind"))
    text = _norm(
        sec.get("summary_ar")
        or lead.get("statement_ar")
        or lead.get("title_ar")
    )
    product = _product_short(
        str(
            lead.get("product_name_ar")
            or sec.get("product_name_ar")
            or ""
        )
    )

    if sec.get("empty") or "لا يوجد منتج" in text or "أدلة غير كافية" in _norm(
        sec.get("status_ar")
    ):
        return (
            "الأدلة ما زالت غير كافية لتحديد سبب مغادرة العملاء.",
            REC_CONTINUE_EVIDENCE_AR,
        )

    if kind == "shipping_friction" or "شحن" in text:
        diag = "يغادر العملاء بعد ظهور الشحن."
        if product:
            diag = f"يغادر العملاء بعد ظهور الشحن في مسار {product}."
        return diag, REC_PURCHASE_JOURNEY_AR

    if any(k in text for k in ("يعود", "عودة", "عدة مرات", "يرجع")):
        return (
            "يعود العملاء عدة مرات قبل التخلي.",
            REC_PURCHASE_JOURNEY_AR,
        )

    if kind == "interest_without_purchase" or any(
        k in text for k in ("اهتمام", "دون شراء", "لا يكملون", "يترددون")
    ):
        return (
            "يظهر العملاء نية شراء متكررة، لكن CartFlow لم يؤكد بعد سبب المغادرة.",
            REC_CONTINUE_EVIDENCE_AR,
        )

    if kind == "product_demand":
        return (
            "الأدلة ما زالت غير كافية لتأكيد سبب مغادرة العملاء.",
            REC_CONTINUE_EVIDENCE_AR,
        )

    return (
        "الأدلة ما زالت غير كافية لتحديد سبب مغادرة العملاء.",
        REC_CONTINUE_EVIDENCE_AR,
    )


def _communication_diagnosis(
    sec: Mapping[str, Any], *, no_phone: int, waiting: int, schedules: int
) -> tuple[str, str]:
    text = _norm(sec.get("summary_ar"))
    if _contact_blocked_evidence(text, no_phone=no_phone) or no_phone > 0:
        return (
            "لا يمكن التواصل مع بعض العملاء لأن رقم الهاتف غير متاح.",
            REC_COMMUNICATION_AR,
        )
    if waiting > 0 or schedules > 0 or "بانتظار" in text:
        return (
            f"{EVIDENCE_SUGGESTS_AR} أن بعض العملاء بانتظار متابعة لم تُغلق بعد.",
            REC_COMMUNICATION_AR,
        )
    if "ضبط" in text or "جاهزية" in text:
        return (
            f"{BELIEVES_AR} قناة التواصل تحتاج ضبطاً قبل أن تصل المتابعة للعملاء.",
            REC_COMMUNICATION_AR,
        )
    if sec.get("empty") or "بشكل طبيعي" in text:
        return (
            f"{STRONGEST_EVIDENCE_AR} أن التواصل مع العملاء يسير دون عائق ظاهر.",
            REC_NO_URGENT_AR,
        )
    return DIAG_INSUFFICIENT_AR, REC_CONTINUE_EVIDENCE_AR


def _carts_diagnosis(
    sec: Mapping[str, Any], *, no_phone: int, waiting: int
) -> tuple[str, str]:
    text = _norm(sec.get("summary_ar"))
    if no_phone > 0 or "مقيدة" in text:
        return (
            f"{BELIEVES_AR} متابعة بعض السلال مقيدة لأن معلومات التواصل غير متاحة.",
            REC_COMMUNICATION_AR,
        )
    if waiting > 0 or "تحتاج متابعة" in text or "قيد المتابعة" in text:
        return (
            f"{EVIDENCE_SUGGESTS_AR} أن بعض السلال تحتاج متابعة قبل أن تضيع فرصة البيع.",
            "راجع السلال.",
        )
    if sec.get("empty") or "مستقر" in text or "لا توجد سلال" in text:
        return (
            f"{STRONGEST_EVIDENCE_AR} أن السلال لا تحتاج تدخلاً تشغيلياً الآن.",
            REC_NO_URGENT_AR,
        )
    return DIAG_INSUFFICIENT_AR, REC_CONTINUE_EVIDENCE_AR


def _stamp(sec: dict[str, Any], diagnosis_ar: str, recommendation_ar: str) -> None:
    sec["diagnosis_ar"] = diagnosis_ar
    sec["recommendation_ar"] = recommendation_ar
    sec["summary_ar"] = _compose_body(diagnosis_ar, recommendation_ar)
    sec["diagnosis_language"] = "home_diagnosis_language_v1"
    # Featured product: do not paint observation titles (اهتمام مرتفع…).
    if sec.get("id") in {"situations", "observations"} and diagnosis_ar:
        items = sec.get("items")
        if isinstance(items, list) and items:
            lead = items[0] if isinstance(items[0], Mapping) else {}
            product = _product_short(str(lead.get("product_name_ar") or ""))
            sec["items"] = [
                {
                    "title_ar": product,
                    "statement_ar": diagnosis_ar,
                    "product_name_ar": product,
                    "href": str(lead.get("href") or "#workspace"),
                }
            ]


def apply_home_diagnosis_language_v1(
    sections: list[dict[str, Any]],
    *,
    summary: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Rewrite painted section copy into Diagnosis → Recommendation form."""
    counts = _teaser_counts(summary)
    src = summary if isinstance(summary, Mapping) else {}
    t = src.get("home_teaser_inputs_v1")
    health_t = t.get("health") if isinstance(t, Mapping) else {}
    store_ok = (
        health_t.get("store_connected")
        if isinstance(health_t, Mapping)
        else None
    )

    out: list[dict[str, Any]] = []
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        sid = str(sec.get("id") or "")
        if sid == "health":
            d, r = _health_diagnosis(sec, no_phone=counts["no_phone"], store_ok=store_ok)
        elif sid == "decisions":
            d, r = _decisions_diagnosis(sec)
        elif sid in {"situations", "observations"}:
            d, r = _product_diagnosis(sec)
        elif sid == "communication":
            d, r = _communication_diagnosis(
                sec,
                no_phone=counts["no_phone"],
                waiting=counts["waiting"],
                schedules=counts["schedules"],
            )
        elif sid == "carts":
            d, r = _carts_diagnosis(
                sec, no_phone=counts["no_phone"], waiting=counts["waiting"]
            )
        else:
            out.append(sec)
            continue
        _stamp(sec, d, r)
        out.append(sec)
    return out


def diagnosis_opens_correctly(text: str) -> bool:
    """True when body does not lead with a forbidden imperative opener."""
    first = _norm(text).split("\n", 1)[0]
    if not first:
        return False
    if _starts_with_forbidden_opener(first):
        return False
    return any(
        first.startswith(p)
        for p in (
            BELIEVES_AR,
            STRONGEST_EVIDENCE_AR,
            EVIDENCE_SUGGESTS_AR,
            DIAG_INSUFFICIENT_AR,
            "يظهر العملاء",
            "يغادر العملاء",
            "يعود العملاء",
            "الأدلة ما زالت",
            "لا يمكن التواصل",
            "لا يستطيع CartFlow",
        )
    )


__all__ = [
    "BELIEVES_AR",
    "DIAG_INSUFFICIENT_AR",
    "REC_COMMUNICATION_AR",
    "REC_CONTINUE_EVIDENCE_AR",
    "REC_PURCHASE_JOURNEY_AR",
    "apply_home_diagnosis_language_v1",
    "diagnosis_opens_correctly",
]
