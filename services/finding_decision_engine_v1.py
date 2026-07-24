# -*- coding: utf-8 -*-
"""
Finding Decision Engine V1 — convert existing Business Findings into merchant Decisions.

Consumes Findings only. Does not create Findings. No AI generation.
If evidence is insufficient → NO DECISION with explicit missing evidence.
"""
from __future__ import annotations

import os
import re
from typing import Any, Mapping, Optional

from services.business_findings_contract_v1 import (
    TYPE_DOMINANT_HESITATION,
    TYPE_HIGH_INTEREST_LOW_PURCHASE,
    TYPE_MISSING_CONTACT_BLOCKS,
    TYPE_RECOVERY_CHANNEL_EFFECTIVENESS,
    TYPE_RETURN_WITHOUT_PURCHASE,
    TYPE_TRAFFIC_VS_CONVERSION,
    TYPE_WHATSAPP_TEST_CANDIDATE,
)

ENV_FINDING_DECISION_ENGINE_V1 = "CARTFLOW_FINDING_DECISION_ENGINE_V1"
DECISION_ENGINE_VERSION_V1 = "finding_decision_engine_v1"

_INSUFFICIENT = frozenset({"insufficient", "unknown", "unavailable", ""})
_KV_RE = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([^\s;]+)")


def finding_decision_engine_v1_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    env = environ if environ is not None else os.environ
    raw = str(env.get(ENV_FINDING_DECISION_ENGINE_V1, "1") or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _parse_evidence_kv(summary: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _KV_RE.finditer(summary or ""):
        out[m.group(1).strip().lower()] = m.group(2).strip()
    return out


def _int_kv(kv: Mapping[str, str], key: str, default: int = 0) -> int:
    raw = str(kv.get(key) or "").strip()
    # allow forms like "4/18"
    if "/" in raw:
        raw = raw.split("/", 1)[0]
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default


def _no_decision(
    *,
    finding_id: str,
    finding_type: str,
    missing_evidence: str,
    evidence_summary: str,
    finding_confidence: str,
) -> dict[str, Any]:
    return {
        "schema": DECISION_ENGINE_VERSION_V1,
        "has_decision": False,
        "status": "NO_DECISION",
        "decision": "",
        "why": "",
        "expected_business_impact": "",
        "required_merchant_action": "",
        "success_metric": "",
        "review_window": "",
        "decision_confidence": "none",
        "missing_evidence": missing_evidence,
        "finding_id": finding_id,
        "finding_type": finding_type,
        "evidence_summary": evidence_summary,
        "finding_confidence": finding_confidence,
        "engine_version": DECISION_ENGINE_VERSION_V1,
    }


def _decision(
    *,
    finding_id: str,
    finding_type: str,
    decision: str,
    why: str,
    impact: str,
    action: str,
    metric: str,
    review_window: str,
    decision_confidence: str,
    evidence_summary: str,
    finding_confidence: str,
) -> dict[str, Any]:
    return {
        "schema": DECISION_ENGINE_VERSION_V1,
        "has_decision": True,
        "status": "DECISION",
        "decision": decision,
        "why": why,
        "expected_business_impact": impact,
        "required_merchant_action": action,
        "success_metric": metric,
        "review_window": review_window,
        "decision_confidence": decision_confidence,
        "missing_evidence": "",
        "finding_id": finding_id,
        "finding_type": finding_type,
        "evidence_summary": evidence_summary,
        "finding_confidence": finding_confidence,
        "engine_version": DECISION_ENGINE_VERSION_V1,
    }


def decide_from_finding_v1(
    finding: Mapping[str, Any] | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> Optional[dict[str, Any]]:
    """
    Map one Finding → Decision contract.

    Returns None only when input is not a finding. Otherwise always returns
    DECISION or NO_DECISION.
    """
    if not finding_decision_engine_v1_enabled(environ=environ):
        return None
    if not isinstance(finding, Mapping):
        return None
    fid = _norm(finding.get("finding_id"))
    ftype = _norm(finding.get("finding_type"))
    if not fid or not ftype:
        return None

    evidence = _norm(finding.get("evidence_summary") or finding.get("evidence_ar"))
    ev_obj = finding.get("evidence")
    if not evidence and isinstance(ev_obj, Mapping):
        evidence = _norm(ev_obj.get("evidence_summary") or ev_obj.get("evidence_ar"))
    elif not evidence and isinstance(ev_obj, str):
        evidence = _norm(ev_obj)
    conf = _norm(
        finding.get("confidence")
        or finding.get("confidence_level")
        or finding.get("confidence_label")
    ).lower()
    kv = _parse_evidence_kv(evidence)
    fid_l = fid.lower()

    # Hard stop: insufficient finding confidence
    if conf in _INSUFFICIENT:
        return _no_decision(
            finding_id=fid,
            finding_type=ftype,
            missing_evidence=(
                "ثقة الاستنتاج غير كافية لاتخاذ قرار تجاري "
                f"(confidence={conf or 'empty'}). مطلوب أدلة أقوى على نفس النمط."
            ),
            evidence_summary=evidence,
            finding_confidence=conf,
        )

    # Traffic vs conversion — needs visitor truth
    if ftype == TYPE_TRAFFIC_VS_CONVERSION:
        return _no_decision(
            finding_id=fid,
            finding_type=ftype,
            missing_evidence=(
                "عدد زيارات موثوق (visitor_total). "
                "لا يُسمح باستخدام السلات كبديل عن الزيارات."
            ),
            evidence_summary=evidence,
            finding_confidence=conf,
        )

    # Dominant hesitation — no dominant share → no decision
    if ftype == TYPE_DOMINANT_HESITATION:
        if "not_dominant" in fid_l or conf == "low":
            return _no_decision(
                finding_id=fid,
                finding_type=ftype,
                missing_evidence=(
                    "سبب تردد مهيمن بحصة كافية عبر أيام إضافية من التقاط الأسباب "
                    "(الحصة الحالية غير كافية لقرار تغيير العرض)."
                ),
                evidence_summary=evidence,
                finding_confidence=conf,
            )
        # Dominant case with medium/high
        top = _norm(kv.get("top") or "")
        share_raw = _norm(kv.get("share") or "")
        return _decision(
            finding_id=fid,
            finding_type=ftype,
            decision=f"ركّز عرض هذا الأسبوع على معالجة سبب التردد الأعلى: {top or 'السبب المهيمن'}.",
            why=(
                f"الاستنتاج يُظهر سبباً مهيمناً بدعم الأدلة ({evidence}). "
                "تغيير العرض دون هذا التركيز يبعثر الجهد."
            ),
            impact="رفع احتمال إكمال الشراء عند العملاء المترددين لنفس السبب.",
            action=(
                "عدّل رسالة العرض/التوصيل/السعر (حسب السبب) في الودجت وقوالب الاسترجاع "
                "خلال نافذة المراجعة — دون تغيير أسباب أخرى بعد."
            ),
            metric=(
                f"انخفاض حصة السبب المهيمن أو ارتفاع التحويل لنفس الشريحة "
                f"(حصة مرصودة: {share_raw or 'انظر الأدلة'})."
            ),
            review_window="7 أيام",
            decision_confidence="medium" if conf == "medium" else conf,
            evidence_summary=evidence,
            finding_confidence=conf,
        )

    # Widget / contact recovery channel
    if ftype == TYPE_RECOVERY_CHANNEL_EFFECTIVENESS and "widget" in fid_l:
        reasons = _int_kv(kv, "reasons")
        contacts = _int_kv(kv, "contacts")
        if reasons >= 1 and contacts == 0:
            return _decision(
                finding_id=fid,
                finding_type=ftype,
                decision="فعّل/حسّن طلب بيانات التواصل مباشرة بعد التقاط سبب التردد.",
                why=(
                    f"الأدلة تُظهر التقاط أسباب ({reasons}) دون جهات اتصال قابلة للاسترجاع "
                    f"(contacts={contacts}). الاستنتاج لا يدعم قراراً آخر قبل إصلاح التواصل."
                ),
                impact="فتح مسار استرجاع لسلات كانت خارج التواصل.",
                action=(
                    "اليوم: راجع إعداد الودجت بحيث يُطلب رقم/تواصل صالح بعد اختيار السبب، "
                    "ثم راقب ظهور contacts>0."
                ),
                metric="contacts > 0 مع استمرار reasons≥1 خلال نافذة المراجعة.",
                review_window="7 أيام",
                decision_confidence="medium" if conf in {"medium", "high"} else conf,
                evidence_summary=evidence,
                finding_confidence=conf,
            )
        if reasons >= 1 and contacts >= 1:
            return _decision(
                finding_id=fid,
                finding_type=ftype,
                decision="أبقِ التقاط السبب مع التواصل، وركّز على سرعة المتابعة بعد التقاط السبب.",
                why=f"الأدلة تُظهر أسباباً وتواصلاً معاً ({evidence}).",
                impact="تحسين زمن الاستجابة يزيد فرص الاسترجاع.",
                action="راجع سلات اليوم ذات السبب+التواصل وأغلق متابعة يدوية خلال 24 ساعة.",
                metric="ارتفاع نسبة المتابعة خلال 24 ساعة للسلات ذات التواصل.",
                review_window="7 أيام",
                decision_confidence=conf if conf in {"medium", "high"} else "medium",
                evidence_summary=evidence,
                finding_confidence=conf,
            )
        return _no_decision(
            finding_id=fid,
            finding_type=ftype,
            missing_evidence="أعداد reasons/contacts كافية من الودجت لاتخاذ قرار تشغيل.",
            evidence_summary=evidence,
            finding_confidence=conf,
        )

    # WhatsApp recovery channel
    if ftype == TYPE_RECOVERY_CHANNEL_EFFECTIVENESS and "whatsapp" in fid_l:
        sent = _int_kv(kv, "sent")
        returned = _int_kv(kv, "returned")
        purchased = _int_kv(kv, "purchased")
        if sent >= 1 and returned == 0 and purchased == 0:
            return _decision(
                finding_id=fid,
                finding_type=ftype,
                decision="لا توسّع حجم رسائل واتساب للاسترجاع هذا الأسبوع.",
                why=(
                    f"أُرسلت {sent} رسالة دون عودة أو شراء موثّق "
                    f"(returned={returned}, purchased={purchased}). "
                    "توسيع الحجم قبل ظهور أثر يُعد تخميناً لا قراراً مبنياً على أثر."
                ),
                impact="تجنّب تكلفة/ضجيج إضافي بلا عائد ظاهر؛ الحفاظ على الثقة بالقناة.",
                action=(
                    "ثبّت الحجم الحالي، راقب العودة بعد الرسالة، ولا ترفع معدل الإرسال "
                    "حتى يظهر returned≥1 أو purchased≥1 في نفس نافذة القياس."
                ),
                metric="returned≥1 أو purchased≥1 على دفعات واتساب الجديدة خلال النافذة.",
                review_window="7 أيام",
                decision_confidence="medium",
                evidence_summary=evidence,
                finding_confidence=conf,
            )
        if sent >= 1 and (returned >= 1 or purchased >= 1):
            return _decision(
                finding_id=fid,
                finding_type=ftype,
                decision="حافظ على قناة واتساب وركّز التحسين على ما بعد العودة.",
                why=f"الأدلة تُظهر إرسالاً مع أثر لاحق ({evidence}).",
                impact="تحسين التحويل بعد العودة دون المساس بأصل القناة.",
                action="راجع مسار ما بعد فتح الرسالة/العودة لنفس السلات المُسترجعة هذا الأسبوع.",
                metric="ارتفاع purchased/(returned أو sent) خلال النافذة.",
                review_window="7 أيام",
                decision_confidence=conf if conf in {"medium", "high"} else "medium",
                evidence_summary=evidence,
                finding_confidence=conf,
            )
        return _no_decision(
            finding_id=fid,
            finding_type=ftype,
            missing_evidence="حجم إرسال واتساب كافٍ مع نتائج عودة/شراء قابلة للقياس.",
            evidence_summary=evidence,
            finding_confidence=conf,
        )

    if ftype == TYPE_MISSING_CONTACT_BLOCKS:
        return _decision(
            finding_id=fid,
            finding_type=ftype,
            decision="أزل حاجز التواصل الذي يمنع الاسترجاع.",
            why=f"الاستنتاج يربط غياب التواصل بتعطيل الاسترجاع ({evidence}).",
            impact="استعادة قابلية المتابعة لسلات كانت مسدودة.",
            action="اليوم: فعّل التقاط تواصل صالح قبل أو مع سبب التردد.",
            metric="انخفاض السلات ذات السبب بدون تواصل خلال النافذة.",
            review_window="7 أيام",
            decision_confidence=conf if conf not in _INSUFFICIENT else "low",
            evidence_summary=evidence,
            finding_confidence=conf,
        )

    if ftype == TYPE_HIGH_INTEREST_LOW_PURCHASE:
        return _decision(
            finding_id=fid,
            finding_type=ftype,
            decision="راجع صفحة/عرض المنتج ذي الاهتمام العالي وتحويل منخفض — دون تغيير كتالوج كامل.",
            why=f"الأدلة تشير إلى اهتمام دون شراء ({evidence}).",
            impact="رفع تحويل المنتج المحدد لا إجمالي المتجر عشوائياً.",
            action="افتح المنتج المشار إليه في الأدلة وعدّل وضوح السعر/الشحن/الثقة هذا الأسبوع فقط.",
            metric="ارتفاع مشتريات نفس المنتج أو انخفاض ATC بلا شراء خلال النافذة.",
            review_window="14 يوماً",
            decision_confidence=conf if conf in {"medium", "high"} else "low",
            evidence_summary=evidence,
            finding_confidence=conf,
        )

    if ftype == TYPE_RETURN_WITHOUT_PURCHASE:
        return _decision(
            finding_id=fid,
            finding_type=ftype,
            decision="حسّن خطوة الإقناع عند عودة العميل دون شراء.",
            why=f"الأدلة تُظهر عودة بلا شراء ({evidence}).",
            impact="تحويل الزيارات العائدة إلى مشتريات.",
            action="راجع رسالة الاسترجاع الثانية/العرض عند العودة لهذا الأسبوع.",
            metric="انخفاض نسبة العودة بلا شراء أو ارتفاع الشراء بعد العودة.",
            review_window="7 أيام",
            decision_confidence=conf if conf in {"medium", "high"} else "low",
            evidence_summary=evidence,
            finding_confidence=conf,
        )

    if ftype == TYPE_WHATSAPP_TEST_CANDIDATE:
        return _decision(
            finding_id=fid,
            finding_type=ftype,
            decision="اختبر توقيت رسالة واتساب على عيّنة محدودة فقط.",
            why=f"الاستنتاج يرشّح اختبار توقيت لا توسعة شاملة ({evidence}).",
            impact="قياس أثر التوقيت قبل الالتزام بجدول جديد.",
            action="شغّل اختبار توقيت على دفعة صغيرة وسجّل العودة/الشراء.",
            metric="مقارنة returned/purchased بين التوقيت الحالي والاختبار.",
            review_window="14 يوماً",
            decision_confidence="low" if conf == "low" else "medium",
            evidence_summary=evidence,
            finding_confidence=conf,
        )

    # Unknown finding type with usable confidence — still refuse generic advice
    return _no_decision(
        finding_id=fid,
        finding_type=ftype,
        missing_evidence=(
            f"قاعدة قرار معتمدة لنوع الاستنتاج `{ftype}` "
            "أو أدلة تشغيلية أوضح لنفس النوع."
        ),
        evidence_summary=evidence,
        finding_confidence=conf,
    )


def attach_decision_to_finding_contract_v1(
    contract: dict[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Attach merchant_decision_v1 onto an MEBF render contract (mutate copy)."""
    if not isinstance(contract, dict):
        return contract
    decision = decide_from_finding_v1(contract, environ=environ)
    if decision is None:
        return contract
    out = dict(contract)
    out["merchant_decision_v1"] = decision
    # Surface-friendly aliases for JS
    out["decision_status"] = decision.get("status")
    out["has_merchant_decision"] = bool(decision.get("has_decision"))
    return out


__all__ = [
    "DECISION_ENGINE_VERSION_V1",
    "ENV_FINDING_DECISION_ENGINE_V1",
    "attach_decision_to_finding_contract_v1",
    "decide_from_finding_v1",
    "finding_decision_engine_v1_enabled",
]
