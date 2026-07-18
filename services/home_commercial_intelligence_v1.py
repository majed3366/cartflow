# -*- coding: utf-8 -*-
"""
Home Commercial Intelligence Transition V1.

Transforms Home admission from "data exists" to "answers a commercial question."

Does not redesign UI/cards/ACF. Injects governed Business Findings into existing
Home section shapes with Commercial Question → Answer → Evidence → Confidence →
Merchant Meaning → Action.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping, MutableMapping, Optional

from services.commercial_question_registry_v1 import (
    DIM_CONTACT,
    DIM_DATA,
    DIM_HESITATION,
    DIM_KNOWLEDGE,
    DIM_PRODUCTS,
    DIM_RECOVERY,
    DIM_TRAFFIC,
    DIM_WHATSAPP,
    REGISTRY_VERSION,
    resolve_question_for_finding_v1,
)

log = logging.getLogger("cartflow.home_commercial_intel")

ENGINE_VERSION = "home_commercial_intelligence_v1"

# Dimensions that prove commercial diversity (contact alone = fail).
_DIVERSITY_CORE = (
    DIM_PRODUCTS,
    DIM_HESITATION,
    DIM_TRAFFIC,
    DIM_RECOVERY,
    DIM_WHATSAPP,
    DIM_KNOWLEDGE,
    DIM_DATA,
)

_OPERATIONAL_BANNED = (
    "عدد السلال",
    "سلة نشطة",
    "تم إرسال",
    "how many carts",
    "cart count",
    "waiting_send",
)


def _norm(v: Any) -> str:
    return str(v or "").strip()


def insight_has_commercial_evidence_model_v1(insight: Mapping[str, Any]) -> bool:
    """Every visible insight must carry the full commercial evidence model."""
    required = (
        "commercial_question_id",
        "commercial_question_ar",
        "commercial_answer_ar",
        "evidence_ar",
        "confidence",
        "merchant_meaning_ar",
    )
    for key in required:
        if not _norm(insight.get(key)):
            return False
    # Insufficient is allowed when explicitly marked.
    conf = _norm(insight.get("confidence")).lower()
    if conf in ("insufficient", "unknown", ""):
        if not insight.get("insufficient_evidence_ok"):
            return False
    return True


def rejects_operational_restatement_v1(text: str) -> bool:
    blob = _norm(text).lower()
    if not blob:
        return True
    return any(tok.lower() in blob for tok in _OPERATIONAL_BANNED) and (
        "لأن" not in blob and "يعني" not in blob and "استنتاج" not in blob
    )


def finding_to_commercial_insight_v1(
    finding: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    """Project a Business Finding into a Home commercial insight."""
    q = resolve_question_for_finding_v1(finding)
    if not q:
        return None
    answer = _norm(finding.get("merchant_summary") or finding.get("title"))
    evidence = _norm(finding.get("evidence_summary"))
    meaning = _norm(finding.get("commercial_meaning") or finding.get("business_impact"))
    action = _norm(finding.get("recommended_direction"))
    conf = _norm(finding.get("confidence_level") or finding.get("confidence")) or "insufficient"
    status = _norm(finding.get("status")).lower()
    insufficient_ok = bool(
        q.get("allows_insufficient")
        or status in ("insufficient_evidence", "conflicting_evidence")
        or conf == "insufficient"
    )
    if not answer or not evidence:
        return None
    if not meaning and not insufficient_ok:
        return None
    if rejects_operational_restatement_v1(answer) and not meaning:
        return None

    dim = _norm(q.get("dimension"))
    insight = {
        "commercial_question_id": q["question_id"],
        "commercial_question_ar": q["question_ar"],
        "commercial_dimension": dim,
        "commercial_answer_ar": answer,
        "evidence_ar": evidence,
        "confidence": conf,
        "merchant_meaning_ar": meaning
        or ("الأدلة غير كافية بعد لاستنتاج تجاري مؤكد." if insufficient_ok else ""),
        "recommended_action_ar": action,
        "insufficient_evidence_ok": insufficient_ok,
        "finding_id": _norm(finding.get("finding_id")),
        "finding_type": _norm(finding.get("finding_type")),
        "family_key": _norm(finding.get("family_key")),
        "truth_id": _norm(finding.get("finding_id") or finding.get("finding_type")),
        "knowledge_id": _norm(finding.get("finding_id")),
        "fact_key": f"fact:finding:{_norm(finding.get('finding_type'))}",
        "insight_key": _norm(finding.get("finding_type")),
        "merchant_problem": _norm(finding.get("finding_type"))
        or _norm(finding.get("family_key")),
        "semantic_topic": _norm(finding.get("family_key"))
        or _norm(finding.get("finding_type")),
        "sample_size": int(finding.get("sample_size") or 0),
        "recommendation_type": _norm(finding.get("recommendation_type")),
        "registry_version": REGISTRY_VERSION,
        "engine": ENGINE_VERSION,
        "ai_used": False,
    }
    if not insight_has_commercial_evidence_model_v1(insight):
        return None
    return insight


def _understanding_item_from_insight(insight: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "observation_ar": insight["commercial_answer_ar"],
        "title_ar": insight["commercial_answer_ar"],
        "evidence_label_ar": insight["evidence_ar"],
        "business_meaning_ar": insight["merchant_meaning_ar"],
        "impact_ar": insight["merchant_meaning_ar"],
        "commercial_impact_ar": insight["merchant_meaning_ar"],
        "recommended_direction_ar": insight.get("recommended_action_ar") or "",
        "confidence": insight["confidence"],
        "confidence_reason_ar": (
            "أدلة غير كافية بعد — وهذا بحد ذاته معرفة تجارية."
            if insight.get("insufficient_evidence_ok")
            and _norm(insight.get("confidence")).lower() == "insufficient"
            else ""
        ),
        "fact_key": insight["fact_key"],
        "insight_key": insight["insight_key"],
        "finding_id": insight.get("finding_id"),
        "knowledge_id": insight.get("knowledge_id"),
        "truth_id": insight.get("truth_id"),
        "merchant_problem": insight["merchant_problem"],
        "semantic_topic": insight["semantic_topic"],
        "commercial_question_id": insight["commercial_question_id"],
        "commercial_question_ar": insight["commercial_question_ar"],
        "commercial_dimension": insight["commercial_dimension"],
        "commercial_answer_ar": insight["commercial_answer_ar"],
        "evidence_ar": insight["evidence_ar"],
        "merchant_meaning_ar": insight["merchant_meaning_ar"],
        "recommended_action_ar": insight.get("recommended_action_ar") or "",
        "insufficient_evidence_ok": insight.get("insufficient_evidence_ok"),
        "source_knowledge_id": f"bfe:{insight.get('finding_id')}",
        "commercial_intelligence_v1": True,
    }


def _opportunity_item_from_insight(insight: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "headline_ar": insight["commercial_answer_ar"],
        "why_ar": insight["merchant_meaning_ar"],
        "evidence_ar": insight["evidence_ar"],
        "commercial_value_ar": insight["merchant_meaning_ar"],
        "confidence": insight["confidence"],
        "fact_key": insight["fact_key"],
        "insight_key": insight["insight_key"],
        "merchant_problem": insight["merchant_problem"],
        "semantic_topic": insight["semantic_topic"],
        "commercial_question_id": insight["commercial_question_id"],
        "commercial_question_ar": insight["commercial_question_ar"],
        "commercial_dimension": insight["commercial_dimension"],
        "commercial_answer_ar": insight["commercial_answer_ar"],
        "merchant_meaning_ar": insight["merchant_meaning_ar"],
        "cta_label_ar": "استكشف التفاصيل",
        "drilldown_href": "#knowledge",
        "commercial_intelligence_v1": True,
    }


def _learning_item_from_insight(insight: Mapping[str, Any]) -> dict[str, Any]:
    conf = _norm(insight.get("confidence")).lower()
    if insight.get("insufficient_evidence_ok") and conf == "insufficient":
        kind = "more_evidence_required"
        progress = "ما زلنا لا نملك أدلة كافية هنا"
    elif conf in ("high", "confirmed"):
        kind = "confidence_increased"
        progress = "استنتاج تجاري أصبح أوضح"
    else:
        kind = "new_behaviour"
        progress = "فهم تجاري جديد"
    return {
        "kind": kind,
        "progress_ar": progress,
        "detail_ar": (
            f"{insight['commercial_question_ar']} — {insight['commercial_answer_ar']}"
        ),
        "confidence": insight["confidence"],
        "fact_key": insight["fact_key"],
        "merchant_problem": insight["merchant_problem"],
        "semantic_topic": insight["semantic_topic"],
        "commercial_question_id": insight["commercial_question_id"],
        "commercial_question_ar": insight["commercial_question_ar"],
        "commercial_dimension": insight["commercial_dimension"],
        "commercial_answer_ar": insight["commercial_answer_ar"],
        "evidence_ar": insight["evidence_ar"],
        "merchant_meaning_ar": insight["merchant_meaning_ar"],
        "insufficient_evidence_ok": insight.get("insufficient_evidence_ok"),
        "commercial_intelligence_v1": True,
    }


def select_diverse_insights_v1(
    findings: list[Mapping[str, Any]],
    *,
    max_insights: int = 6,
) -> list[dict[str, Any]]:
    """Prefer one insight per commercial dimension (anti cart/phone monopoly)."""
    insights: list[dict[str, Any]] = []
    for f in findings:
        if not isinstance(f, Mapping):
            continue
        ins = finding_to_commercial_insight_v1(f)
        if ins:
            insights.append(ins)
    # Prefer non-contact first for diversity
    insights.sort(
        key=lambda i: (
            0 if i.get("commercial_dimension") != DIM_CONTACT else 1,
            0 if i.get("commercial_dimension") in _DIVERSITY_CORE else 1,
            -int(i.get("sample_size") or 0),
        )
    )
    seen_dim: set[str] = set()
    out: list[dict[str, Any]] = []
    for ins in insights:
        dim = _norm(ins.get("commercial_dimension"))
        if dim in seen_dim:
            continue
        seen_dim.add(dim)
        out.append(ins)
        if len(out) >= max_insights:
            break
    return out


def apply_home_commercial_intelligence_v1(
    home: MutableMapping[str, Any],
    *,
    store_slug: str = "",
    findings_package: Optional[Mapping[str, Any]] = None,
    dash_store: Any = None,
    load_db: bool = False,
    demo_fixture: bool = False,
) -> MutableMapping[str, Any]:
    """
    Admit commercial insights into Home sections.

    Call after Daily Brief finalize builders, before or after semantic composition
    (caller should re-run semantic composition afterward).
    """
    if not isinstance(home, MutableMapping):
        return home

    slug = _norm(store_slug) or _norm(home.get("store_slug")) or "demo"
    package: Mapping[str, Any]
    if isinstance(findings_package, Mapping) and findings_package.get("findings") is not None:
        package = findings_package
    else:
        try:
            from services.business_findings_engine_v1 import (  # noqa: PLC0415
                run_business_findings_engine_v1,
            )

            package = run_business_findings_engine_v1(
                store_slug=slug,
                load_db=bool(load_db),
                dash_store=dash_store,
                demo_fixture=bool(demo_fixture) or not load_db,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("commercial intelligence findings failed: %s", exc)
            home["home_commercial_intelligence_v1"] = {
                "ok": False,
                "error": type(exc).__name__,
                "engine": ENGINE_VERSION,
            }
            return home

    findings = [
        f for f in list(package.get("findings") or []) if isinstance(f, Mapping)
    ]
    diverse = select_diverse_insights_v1(findings)
    by_dim = { _norm(i.get("commercial_dimension")): i for i in diverse }

    admitted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    # --- Understanding: prefer non-contact commercial answer ---
    und_insight = None
    for dim in (DIM_PRODUCTS, DIM_HESITATION, DIM_TRAFFIC, DIM_RECOVERY, DIM_DATA):
        if dim in by_dim:
            und_insight = by_dim[dim]
            break
    if und_insight is None:
        und_insight = next(
            (i for i in diverse if i.get("commercial_dimension") != DIM_CONTACT),
            None,
        )
    understanding = home.get("store_understanding")
    if not isinstance(understanding, dict):
        understanding = {"items": []}
        home["store_understanding"] = understanding
    if und_insight:
        item = _understanding_item_from_insight(und_insight)
        understanding["items"] = [item]
        understanding["section_question_ar"] = und_insight["commercial_question_ar"]
        understanding["lead_ar"] = und_insight["commercial_question_ar"]
        understanding["purpose_ar"] = (
            "سؤال تجاري → إجابة → دليل → ثقة → معنى للتاجر"
        )
        understanding["commercial_intelligence_v1"] = True
        understanding["home_admission_v1"] = {
            "admitted": True,
            "reason": "answers_commercial_question",
            "cognitive_role": "explain",
            "commercial_question_id": und_insight["commercial_question_id"],
        }
        understanding["suppressed"] = False
        admitted.append(
            {
                "section": "business_understanding",
                "question_id": und_insight["commercial_question_id"],
                "dimension": und_insight["commercial_dimension"],
            }
        )
    home["business_understanding"] = understanding
    home["store_understanding"] = understanding

    # --- Opportunity: products / recovery / whatsapp — never inverse contact count ---
    opp_insight = None
    for dim in (DIM_PRODUCTS, DIM_RECOVERY, DIM_WHATSAPP, DIM_HESITATION):
        if dim in by_dim and (und_insight is None or by_dim[dim] is not und_insight):
            # Prefer a different insight than understanding when possible
            if und_insight and by_dim[dim].get("finding_id") == und_insight.get(
                "finding_id"
            ):
                continue
            opp_insight = by_dim[dim]
            break
    if opp_insight is None:
        for dim in (DIM_PRODUCTS, DIM_RECOVERY, DIM_WHATSAPP):
            if dim in by_dim:
                opp_insight = by_dim[dim]
                break
    opp = home.get("biggest_opportunity")
    if not isinstance(opp, dict):
        opp = {
            "title_ar": "أكبر فرصة اليوم",
            "item": None,
            "items": [],
            "knowledge_role": "opportunity",
        }
        home["biggest_opportunity"] = opp
    if opp_insight:
        item = _opportunity_item_from_insight(opp_insight)
        opp["item"] = item
        opp["items"] = [item]
        opp["section_question_ar"] = opp_insight["commercial_question_ar"]
        opp["lead_ar"] = opp_insight["commercial_question_ar"]
        opp["commercial_intelligence_v1"] = True
        opp["home_admission_v1"] = {
            "admitted": True,
            "reason": "answers_commercial_question",
            "cognitive_role": "opportunity",
            "commercial_question_id": opp_insight["commercial_question_id"],
        }
        opp["suppressed"] = False
        admitted.append(
            {
                "section": "biggest_opportunity",
                "question_id": opp_insight["commercial_question_id"],
                "dimension": opp_insight["commercial_dimension"],
            }
        )
    else:
        # Reject operational recoverable_with_contact restatement
        cur = opp.get("item") if isinstance(opp.get("item"), Mapping) else None
        if cur and (
            "recoverable_with_contact" in _norm(cur.get("fact_key"))
            or rejects_operational_restatement_v1(_norm(cur.get("headline_ar")))
        ):
            opp["item"] = None
            opp["items"] = []
            rejected.append(
                {
                    "section": "biggest_opportunity",
                    "reason": "operational_restatement_rejected",
                }
            )

    # --- Learning: knowledge / missing evidence / traffic honesty ---
    learn_insight = None
    for dim in (DIM_DATA, DIM_KNOWLEDGE, DIM_TRAFFIC, DIM_WHATSAPP, DIM_HESITATION):
        if dim in by_dim:
            cand = by_dim[dim]
            if und_insight and cand.get("finding_id") == und_insight.get("finding_id"):
                continue
            if opp_insight and cand.get("finding_id") == opp_insight.get("finding_id"):
                continue
            learn_insight = cand
            break
    learning = home.get("learning_progress")
    if not isinstance(learning, dict):
        learning = {"items": [], "knowledge_role": "learning_progress"}
        home["learning_progress"] = learning
    if learn_insight:
        item = _learning_item_from_insight(learn_insight)
        learning["items"] = [item]
        learning["section_question_ar"] = learn_insight["commercial_question_ar"]
        learning["lead_ar"] = learn_insight["commercial_question_ar"]
        learning["commercial_intelligence_v1"] = True
        learning["home_admission_v1"] = {
            "admitted": True,
            "reason": "answers_commercial_question",
            "cognitive_role": "learning_progress",
            "commercial_question_id": learn_insight["commercial_question_id"],
        }
        learning["suppressed"] = False
        admitted.append(
            {
                "section": "learning_progress",
                "question_id": learn_insight["commercial_question_id"],
                "dimension": learn_insight["commercial_dimension"],
            }
        )

    # --- Health: commercial orientation, not cart counts ---
    health = home.get("business_health")
    if isinstance(health, dict):
        dims_answered = sorted(
            {a["dimension"] for a in admitted if a.get("dimension")}
        )
        evidence_bits = []
        if dims_answered:
            evidence_bits.append(f"{len(dims_answered)} أسئلة تجارية بأدلة")
        # Drop phone/cart operational evidence lines
        prev = _norm(health.get("evidence_summary_ar"))
        if prev:
            parts = [
                p.strip()
                for p in prev.split("·")
                if p.strip()
                and "تواصل" not in p
                and "سلة" not in p
                and "رقم" not in p
            ]
            evidence_bits.extend(parts[:1])
        health["evidence_summary_ar"] = " · ".join(evidence_bits)
        if und_insight or opp_insight:
            health["summary_ar"] = (
                "المتجر يعمل — ولدينا فهم تجاري متعدد الأبعاد يحتاج انتباهك."
                if dims_answered
                else health.get("summary_ar")
            )
        health["commercial_questions_answered"] = len(
            {a.get("question_id") for a in admitted}
        )
        health["commercial_dimensions"] = dims_answered

    # Priority may keep contact ACTION — stamp commercial question if contact finding exists
    contact = by_dim.get(DIM_CONTACT)
    attention = home.get("attention_today") or home.get("todays_priority")
    if isinstance(attention, dict) and contact:
        items = list(attention.get("items") or [])
        if items and isinstance(items[0], dict):
            items[0]["commercial_question_id"] = contact["commercial_question_id"]
            items[0]["commercial_question_ar"] = contact["commercial_question_ar"]
            items[0]["commercial_dimension"] = DIM_CONTACT
            items[0]["commercial_answer_ar"] = contact["commercial_answer_ar"]
            items[0]["merchant_meaning_ar"] = contact["merchant_meaning_ar"]
            items[0]["evidence_ar"] = contact["evidence_ar"]
            attention["items"] = items
            attention["section_question_ar"] = contact["commercial_question_ar"]
            admitted.append(
                {
                    "section": "todays_priority",
                    "question_id": contact["commercial_question_id"],
                    "dimension": DIM_CONTACT,
                }
            )
        home["attention_today"] = attention
        home["todays_priority"] = attention

    dims = sorted({a["dimension"] for a in admitted if a.get("dimension")})
    questions = sorted({a["question_id"] for a in admitted if a.get("question_id")})
    home["home_commercial_intelligence_v1"] = {
        "ok": True,
        "engine": ENGINE_VERSION,
        "registry_version": REGISTRY_VERSION,
        "findings_engine": package.get("engine_version"),
        "evidence_loaded_from": (package.get("evidence") or {}).get("loaded_from"),
        "admitted": admitted,
        "rejected": rejected,
        "dimensions_answered": dims,
        "questions_answered": questions,
        "questions_answered_count": len(questions),
        "diversity_ok": bool(set(dims) & set(_DIVERSITY_CORE)),
        "success_metric": (
            "number of different commercial questions answered with evidence"
        ),
        "findings_produced": len(findings),
        "ai_used": False,
    }
    obs = home.get("observability")
    if not isinstance(obs, dict):
        obs = {}
        home["observability"] = obs
    obs["home_commercial_intelligence_v1"] = True
    obs["commercial_questions_answered"] = len(questions)
    obs["commercial_dimensions_answered"] = dims
    obs["commercial_diversity_ok"] = bool(set(dims) & set(_DIVERSITY_CORE))
    return home


__all__ = [
    "ENGINE_VERSION",
    "apply_home_commercial_intelligence_v1",
    "finding_to_commercial_insight_v1",
    "insight_has_commercial_evidence_model_v1",
    "select_diverse_insights_v1",
]
