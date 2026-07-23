# -*- coding: utf-8 -*-
"""
MEIF V1 — merchant-facing Knowledge presentation only.

Does not change Knowledge Foundation statements.
Does not strengthen claims or invent certainty.
"""
from __future__ import annotations

from typing import Any

# Pattern → merchant language (Arabic). Claims stay observational.
_TRANSLATIONS: tuple[tuple[str, str, str], ...] = (
    (
        "evidence does not include cart_abandoned_count",
        "ما زلنا لا نملك عدّاداً مكتملاً لسلات متروكة في طبقة الأدلة هذه — لا يعني ذلك غياب سلات في متجرك.",
        "insufficient",
    ),
    (
        "evidence does not include cart_added_count",
        "عدّاد إضافات السلة في طبقة الأدلة غير مكتمل بعد — نعرض فقط ما نملك عليه دليلاً.",
        "insufficient",
    ),
    (
        "evidence quality is very_high",
        "جودة الأدلة المتاحة لهذه الملاحظة مرتفعة ضمن نافذة المراجعة.",
        "high",
    ),
    (
        "evidence quality is high",
        "جودة الأدلة المتاحة لهذه الملاحظة جيدة ضمن نافذة المراجعة.",
        "high",
    ),
    (
        "purchases have newly appeared",
        "ظهرت مشتريات جديدة ضمن نافذة المراجعة الأخيرة.",
        "medium",
    ),
    (
        "evidence-linked events have newly appeared",
        "ظهرت أحداث مرتبطة بالأدلة حديثاً ضمن نافذة المراجعة.",
        "medium",
    ),
    (
        "cart additions have newly appeared",
        "ظهرت إضافات سلة جديدة ضمن نافذة المراجعة الأخيرة.",
        "medium",
    ),
)


def translate_knowledge_for_merchant_v1(statement: dict[str, Any]) -> dict[str, Any]:
    """Return presentation fields; never mutate source statement claim strength."""
    raw = str(statement.get("statement") or "").strip()
    low = raw.lower()
    merchant_ar = raw
    confidence_label = str(statement.get("confidence_level") or "unknown")
    matched = False
    for needle, ar, conf in _TRANSLATIONS:
        if needle in low:
            merchant_ar = ar
            confidence_label = conf
            matched = True
            break
    if not matched:
        # Keep original; mark as technical so UI can show gently.
        merchant_ar = (
            "ملاحظة تقنية من طبقة المعرفة — لم تُترجم بعد إلى لغة تشغيل يومية: "
            + (raw[:180] if raw else "بدون نص")
        )
    return {
        "knowledge_id": statement.get("knowledge_id"),
        "source_statement": raw,
        "merchant_statement_ar": merchant_ar,
        "knowledge_type": statement.get("knowledge_type"),
        "confidence_level": statement.get("confidence_level"),
        "confidence_label": confidence_label,
        # Merchant presentation applied (exact match or soft technical wrap).
        "translated": True,
        "translation_matched": matched,
        "claim_strengthened": False,
        "source_lineage": {
            "source_type": "knowledge",
            "source_id": statement.get("knowledge_id"),
            "evidence_confidence_id": statement.get("evidence_confidence_id"),
        },
    }


__all__ = ["translate_knowledge_for_merchant_v1"]
