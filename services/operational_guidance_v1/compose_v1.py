# -*- coding: utf-8 -*-
"""
Operational Guidance Layer V1 — compose governed guidance objects.

Sequence: Evidence → Diagnosis → Recommendation → Why → Action → Recheck.

Consumes existing summary truth only (diagnostic publication, teasers,
optional hesitation distribution). Never fabricates causality or uplift.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.business_findings_families_v1 import (
    MIN_DOMINANT_COUNT,
    MIN_DOMINANT_SHARE,
    MIN_HESITATION_TOTAL,
)
from services.diagnostic_reasoning_v1.contract_v1 import (
    DIAGNOSIS_STATUS_INSUFFICIENT,
    DIAGNOSIS_STATUS_SUPPORTED,
    FAMILY_CHECKOUT_AFTER_SHIPPING,
    FAMILY_CONTACT_FOLLOWUP_BLOCKED,
    FAMILY_INTEREST_WITHOUT_PURCHASE,
)
from services.operational_guidance_v1.contract_v1 import (
    FAMILY_COMMUNICATION_FOLLOWUP,
    FAMILY_PRICE_HESITATION,
    FAMILY_PRODUCT_CONFIDENCE,
    FAMILY_SHIPPING_FRICTION,
    FAMILY_WAIT_INSUFFICIENT,
    GUIDANCE_SCHEMA_V1,
    GUIDANCE_VERSION_V1,
    STATE_ACTIVE,
    STATE_INSUFFICIENT,
    empty_guidance_object_v1,
    is_bare_generic_recommendation_ar,
    validate_guidance_object_v1,
)

REASON_LABEL_AR = {
    "price": "السعر",
    "shipping": "الشحن",
    "delivery": "مدة التوصيل",
    "quality": "الجودة",
    "warranty": "الضمان",
    "thinking": "التفكير قبل الشراء",
    "other": "سبب آخر",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _norm(text: Any) -> str:
    return " ".join(str(text or "").strip().split())


def _as_int(v: Any) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


def _teasers(summary: Mapping[str, Any]) -> dict[str, Any]:
    raw = summary.get("home_teaser_inputs_v1")
    return dict(raw) if isinstance(raw, Mapping) else {}


def _hesitation_from_summary(
    summary: Mapping[str, Any],
) -> tuple[int, dict[str, int]]:
    """Optional lightweight hesitation counts already on the summary."""
    for key in ("hesitation_evidence_v1", "operational_guidance_evidence_v1"):
        blob = summary.get(key)
        if not isinstance(blob, Mapping):
            continue
        total = _as_int(blob.get("hesitation_total"))
        dist_raw = blob.get("hesitation_distribution")
        dist: dict[str, int] = {}
        if isinstance(dist_raw, Mapping):
            for k, v in dist_raw.items():
                kk = str(k).strip().lower()
                if kk:
                    dist[kk] = _as_int(v)
        if total or dist:
            if not total:
                total = sum(dist.values())
            return total, dist
    return 0, {}


def _finalize(obj: dict[str, Any]) -> dict[str, Any]:
    errors = validate_guidance_object_v1(obj)
    if errors:
        obj["ok"] = False
        obj["contract_errors"] = errors
        return obj
    if is_bare_generic_recommendation_ar(obj.get("recommendation")):
        obj["ok"] = False
        obj["contract_errors"] = ["bare_generic_recommendation"]
        return obj
    # Merchant surfaces (no chain-of-thought).
    obj["home_surface"] = {
        "what_we_see_ar": _norm(obj.get("evidence_summary_ar") or obj.get("diagnosis")),
        "what_it_means_ar": _norm(obj.get("diagnosis")),
        "what_to_do_now_ar": _norm(obj.get("merchant_action")),
        "when_to_recheck_ar": _norm(obj.get("recheck_condition")),
    }
    obj["workspace_surface"] = {
        "evidence_ar": _norm(obj.get("evidence_summary_ar") or ""),
        "diagnosis_ar": _norm(obj.get("diagnosis")),
        "recommendation_ar": _norm(obj.get("recommendation")),
        "why_ar": _norm(obj.get("reasoning_summary")),
        "recheck_condition_ar": _norm(obj.get("recheck_condition")),
        "action_ar": _norm(obj.get("merchant_action")),
    }
    obj["ok"] = True
    obj["contract_errors"] = []
    return obj


def _guidance(
    *,
    store_slug: str,
    family: str,
    guidance_id: str,
    subject: str,
    evidence_refs: list[str],
    evidence_summary_ar: str,
    diagnosis: str,
    recommendation: str,
    reasoning_summary: str,
    merchant_action: str,
    recheck_condition: str,
    confidence_state: str,
    expected_monitored_outcome: str = "",
    generated_at: str = "",
) -> dict[str, Any]:
    obj = empty_guidance_object_v1(
        store_slug=store_slug,
        subject=subject,
        guidance_id=guidance_id,
        generated_at=generated_at or _now_iso(),
    )
    obj.update(
        {
            "schema": GUIDANCE_SCHEMA_V1,
            "guidance_version": GUIDANCE_VERSION_V1,
            "family": family,
            "evidence_refs": list(evidence_refs),
            "evidence_summary_ar": _norm(evidence_summary_ar),
            "diagnosis": _norm(diagnosis),
            "recommendation": _norm(recommendation),
            "reasoning_summary": _norm(reasoning_summary),
            "merchant_action": _norm(merchant_action),
            "recheck_condition": _norm(recheck_condition),
            "confidence_state": confidence_state,
            "expected_monitored_outcome": _norm(expected_monitored_outcome),
        }
    )
    return _finalize(obj)


def compose_wait_insufficient_v1(
    *,
    store_slug: str,
    missing_ar: str,
    observe_ar: str,
    unlock_ar: str,
    evidence_refs: Optional[list[str]] = None,
    generated_at: str = "",
) -> dict[str, Any]:
    return _guidance(
        store_slug=store_slug,
        family=FAMILY_WAIT_INSUFFICIENT,
        guidance_id=f"ogl:wait:{store_slug or 'store'}",
        subject="store",
        evidence_refs=evidence_refs or ["evidence:insufficient"],
        evidence_summary_ar=missing_ar,
        diagnosis=(
            "لا توجد أدلة كافية بعد لاتخاذ قرار تشغيلي موثوق."
        ),
        recommendation=(
            "لا تغيّر السعر أو الشحن أو العرض الآن — انتظر حتى يكتمل شرط إعادة الفحص."
        ),
        reasoning_summary=(
            "إصدار توصية بدون كفاية أدلة يوجّه قرارات المتجر على عينة غير موثوقة."
        ),
        merchant_action=observe_ar,
        recheck_condition=unlock_ar,
        confidence_state=STATE_INSUFFICIENT,
        expected_monitored_outcome="ظهور نمط تردد واضح بما يكفي لفتح قرار محكوم.",
        generated_at=generated_at,
    )


def compose_communication_followup_v1(
    *,
    store_slug: str,
    no_phone: int,
    generated_at: str = "",
) -> dict[str, Any]:
    n = max(0, int(no_phone))
    return _guidance(
        store_slug=store_slug,
        family=FAMILY_COMMUNICATION_FOLLOWUP,
        guidance_id=f"ogl:comm:no_phone:{store_slug or 'store'}",
        subject="store",
        evidence_refs=[f"teaser:no_phone:{n}"],
        evidence_summary_ar=(
            f"يوجد {n} سلة تحتاج متابعة لكن رقم التواصل غير متاح."
            if n
            else "متابعة بعض العملاء مقيدة لعدم توفر رقم التواصل."
        ),
        diagnosis=(
            "مسار الاسترجاع عبر التواصل متوقف لأن بيانات الاتصال ناقصة."
        ),
        recommendation=(
            "لا تعتمد على رسائل جديدة قبل تأمين وسيلة تواصل صالحة للسلال المعنية."
        ),
        reasoning_summary=(
            "بدون رقم أو قناة اتصال، لا يمكن إكمال متابعة الاسترجاع لهؤلاء العملاء."
        ),
        merchant_action=(
            "افتح التواصل واجمع وسيلة اتصال صالحة للسلال التي تظهر بلا رقم."
        ),
        recheck_condition=(
            "أعد الفحص عندما يصبح عدد السلال بلا رقم = 0، أو بعد تأمين قناة تواصل "
            "لأي سلة ذات أولوية."
        ),
        confidence_state=STATE_ACTIVE,
        expected_monitored_outcome="انخفاض السلال بلا رقم وبدء متابعة استرجاع قابلة للتنفيذ.",
        generated_at=generated_at,
    )


def compose_from_hesitation_distribution_v1(
    *,
    store_slug: str,
    total: int,
    distribution: Mapping[str, int],
    generated_at: str = "",
) -> Optional[dict[str, Any]]:
    total_i = max(0, int(total))
    dist = {str(k).lower(): _as_int(v) for k, v in dict(distribution or {}).items()}
    if total_i < MIN_HESITATION_TOTAL or not dist:
        return compose_wait_insufficient_v1(
            store_slug=store_slug,
            missing_ar=(
                f"عدد أسباب التردد المسجّلة ({total_i}) أقل من الحد الآمن "
                f"({MIN_HESITATION_TOTAL})."
            ),
            observe_ar=(
                "استمر في تشغيل الودجيت لجمع أسباب تردد مؤهّلة دون تغيير السعر أو الشحن."
            ),
            unlock_ar=(
                f"أعد القرار عندما يصل إجمالي أسباب التردد إلى {MIN_HESITATION_TOTAL} "
                f"على الأقل خلال نافذة المراقبة الحالية."
            ),
            evidence_refs=[f"hesitation_total:{total_i}"],
            generated_at=generated_at,
        )

    top_reason, top_count = max(dist.items(), key=lambda kv: kv[1])
    share = top_count / max(total_i, 1)
    if top_count < MIN_DOMINANT_COUNT or share < MIN_DOMINANT_SHARE:
        return compose_wait_insufficient_v1(
            store_slug=store_slug,
            missing_ar=(
                f"أسباب التردد موزّعة ({top_reason}:{top_count}/{total_i}) بلا سبب مهيمن."
            ),
            observe_ar=(
                "لا تركّز على سبب واحد بعد — راقب التوزيع دون تغيير العرض."
            ),
            unlock_ar=(
                f"أعد القرار إذا بلغ سبب واحد ≥ {MIN_DOMINANT_COUNT} حالات "
                f"وحصة ≥ {int(MIN_DOMINANT_SHARE * 100)}٪ من العينة."
            ),
            evidence_refs=[f"hesitation_dist:{top_reason}:{top_count}/{total_i}"],
            generated_at=generated_at,
        )

    label = REASON_LABEL_AR.get(top_reason, top_reason)
    if top_reason in ("shipping", "delivery"):
        family = FAMILY_SHIPPING_FRICTION
        diagnosis = (
            f"السبب الأكثر تكراراً للتردّد هو {label} "
            f"({top_count} من {total_i}، {share:.0%}). "
            "هذا نمط ارتباط وليس إثبات سبب جذري نهائي."
        )
        recommendation = (
            "لا تغيّر سعر الشحن أو مدته الآن. افصل أولاً بين اعتراض التكلفة ومدة التوصيل "
            "عبر الأسئلة المؤهّلة في الودجيت."
        )
        action = (
            f"راجع نصوص سبب «{label}» في سياسة الاسترجاع والودجيت للتوضيح فقط — "
            "بدون خصم أو شحن مجاني حتى يتحقق شرط إعادة الفحص."
        )
        outcome = "انخفاض اعتراضات الشحن/التوصيل مع استمرار العملاء بعد خطوة الشحن."
    elif top_reason == "price":
        family = FAMILY_PRICE_HESITATION
        diagnosis = (
            f"السبب الأكثر تكراراً للتردّد هو السعر "
            f"({top_count} من {total_i}، {share:.0%}). "
            "النمط لا يثبت وحده أن الخصم هو الحل الصحيح."
        )
        recommendation = (
            "لا تخفّض السعر أو تطلق خصماً عاماً الآن. ثبّت وضوح القيمة والعرض أولاً."
        )
        action = (
            "افحص صفحة المنتج/العرض المرتبط بالسعر وعدّل الوضوح فقط؛ أعد قياس حصة "
            "سبب السعر بعد ذلك."
        )
        outcome = "انخفاض حصة سبب السعر بين أسباب التردد المؤهّلة."
    elif top_reason in ("quality", "warranty"):
        family = FAMILY_PRODUCT_CONFIDENCE
        diagnosis = (
            f"السبب الأكثر تكراراً للتردّد هو {label} "
            f"({top_count} من {total_i}، {share:.0%})."
        )
        recommendation = (
            "لا تغيّر التسعير. حسّن وضوح الجودة/الضمان في صفحة المنتج قبل أي عرض تجاري."
        )
        action = (
            f"حدّث وصف {label} الظاهر للعميل في المتجر والودجيت، ثم راقب حصة هذا السبب."
        )
        outcome = f"انخفاض حصة سبب {label} مع بقاء الاهتمام بالمنتج."
    else:
        return compose_wait_insufficient_v1(
            store_slug=store_slug,
            missing_ar=(
                f"السبب الأعلى ({label}) لا يملك عائلة توجيه مدعومة بالكامل بعد."
            ),
            observe_ar="استمر في جمع الأدلة دون تغييرات سعر/شحن.",
            unlock_ar=(
                "أعد القرار عند ظهور نمط شحن أو سعر أو جودة بحدود الكفاية المعتمدة."
            ),
            evidence_refs=[f"hesitation_dist:{top_reason}:{top_count}/{total_i}"],
            generated_at=generated_at,
        )

    return _guidance(
        store_slug=store_slug,
        family=family,
        guidance_id=f"ogl:hesitation:{top_reason}:{store_slug or 'store'}",
        subject="store",
        evidence_refs=[
            f"hesitation_total:{total_i}",
            f"hesitation_top:{top_reason}:{top_count}",
            f"hesitation_share:{share:.2f}",
        ],
        evidence_summary_ar=(
            f"{label} يتكرر في {top_count} من أصل {total_i} سبب مسجّل ({share:.0%})."
        ),
        diagnosis=diagnosis,
        recommendation=recommendation,
        reasoning_summary=(
            "الاعتماد على السبب الأكثر تكراراً موجّه للمراقبة والتحقيق — "
            "وليس لإثبات علاقة سببية كاملة."
        ),
        merchant_action=action,
        recheck_condition=(
            f"أعد القرار بعد جمع عيّنة جديدة ≥ {MIN_HESITATION_TOTAL}، "
            f"وإذا بقيت حصة {label} ≥ {int(MIN_DOMINANT_SHARE * 100)}٪ "
            "دون انخفاض واضح."
        ),
        confidence_state=STATE_ACTIVE,
        expected_monitored_outcome=outcome,
        generated_at=generated_at,
    )


def compose_from_diagnostic_publication_v1(
    *,
    store_slug: str,
    pub: Mapping[str, Any],
    generated_at: str = "",
) -> dict[str, Any]:
    family_dx = str(pub.get("diagnostic_family") or "")
    status = str(pub.get("diagnosis_status") or "")
    obs = _norm(pub.get("observation_ar"))
    diag = _norm(pub.get("diagnosis_ar"))
    rec = _norm(pub.get("recommendation_ar"))
    conf = str(pub.get("confidence_level") or "") or STATE_INSUFFICIENT

    if family_dx == FAMILY_CONTACT_FOLLOWUP_BLOCKED:
        return compose_communication_followup_v1(
            store_slug=store_slug,
            no_phone=1,
            generated_at=generated_at,
        )

    if status != DIAGNOSIS_STATUS_SUPPORTED or not diag:
        return compose_wait_insufficient_v1(
            store_slug=store_slug,
            missing_ar=obs or diag or "الأدلة التشخيصية غير كافية بعد.",
            observe_ar=(
                "راقب الحالات الجديدة دون تغيير السعر أو الشحن حتى تتضح الأدلة."
            ),
            unlock_ar=(
                "أعد القرار عندما يصبح التشخيص مدعوماً بأدلة كافية وغير متعارضة."
            ),
            evidence_refs=[
                f"diagnostic:{pub.get('diagnostic_id') or family_dx or 'unknown'}",
                f"diagnosis_status:{status or DIAGNOSIS_STATUS_INSUFFICIENT}",
            ],
            generated_at=generated_at,
        )

    if family_dx == FAMILY_CHECKOUT_AFTER_SHIPPING:
        ogl_family = FAMILY_SHIPPING_FRICTION
        recommendation = (
            "لا تغيّر تكلفة الشحن الآن. ثبّت أي اعتراض مهيمن (تكلفة مقابل مدة) قبل أي اختبار."
            if is_bare_generic_recommendation_ar(rec) or not rec
            else rec
        )
        action = (
            "وضّح تكلفة ومدة الشحن للعميل في المسار الحالي، ثم راقب اعتراضات الشحن/التوصيل."
        )
        recheck = (
            "أعد القرار عندما تتوفر عيّنة تردد كافية ويظهر سبب شحن أو توصيل مهيمن "
            f"(≥ {MIN_DOMINANT_COUNT} و≥ {int(MIN_DOMINANT_SHARE * 100)}٪)."
        )
        outcome = "استمرار العملاء بعد خطوة الشحن مع انخفاض اعتراضات الشحن."
    elif family_dx == FAMILY_INTEREST_WITHOUT_PURCHASE:
        ogl_family = FAMILY_PRODUCT_CONFIDENCE
        recommendation = (
            "لا تطلق خصماً. حسّن وضوح المنتج والجودة قبل أي عرض سعري."
            if is_bare_generic_recommendation_ar(rec) or not rec
            else rec
        )
        action = "راجع صفحة المنتج الأكثر ظهوراً في الاهتمام وعدّل وضوح الجودة/المواصفات فقط."
        recheck = (
            "أعد القرار بعد عيّنة تردد جديدة ≥ "
            f"{MIN_HESITATION_TOTAL} مع استمرار فجوة الاهتمام→الشراء."
        )
        outcome = "ارتفاع إتمام الشراء للمنتجات ذات الاهتمام المرتفع."
    else:
        ogl_family = FAMILY_WAIT_INSUFFICIENT
        recommendation = (
            "لا تغيّر العرض التجاري الآن — الدليل التشخيصي لا يفتح عائلة توجيه مدعومة بالكامل."
        )
        action = "واصل جمع الأدلة عبر الودجيت ومسار السلة دون تغييرات سعر/شحن."
        recheck = "أعد القرار عند ظهور عائلة تشخيص مدعومة (شحن / سعر / تواصل / جودة)."
        outcome = "توفر تشخيص مدعوم بما يكفي لفتح توجيه محكوم."

    # Upgrade bare diagnostic recs into grounded recommendation text.
    if is_bare_generic_recommendation_ar(recommendation):
        recommendation = (
            "لا تتخذ إجراءً تجارياً واسعاً الآن؛ نفّذ خطوة التوضيح المحددة أدناه ثم أعد الفحص."
        )

    conf_state = STATE_ACTIVE if conf in ("high", "medium", "low", "") else STATE_INSUFFICIENT
    if conf in ("insufficient",):
        conf_state = STATE_INSUFFICIENT

    return _guidance(
        store_slug=store_slug,
        family=ogl_family,
        guidance_id=f"ogl:dx:{pub.get('diagnostic_id') or family_dx or 'pub'}",
        subject=str(pub.get("subject_type") or "store"),
        evidence_refs=[
            f"diagnostic:{pub.get('diagnostic_id') or family_dx}",
            f"diagnosis_status:{status}",
        ],
        evidence_summary_ar=obs or diag,
        diagnosis=diag,
        recommendation=recommendation,
        reasoning_summary=(
            "التوجيه مبني على التشخيص المنشور فقط — بدون افتراض رفع إيراد أو علاقة سببية زائدة."
        ),
        merchant_action=action,
        recheck_condition=recheck,
        confidence_state=conf_state,
        expected_monitored_outcome=outcome,
        generated_at=generated_at or str(pub.get("generated_at") or "") or _now_iso(),
    )


def compose_operational_guidance_v1(
    summary: Mapping[str, Any] | None,
    *,
    store_slug: str = "",
    generated_at: str = "",
) -> dict[str, Any]:
    """Pick the strongest safe guidance from available summary truth."""
    src = summary if isinstance(summary, Mapping) else {}
    slug = str(store_slug or src.get("store_slug") or "").strip()
    ts = generated_at or _now_iso()
    teasers = _teasers(src)
    health = teasers.get("health") if isinstance(teasers.get("health"), Mapping) else {}
    no_phone = _as_int(health.get("no_phone"))

    # 1) Contact block — operational and actionable now.
    if no_phone > 0:
        return compose_communication_followup_v1(
            store_slug=slug, no_phone=no_phone, generated_at=ts
        )

    # 2) Hesitation distribution when present on summary (tests / optional attach).
    total, dist = _hesitation_from_summary(src)
    if total or dist:
        g = compose_from_hesitation_distribution_v1(
            store_slug=slug, total=total, distribution=dist, generated_at=ts
        )
        if g is not None:
            return g

    # 3) Diagnostic publication already attached to summary.
    pub = src.get("diagnostic_publication_v1")
    if isinstance(pub, Mapping) and (
        _norm(pub.get("diagnosis_ar")) or _norm(pub.get("observation_ar"))
    ):
        return compose_from_diagnostic_publication_v1(
            store_slug=slug, pub=pub, generated_at=ts
        )

    # 4) Honest insufficient default.
    return compose_wait_insufficient_v1(
        store_slug=slug,
        missing_ar="لا تتوفر بعد أدلة تردد أو تشخيص منشور كافٍ لقرار تشغيلي.",
        observe_ar=(
            "اترك الودجيت ومسار الاسترجاع يعملان لجمع أدلة مؤهّلة — بدون تغيير السعر أو الشحن."
        ),
        unlock_ar=(
            f"أعد القرار عند توفر تشخيص مدعوم، أو عند وصول أسباب التردد إلى "
            f"{MIN_HESITATION_TOTAL} على الأقل."
        ),
        evidence_refs=["summary:no_guidance_evidence"],
        generated_at=ts,
    )


def attach_operational_guidance_to_summary_v1(
    summary: dict[str, Any],
    *,
    store_slug: str = "",
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return summary
    slug = str(store_slug or summary.get("store_slug") or "").strip()
    guidance = compose_operational_guidance_v1(summary, store_slug=slug)
    summary["operational_guidance_v1"] = guidance
    # Enrich HES package when present.
    hes = summary.get("home_executive_summary_v1")
    if isinstance(hes, dict) and hes.get("ok"):
        hes["operational_guidance_v1"] = {
            "ok": bool(guidance.get("ok")),
            "guidance_id": guidance.get("guidance_id"),
            "family": guidance.get("family"),
            "confidence_state": guidance.get("confidence_state"),
            "home_surface": dict(guidance.get("home_surface") or {}),
        }
        summary["home_executive_summary_v1"] = hes
    return summary


def project_guidance_onto_workspace_card_v1(
    card: Mapping[str, Any] | None,
    guidance: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Attach workspace guidance fields without duplicating Home executive copy."""
    out = dict(card) if isinstance(card, Mapping) else {}
    g = guidance if isinstance(guidance, Mapping) else {}
    ws = g.get("workspace_surface") if isinstance(g.get("workspace_surface"), Mapping) else {}
    if not g.get("ok"):
        return out
    if ws.get("evidence_ar"):
        out["evidence_lines_ar"] = [ws["evidence_ar"]]
    if ws.get("diagnosis_ar"):
        out["diagnosis_ar"] = ws["diagnosis_ar"]
    if ws.get("recommendation_ar"):
        out["operational_guidance_ar"] = ws["recommendation_ar"]
    if ws.get("why_ar"):
        out["why_ar"] = ws["why_ar"]
    if ws.get("recheck_condition_ar"):
        out["recheck_condition_ar"] = ws["recheck_condition_ar"]
        # Keep wait lines honest and specific.
        out["action_wait_lines_ar"] = [
            f"أعد الفحص: {ws['recheck_condition_ar']}",
        ]
    if ws.get("action_ar"):
        out["decision_sentence_ar"] = ws["action_ar"]
    out["operational_guidance_v1"] = {
        "guidance_id": g.get("guidance_id"),
        "family": g.get("family"),
        "workspace_surface": dict(ws),
    }
    return out


__all__ = [
    "attach_operational_guidance_to_summary_v1",
    "compose_communication_followup_v1",
    "compose_from_diagnostic_publication_v1",
    "compose_from_hesitation_distribution_v1",
    "compose_operational_guidance_v1",
    "compose_wait_insufficient_v1",
    "project_guidance_onto_workspace_card_v1",
]
