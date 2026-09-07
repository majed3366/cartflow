# -*- coding: utf-8 -*-
"""Overlay Commercial Action Language V1 onto merchant-visible payloads."""
from __future__ import annotations

from typing import Any, Mapping

from services.commercial_action_language_v1.contract_v1 import (
    CONTRACT_FAMILIES,
    FAMILY_PRODUCT,
    contract_for_family_v1,
)

_OGL_FAMILY_TO_CONTRACT = {
    "product_confidence_quality": FAMILY_PRODUCT,
}

_REASON_LABEL_AR = {
    "shipping": "الشحن",
    "delivery": "التوصيل",
    "price": "السعر",
    "quality": "الجودة",
    "warranty": "الضمان",
}


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _reason_label(evidence: Mapping[str, Any] | None) -> str:
    if not isinstance(evidence, Mapping):
        return ""
    counts = evidence.get("counts") if isinstance(evidence.get("counts"), Mapping) else {}
    reason = _norm(counts.get("top_reason")).lower()
    return _REASON_LABEL_AR.get(reason, "")


def _evidence_from_ogl(guidance: Mapping[str, Any]) -> dict[str, Any] | None:
    refs = guidance.get("evidence_refs")
    if not isinstance(refs, list):
        return None
    top_reason = ""
    top_count = None
    total = None
    share = None
    for raw in refs:
        ref = _norm(raw)
        if ref.startswith("hesitation_total:"):
            try:
                total = int(ref.split(":", 1)[1])
            except (TypeError, ValueError, IndexError):
                pass
        elif ref.startswith("hesitation_top:"):
            parts = ref.split(":")
            if len(parts) >= 3:
                top_reason = _norm(parts[1]).lower()
                try:
                    top_count = int(parts[2])
                except (TypeError, ValueError):
                    pass
        elif ref.startswith("hesitation_share:"):
            try:
                share = float(ref.split(":", 1)[1])
            except (TypeError, ValueError, IndexError):
                pass
        elif ref.startswith("hesitation_dist:"):
            parts = ref.split(":")
            if len(parts) >= 3 and "/" in parts[2]:
                top_reason = _norm(parts[1]).lower()
                left, right = parts[2].split("/", 1)
                try:
                    top_count = int(left)
                    total = int(right)
                except (TypeError, ValueError):
                    pass
    if top_count is None and total is None:
        return None
    return {
        "counts": {
            "hesitation_total": total,
            "top_reason": top_reason,
            "top_count": top_count,
            "top_share": share,
        }
    }


def _apply_to_opportunity(opp: dict[str, Any]) -> None:
    fam = _norm(opp.get("family"))
    if fam not in CONTRACT_FAMILIES:
        return
    ev = opp.get("evidence") if isinstance(opp.get("evidence"), Mapping) else {}
    pack = contract_for_family_v1(fam, evidence=ev, reason_label_ar=_reason_label(ev))
    if not pack:
        return
    opp["action_ar"] = pack["action_ar"]
    opp["measure_ar"] = pack["measure_ar"]
    opp["recheck_ar"] = pack["recheck_ar"]
    if pack.get("evidence_ar"):
        opp["why_ar"] = pack["evidence_ar"]
    dc = opp.get("decision_contract_ar")
    if not isinstance(dc, dict):
        dc = {}
        opp["decision_contract_ar"] = dc
    dc["decision_ar"] = pack["situation_ar"]
    dc["why_now_ar"] = pack["evidence_ar"]
    dc["do_this_ar"] = pack["action_ar"]
    dc["dont_ar"] = pack["dont_ar"]
    dc["measure_ar"] = pack["measure_ar"]
    dc["recheck_ar"] = pack["recheck_ar"]
    dc["cta_ar"] = pack["cta_ar"]


def _apply_to_catalog_card(card: dict[str, Any], evidence: Mapping[str, Any] | None) -> None:
    fam = _norm(card.get("family"))
    if fam not in CONTRACT_FAMILIES:
        return
    pack = contract_for_family_v1(
        fam, evidence=evidence, reason_label_ar=_reason_label(evidence)
    )
    if not pack:
        return
    card["action_ar"] = pack["action_ar"]
    card["measure_ar"] = pack["measure_ar"]
    card["recheck_ar"] = pack["recheck_ar"]
    if pack.get("evidence_ar"):
        card["why_ar"] = pack["evidence_ar"]


def project_guidance_action_language_v1(
    guidance: dict[str, Any],
    *,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Rewrite OGL merchant-facing action fields for contract families only."""
    if not isinstance(guidance, dict):
        return guidance
    fam = _OGL_FAMILY_TO_CONTRACT.get(_norm(guidance.get("family")), _norm(guidance.get("family")))
    if fam not in CONTRACT_FAMILIES:
        return guidance
    ev = evidence if isinstance(evidence, Mapping) else _evidence_from_ogl(guidance)
    pack = contract_for_family_v1(fam, evidence=ev, reason_label_ar=_reason_label(ev))
    if not pack:
        return guidance
    guidance["merchant_action"] = pack["action_ar"]
    guidance["recommendation"] = pack["dont_ar"]
    guidance["diagnosis"] = pack["diagnosis_ar"]
    guidance["recheck_condition"] = pack["recheck_ar"]
    if pack.get("evidence_ar"):
        guidance["evidence_summary_ar"] = pack["evidence_ar"]
    home = guidance.get("home_surface")
    if isinstance(home, dict):
        home["what_it_means_ar"] = pack["diagnosis_ar"]
        home["what_to_do_now_ar"] = pack["action_ar"]
        home["when_to_recheck_ar"] = pack["recheck_ar"]
    ws = guidance.get("workspace_surface")
    if isinstance(ws, dict):
        ws["diagnosis_ar"] = pack["diagnosis_ar"]
        ws["why_ar"] = pack["evidence_ar"]
        ws["recommendation_ar"] = pack["dont_ar"]
        ws["action_ar"] = pack["action_ar"]
        ws["recheck_condition_ar"] = pack["recheck_ar"]
    return guidance


def project_commercial_action_language_v1(body: dict[str, Any]) -> dict[str, Any]:
    """Overlay contract language on a dashboard summary (fail-closed)."""
    if not isinstance(body, dict):
        return body
    col = body.get("commercial_opportunity_layer_v1")
    evidence = None
    if isinstance(col, dict):
        primary = col.get("primary") if isinstance(col.get("primary"), dict) else None
        if primary:
            evidence = primary.get("evidence") if isinstance(primary.get("evidence"), Mapping) else None
            _apply_to_opportunity(primary)
        for row in list(col.get("secondaries") or []):
            if isinstance(row, dict):
                _apply_to_opportunity(row)
    cat = body.get("mission_catalog_v1")
    if isinstance(cat, dict):
        primary_c = cat.get("primary") if isinstance(cat.get("primary"), dict) else None
        if primary_c:
            _apply_to_catalog_card(primary_c, evidence)
        for row in list(cat.get("secondaries") or []):
            if isinstance(row, dict):
                _apply_to_catalog_card(row, row.get("evidence") if isinstance(row.get("evidence"), Mapping) else evidence)
    ogl = body.get("operational_guidance_v1")
    if isinstance(ogl, dict):
        project_guidance_action_language_v1(ogl, evidence=evidence)
    return body


__all__ = [
    "project_commercial_action_language_v1",
    "project_guidance_action_language_v1",
]
