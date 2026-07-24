# -*- coding: utf-8 -*-
"""Compose decisions from verified existing FDE/BFL findings."""
from __future__ import annotations

from typing import Any, Mapping

from services.decision_composition_engine_v1.contract_v1 import (
    DECISION_TYPE_RECOVERABILITY_GAP,
    DECISION_TYPE_VERIFIED_FINDING,
    SUPPRESS_ACTION_UNSUPPORTED,
    SUPPRESS_GENERIC_PRODUCT,
    SUPPRESS_INSUFFICIENT_EVIDENCE,
    SUPPRESS_STALE,
    SUPPRESS_SUBJECT_UNIDENTIFIED,
    contains_generic_product_language,
    new_candidate,
)
from services.decision_composition_engine_v1.inputs_v1 import extract_product_identity_v1
from services.decision_composition_engine_v1.priority_v1 import calculate_priority_v1
from services.decision_composition_engine_v1.suppress_v1 import mark_suppressed


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _finding_type(contract: Mapping[str, Any]) -> str:
    return _norm(contract.get("finding_type") or contract.get("type"))


def compose_from_finding_contract_v1(
    contract: Mapping[str, Any],
    *,
    store_slug: str,
) -> dict[str, Any] | None:
    if not isinstance(contract, Mapping):
        return None
    fid = _norm(contract.get("finding_id"))
    if not fid:
        return None

    ftype = _finding_type(contract)
    # Recoverability covered by dedicated OT composer — avoid duplicate.
    if "missing_contact" in ftype:
        return mark_suppressed(
            new_candidate(
                decision_id=f"dce:finding:{fid}",
                store_slug=store_slug,
                decision_type=DECISION_TYPE_RECOVERABILITY_GAP,
                title=_norm(contract.get("title")),
            ),
            "covered_by_recoverability_gap_composer",
        )

    dec = contract.get("merchant_decision_v1")
    if not isinstance(dec, Mapping):
        dec = {}

    status = _norm(dec.get("status") or "")
    has_decision = bool(dec.get("has_decision")) and status == "DECISION"
    if not has_decision:
        return mark_suppressed(
            new_candidate(
                decision_id=f"dce:finding:{fid}",
                store_slug=store_slug,
                decision_type=DECISION_TYPE_VERIFIED_FINDING,
                title=_norm(contract.get("title") or fid),
                evidence_summary=_norm(
                    dec.get("evidence_summary") or contract.get("evidence_summary")
                ),
                source_truth_types=["business_finding", "finding_decision_engine"],
            ),
            SUPPRESS_INSUFFICIENT_EVIDENCE
            if _norm(dec.get("missing_evidence"))
            else SUPPRESS_ACTION_UNSUPPORTED,
        )

    # Stale: lifecycle may stamp status
    lifecycle = _norm(contract.get("lifecycle_status") or contract.get("status")).lower()
    if lifecycle in {"stale", "expired", "archived", "superseded"}:
        return mark_suppressed(
            new_candidate(
                decision_id=f"dce:finding:{fid}",
                store_slug=store_slug,
                decision_type=DECISION_TYPE_VERIFIED_FINDING,
                title=_norm(contract.get("title")),
            ),
            SUPPRESS_STALE,
        )

    product_types = (
        "high_interest_low_purchase",
        "low_product_interest",
        "repeated_interest",
        "return_without_purchase",
    )
    needs_product = any(t in ftype for t in product_types)
    product_id, product_name = extract_product_identity_v1(contract)
    subject_type = "product" if needs_product else "store"
    subject_id = product_id if needs_product else store_slug

    if needs_product and not product_id:
        return mark_suppressed(
            new_candidate(
                decision_id=f"dce:finding:{fid}",
                store_slug=store_slug,
                decision_type=DECISION_TYPE_VERIFIED_FINDING,
                decision_subject_type="product",
                title=_norm(contract.get("title")),
            ),
            SUPPRESS_SUBJECT_UNIDENTIFIED,
        )

    decision = _norm(dec.get("decision") or contract.get("title") or contract.get("merchant_statement_ar"))
    why = _norm(dec.get("why") or contract.get("explanation"))
    evidence = _norm(dec.get("evidence_summary") or contract.get("evidence_summary"))
    action = _norm(dec.get("required_merchant_action") or contract.get("recommended_action"))
    outcome = _norm(dec.get("expected_business_impact") or "")
    conf = _norm(dec.get("decision_confidence") or contract.get("confidence") or "medium")

    if needs_product and product_name:
        # Prefer named product in decision language; never generic.
        if contains_generic_product_language(decision, why):
            return mark_suppressed(
                new_candidate(
                    decision_id=f"dce:finding:{fid}",
                    store_slug=store_slug,
                    decision_type=DECISION_TYPE_VERIFIED_FINDING,
                    decision_subject_type="product",
                    decision_subject_id=product_id,
                    title=decision,
                ),
                SUPPRESS_GENERIC_PRODUCT,
            )
        if product_name not in decision:
            decision = f"راجع أداء المنتج {product_name}."

    if contains_generic_product_language(decision, why, action):
        return mark_suppressed(
            new_candidate(
                decision_id=f"dce:finding:{fid}",
                store_slug=store_slug,
                decision_type=DECISION_TYPE_VERIFIED_FINDING,
                title=decision,
            ),
            SUPPRESS_GENERIC_PRODUCT,
        )

    why_now = _norm(contract.get("why_now_ar")) or (
        "الأدلة الحالية كافية لإثارة قرار يحتاج انتباهك الآن."
    )
    ignore = _norm(contract.get("ignore_consequence_ar")) or (
        "إذا تُرك دون مراجعة، قد يستمر نفس النمط دون تحسين واضح."
    )
    first = _norm(contract.get("first_step_ar")) or action

    cand = new_candidate(
        decision_id=f"dce:finding:{fid}",
        store_slug=store_slug,
        decision_type=DECISION_TYPE_VERIFIED_FINDING,
        decision_subject_type=subject_type,
        decision_subject_id=subject_id,
        title=decision,
        merchant_decision=decision,
        why=why,
        why_now=why_now,
        evidence_summary=evidence,
        evidence_refs=[f"finding:{fid}", ftype],
        ignore_consequence=ignore,
        recommended_action=action,
        first_step=first,
        expected_outcome=outcome or "تحسين واضح بعد تنفيذ الإجراء الموصى به.",
        confidence=conf if conf.lower() not in {"none", ""} else "medium",
        source_truth_types=["business_finding", "finding_decision_engine", ftype],
        finding_id=fid,
        finding_type=ftype,
        view_details_href="#workspace",
        affected_count=_as_affected(contract, dec),
    )
    score, band, factors = calculate_priority_v1(
        cand,
        affected_count=_as_affected(contract, dec),
        automation_can_resolve=False,
    )
    cand["priority"] = score
    cand["priority_band"] = band
    cand["priority_factors"] = factors
    return cand


def _as_affected(contract: Mapping[str, Any], dec: Mapping[str, Any]) -> int:
    for key in ("affected_carts", "evidence_count", "sample_size"):
        for src in (dec, contract):
            try:
                n = int(src.get(key) or 0)
                if n > 0:
                    return n
            except (TypeError, ValueError):
                pass
    return 0


__all__ = ["compose_from_finding_contract_v1"]
