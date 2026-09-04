# -*- coding: utf-8 -*-
"""
Commercial Opportunity Layer V1 — compose from production summary truth only.

No AI, no external APIs, no simulation missions on /dashboard.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.commercial_opportunity_layer_v1.contract_v1 import (
    EMPTY_STATE_AR,
    FAMILY_COMMUNICATION_FOLLOWUP,
    FAMILY_PRICE_HESITATION,
    FAMILY_PRODUCT_CONFIDENCE,
    FAMILY_RECOVERY_HESITATION,
    FAMILY_SHIPPING_FRICTION,
    LAYER_SCHEMA,
    LAYER_VERSION,
    OPPORTUNITY_SCHEMA,
    PARTIAL_GAP_PREFIX_AR,
    PRIMARY_EYEBROW_AR,
    TRUTH_INSUFFICIENT,
    TRUTH_PRODUCTION_PARTIAL,
    TRUTH_PRODUCTION_READY,
    TRUTH_SIMULATION_ONLY,
    empty_package_v1,
    package_has_simulation_leak,
    validate_opportunity_v1,
)
from services.commercial_opportunity_layer_v1.priority_v1 import (
    priority_explanation_ar,
    score_opportunity_v1,
)
from services.commercial_opportunity_layer_v1.truth_gate_v1 import (
    classify_communication_truth_v1,
    classify_hesitation_truth_v1,
    may_render_on_merchant_home,
    summary_marks_simulation,
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

# Map raw reason keys → commercial family (lab-only families excluded).
_REASON_FAMILY = {
    "shipping": FAMILY_SHIPPING_FRICTION,
    "delivery": FAMILY_SHIPPING_FRICTION,
    "price": FAMILY_PRICE_HESITATION,
    "quality": FAMILY_PRODUCT_CONFIDENCE,
    "warranty": FAMILY_PRODUCT_CONFIDENCE,
    "thinking": FAMILY_RECOVERY_HESITATION,
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


def _hesitation_counts(summary: Mapping[str, Any]) -> tuple[int, dict[str, int]]:
    for key in (
        "hesitation_evidence_v1",
        "operational_guidance_evidence_v1",
        "merchant_reason_counts_week",
    ):
        blob = summary.get(key)
        if key == "merchant_reason_counts_week" and isinstance(blob, Mapping):
            dist = {
                str(k).strip().lower(): _as_int(v)
                for k, v in blob.items()
                if str(k).strip()
            }
            total = sum(dist.values())
            if total or dist:
                return total, dist
            continue
        if not isinstance(blob, Mapping):
            continue
        total = _as_int(blob.get("hesitation_total"))
        dist_raw = blob.get("hesitation_distribution") or blob.get("distribution")
        dist: dict[str, int] = {}
        if isinstance(dist_raw, Mapping):
            for k, v in dist_raw.items():
                kk = str(k).strip().lower()
                if kk:
                    dist[kk] = _as_int(v)
        if not dist and key == "merchant_reason_counts_week":
            continue
        if total or dist:
            if not total:
                total = sum(dist.values())
            return total, dist
    # Nested counts on hesitation blob shaped as flat reason→count
    raw = summary.get("merchant_reason_counts_week")
    if isinstance(raw, Mapping) and raw:
        dist = {
            str(k).strip().lower(): _as_int(v)
            for k, v in raw.items()
            if str(k).strip()
        }
        return sum(dist.values()), dist
    return 0, {}


def _teaser_health(summary: Mapping[str, Any]) -> dict[str, Any]:
    teasers = summary.get("home_teaser_inputs_v1")
    if not isinstance(teasers, Mapping):
        return {}
    health = teasers.get("health")
    return dict(health) if isinstance(health, Mapping) else {}


def _decision_contract(
    *,
    title: str,
    why_now: str,
    do_this: str,
    dont: str,
    measure: str,
    recheck: str,
) -> dict[str, str]:
    return {
        "decision_ar": title,
        "why_now_ar": why_now,
        "do_this_ar": do_this,
        "dont_ar": dont,
        "measure_ar": measure,
        "recheck_ar": recheck,
    }


def _build_hesitation_opportunity(
    *,
    store_slug: str,
    reason: str,
    count: int,
    total: int,
    truth_class: str,
    generated_at: str,
) -> Optional[dict[str, Any]]:
    if truth_class in (TRUTH_INSUFFICIENT, TRUTH_SIMULATION_ONLY):
        return None
    family = _REASON_FAMILY.get(reason)
    if not family:
        return None
    label = REASON_LABEL_AR.get(reason, reason)
    share = count / max(total, 1)
    share_pct = int(round(share * 100))
    constrained = truth_class == TRUTH_PRODUCTION_PARTIAL
    gap = PARTIAL_GAP_PREFIX_AR if constrained else ""

    if family == FAMILY_SHIPPING_FRICTION:
        title = f"{gap}توضيح احتكاك الشحن قبل أي تغيير سعر"
        why = f"«{label}» {count}/{total} ({share_pct}٪) — يقطع الشراء عند الشحن."
        action = "افصل في الودجيت بين تكلفة الشحن ومدة التوصيل — بلا خصم."
        dont = "لا تخفّض الشحن أو تجعله مجانيًا قبل فصل الاعتراض."
        measure = f"حصة أسباب الشحن/التوصيل خلال 7 أيام (الآن {share_pct}٪)."
        objective = "تقليل التسرب عند خطوة الشحن"
    elif family == FAMILY_PRICE_HESITATION:
        title = f"{gap}تثبيت وضوح القيمة قبل أي خصم"
        why = f"السعر الأعلى ({count}/{total}، {share_pct}٪) — لا يثبت أن الخصم يرفع الإيراد."
        action = "وضّح العرض في صفحة المنتج — بلا خصم عام."
        dont = "لا تطلق خصمًا عامًا الآن."
        measure = f"حصة سبب السعر (الآن {share_pct}٪)."
        objective = "خفض تردد السعر دون حرق هامش"
    elif family == FAMILY_PRODUCT_CONFIDENCE:
        title = f"{gap}تحسين ثقة المنتج الظاهرة"
        why = f"«{label}» {count}/{total} ({share_pct}٪) كسبب تردد."
        action = f"حدّث وصف {label} في المتجر والودجيت فقط."
        dont = "لا تغيّر التسعير لهذا النمط."
        measure = f"حصة سبب {label} بعد التحديث (أساس {share_pct}٪)."
        objective = "رفع ثقة المنتج"
    else:  # recovery hesitation / thinking
        title = f"{gap}متابعة من يترددون قبل الشراء"
        why = f"«{label}» {count}/{total} ({share_pct}٪) — متابعة استرجاع محدودة القياس."
        action = "راجع رسالة المتابعة الأولى لهذه الشريحة — بلا خصم جديد."
        dont = "لا تفترض أن الخصم مطلوب لكل متردد."
        measure = "متابعات هذه الشريحة + تغيّر حصة السبب خلال 7 أيام."
        objective = "استرجاع المترددين بمتابعة واضحة"

    recheck = (
        f"بعد عيّنة ≥ 8، أو انخفاض واضح في حصة «{label}»."
        if not constrained
        else f"عندما تكتمل العيّنة وتبقى «{label}» مهيمنة."
    )
    opp: dict[str, Any] = {
        "schema": OPPORTUNITY_SCHEMA,
        "opportunity_id": f"col:{family}:{reason}:{store_slug or 'store'}",
        "family": family,
        "truth_class": truth_class,
        "title_ar": _norm(title),
        "why_ar": _norm(why),
        "action_ar": _norm(action),
        "measure_ar": _norm(measure),
        "recheck_ar": _norm(recheck),
        "objective_ar": _norm(objective),
        "eyebrow_ar": PRIMARY_EYEBROW_AR,
        "priority_why_ar": priority_explanation_ar(
            {"family": family, "truth_class": truth_class}
        ),
        "evidence": {
            "lines_ar": [
                f"أسباب التردد (7 أيام): {total}",
                f"الأعلى: {label} — {count} ({share_pct}٪)",
                "مصدر: سجل أسباب متجرك.",
            ],
            "counts": {
                "hesitation_total": total,
                "top_reason": reason,
                "top_count": count,
                "top_share": round(share, 4),
            },
        },
        "decision_contract_ar": _decision_contract(
            title=_norm(title),
            why_now=_norm(why),
            do_this=_norm(action),
            dont=_norm(dont),
            measure=_norm(measure),
            recheck=_norm(recheck),
        ),
        "workspace_href": "#workspace",
        "generated_at": generated_at,
        "_urgency": min(20, count),
        "_evidence_strength": 20 if truth_class == TRUTH_PRODUCTION_READY else 8,
    }
    return opp


def _build_communication_opportunity(
    *,
    store_slug: str,
    no_phone: int,
    truth_class: str,
    generated_at: str,
) -> Optional[dict[str, Any]]:
    if truth_class in (TRUTH_INSUFFICIENT, TRUTH_SIMULATION_ONLY):
        return None
    constrained = truth_class == TRUTH_PRODUCTION_PARTIAL
    gap = PARTIAL_GAP_PREFIX_AR if constrained else ""
    title = f"{gap}تأمين وسيلة تواصل للسلال المعلّقة"
    why = f"{no_phone} سلة بلا تواصل صالح — المتابعة متعذّرة."
    action = "اجمع وسيلة اتصال للسلال ذات الأولوية بلا رقم."
    dont = "لا ترسل حملات عامة قبل سد فجوة التواصل."
    measure = "عدد السلال بلا رقم (هدف: انخفاض نحو صفر)."
    recheck = "عندما يصبح العدد = 0 أو تُؤمَّن قناة لسلة ذات أولوية."
    family = FAMILY_COMMUNICATION_FOLLOWUP
    return {
        "schema": OPPORTUNITY_SCHEMA,
        "opportunity_id": f"col:{family}:no_phone:{store_slug or 'store'}",
        "family": family,
        "truth_class": truth_class,
        "title_ar": _norm(title),
        "why_ar": _norm(why),
        "action_ar": _norm(action),
        "measure_ar": _norm(measure),
        "recheck_ar": _norm(recheck),
        "objective_ar": "تمكين متابعة الاسترجاع",
        "eyebrow_ar": PRIMARY_EYEBROW_AR,
        "priority_why_ar": priority_explanation_ar(
            {"family": family, "truth_class": truth_class}
        ),
        "evidence": {
            "lines_ar": [
                f"سلال بلا رقم: {no_phone}",
                "مصدر: صحة سلال المتجر.",
            ],
            "counts": {"no_phone": no_phone},
        },
        "decision_contract_ar": _decision_contract(
            title=_norm(title),
            why_now=_norm(why),
            do_this=_norm(action),
            dont=_norm(dont),
            measure=_norm(measure),
            recheck=_norm(recheck),
        ),
        "workspace_href": "#workspace",
        "generated_at": generated_at,
        "_urgency": min(20, no_phone * 3),
        "_evidence_strength": 18 if truth_class == TRUTH_PRODUCTION_READY else 7,
    }


def _finalize_opp(opp: dict[str, Any]) -> Optional[dict[str, Any]]:
    errors = validate_opportunity_v1(opp)
    if errors:
        return None
    if not may_render_on_merchant_home(str(opp.get("truth_class") or "")):
        return None
    # Strip internal scoring helpers from merchant payload later
    return opp


def compose_commercial_opportunity_layer_v1(
    summary: Mapping[str, Any] | None,
    *,
    store_slug: str = "",
    generated_at: str = "",
) -> dict[str, Any]:
    src = summary if isinstance(summary, Mapping) else {}
    slug = str(store_slug or src.get("store_slug") or "").strip()
    ts = generated_at or _now_iso()
    sim = summary_marks_simulation(src)

    candidates: list[dict[str, Any]] = []
    suppressed: list[dict[str, str]] = []

    total, dist = _hesitation_counts(src)
    if sim and (total or dist):
        suppressed.append(
            {
                "family": "hesitation",
                "truth_class": TRUTH_SIMULATION_ONLY,
                "reason": "simulation_marked_summary",
            }
        )
    elif dist:
        # Merge delivery into shipping for ranking display preference
        merged = dict(dist)
        if "delivery" in merged:
            merged["shipping"] = merged.get("shipping", 0) + merged.pop("delivery")
        top_reason, top_count = max(merged.items(), key=lambda kv: kv[1])
        share = top_count / max(total, 1)
        tc = classify_hesitation_truth_v1(
            total=total, top_count=top_count, share=share, simulation=sim
        )
        if tc == TRUTH_INSUFFICIENT:
            suppressed.append(
                {
                    "family": _REASON_FAMILY.get(top_reason, top_reason),
                    "truth_class": tc,
                    "reason": f"weak_hesitation:{top_reason}:{top_count}/{total}",
                }
            )
        else:
            opp = _build_hesitation_opportunity(
                store_slug=slug,
                reason=top_reason,
                count=top_count,
                total=total,
                truth_class=tc,
                generated_at=ts,
            )
            if opp:
                # Secondaries from next reasons with enough evidence
                ranked_reasons = sorted(
                    merged.items(), key=lambda kv: kv[1], reverse=True
                )
                for reason, cnt in ranked_reasons:
                    if reason == top_reason:
                        continue
                    sh = cnt / max(total, 1)
                    tc2 = classify_hesitation_truth_v1(
                        total=total, top_count=cnt, share=sh, simulation=sim
                    )
                    if tc2 == TRUTH_INSUFFICIENT:
                        continue
                    # Secondaries: allow PARTIAL only if count >= 3
                    if tc2 == TRUTH_PRODUCTION_PARTIAL and cnt < 3:
                        continue
                    o2 = _build_hesitation_opportunity(
                        store_slug=slug,
                        reason=reason,
                        count=cnt,
                        total=total,
                        truth_class=tc2,
                        generated_at=ts,
                    )
                    if o2:
                        candidates.append(o2)
                candidates.insert(0, opp)

    health = _teaser_health(src)
    no_phone = _as_int(health.get("no_phone"))
    if no_phone:
        tc_c = classify_communication_truth_v1(no_phone=no_phone, simulation=sim)
        if tc_c == TRUTH_INSUFFICIENT:
            suppressed.append(
                {
                    "family": FAMILY_COMMUNICATION_FOLLOWUP,
                    "truth_class": tc_c,
                    "reason": f"no_phone:{no_phone}",
                }
            )
        else:
            c_opp = _build_communication_opportunity(
                store_slug=slug,
                no_phone=no_phone,
                truth_class=tc_c,
                generated_at=ts,
            )
            if c_opp:
                candidates.append(c_opp)

    finalized: list[dict[str, Any]] = []
    for raw in candidates:
        done = _finalize_opp(dict(raw))
        if done:
            finalized.append(done)
        else:
            suppressed.append(
                {
                    "family": str(raw.get("family") or ""),
                    "truth_class": str(raw.get("truth_class") or ""),
                    "reason": "validation_failed",
                }
            )

    # Dedupe by family — keep highest score
    by_family: dict[str, dict[str, Any]] = {}
    for opp in finalized:
        fam = str(opp.get("family") or "")
        prev = by_family.get(fam)
        if prev is None or score_opportunity_v1(opp) > score_opportunity_v1(prev):
            by_family[fam] = opp
    ranked = sorted(by_family.values(), key=score_opportunity_v1, reverse=True)

    # Prefer READY for primary; never fill with weak noise
    ready = [o for o in ranked if o.get("truth_class") == TRUTH_PRODUCTION_READY]
    partial = [o for o in ranked if o.get("truth_class") == TRUTH_PRODUCTION_PARTIAL]
    ordered = ready + partial

    primary = ordered[0] if ordered else None
    secondaries = ordered[1:3] if primary else []

    def _public(opp: dict[str, Any] | None) -> dict[str, Any] | None:
        if not opp:
            return None
        out = {k: v for k, v in opp.items() if not str(k).startswith("_")}
        return out

    pkg = empty_package_v1(enabled=True)
    pkg.update(
        {
            "ok": True,
            "schema": LAYER_SCHEMA,
            "layer_version": LAYER_VERSION,
            "store_slug": slug,
            "generated_at": ts,
            "primary": _public(primary),
            "secondaries": [_public(s) for s in secondaries if s],
            "empty": primary is None,
            "empty_state_ar": EMPTY_STATE_AR,
            "suppressed": suppressed[:12],
            "cost": {
                "ai_calls": 0,
                "external_api_calls": 0,
                "estimated_extra_queries": 0,
                "path": "summary_truth→bounded_candidates→rank→materialize",
            },
        }
    )
    if package_has_simulation_leak(pkg):
        return empty_package_v1(
            enabled=True, reason="simulation_leak_blocked"
        )
    return pkg


__all__ = ["compose_commercial_opportunity_layer_v1"]
