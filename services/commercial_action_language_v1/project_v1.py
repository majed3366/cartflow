# -*- coding: utf-8 -*-
"""Overlay Commercial Action Language V1 onto merchant-visible payloads."""
from __future__ import annotations

from typing import Any, Mapping

from services.commercial_action_language_v1.contract_v1 import (
    ACCEPTED_STATE_AR,
    CONTRACT_FAMILIES,
    FAMILY_PRICE,
    FAMILY_PRODUCT,
    FAMILY_SHIPPING,
    FAMILY_WAIT,
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

_FAMILY_REASON_KEYS = {
    FAMILY_SHIPPING: frozenset({"shipping", "delivery"}),
    FAMILY_PRICE: frozenset({"price"}),
    FAMILY_PRODUCT: frozenset({"quality", "warranty"}),
    FAMILY_WAIT: frozenset(),
}


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _evidence_matches_family(evidence: Mapping[str, Any] | None, family: str) -> bool:
    if not isinstance(evidence, Mapping):
        return False
    allowed = _FAMILY_REASON_KEYS.get(family)
    if allowed is None:
        return False
    if family == FAMILY_WAIT:
        return True
    counts = evidence.get("counts") if isinstance(evidence.get("counts"), Mapping) else {}
    reason = _norm(counts.get("top_reason")).lower()
    if not reason:
        return False
    return reason in allowed


def _owned_evidence(row: Mapping[str, Any], family: str) -> Mapping[str, Any] | None:
    ev = row.get("evidence") if isinstance(row.get("evidence"), Mapping) else None
    if _evidence_matches_family(ev, family):
        return ev
    return None


def _col_evidence_by_family(col: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    if not isinstance(col, Mapping):
        return out
    rows: list[Any] = [col.get("primary")]
    rows.extend(list(col.get("secondaries") or []))
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        fam = _norm(row.get("family"))
        ev = _owned_evidence(row, fam)
        if fam and ev is not None:
            out[fam] = ev
    return out


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
    ev = _owned_evidence(opp, fam) or {}
    pack = contract_for_family_v1(fam, evidence=ev, reason_label_ar=_reason_label(ev))
    if not pack:
        return
    if pack.get("situation_ar"):
        opp["title_ar"] = pack["situation_ar"]
        raw_why = _norm(opp.get("priority_why_ar"))
        if (not raw_why) or ("احتكاك" in raw_why) or ("يقطع" in raw_why):
            opp["priority_why_ar"] = pack["situation_ar"]
    opp["action_ar"] = pack["action_ar"]
    opp["measure_ar"] = pack["measure_ar"]
    opp["recheck_ar"] = pack["recheck_ar"]
    if pack.get("diagnosis_ar"):
        opp["diagnosis_ar"] = pack["diagnosis_ar"]
    if pack.get("dont_ar"):
        opp["dont_ar"] = pack["dont_ar"]
    if pack.get("evidence_ar"):
        opp["why_ar"] = pack["evidence_ar"]
    dc = opp.get("decision_contract_ar")
    if not isinstance(dc, dict):
        dc = {}
        opp["decision_contract_ar"] = dc
    dc["decision_ar"] = pack["situation_ar"]
    dc["why_now_ar"] = pack["evidence_ar"]
    dc["do_this_ar"] = pack.get("mission_ar") or pack["action_ar"]
    dc["dont_ar"] = pack["dont_ar"]
    dc["measure_ar"] = pack["measure_ar"]
    dc["recheck_ar"] = pack["recheck_ar"]
    dc["cta_ar"] = pack["cta_ar"]
    dc["diagnosis_ar"] = pack["diagnosis_ar"]


def _apply_to_catalog_card(card: dict[str, Any], evidence: Mapping[str, Any] | None) -> None:
    fam = _norm(card.get("family"))
    if fam not in CONTRACT_FAMILIES:
        return
    pack = contract_for_family_v1(
        fam, evidence=evidence, reason_label_ar=_reason_label(evidence)
    )
    if not pack:
        return
    if pack.get("situation_ar"):
        card["title_ar"] = pack["situation_ar"]
    card["action_ar"] = pack["action_ar"]
    if pack.get("mission_ar"):
        card["mission_ar"] = pack["mission_ar"]
    card["measure_ar"] = pack["measure_ar"]
    card["recheck_ar"] = pack["recheck_ar"]
    if pack.get("evidence_ar"):
        card["why_ar"] = pack["evidence_ar"]
    if pack.get("diagnosis_ar"):
        card["diagnosis_ar"] = pack["diagnosis_ar"]
    if pack.get("dont_ar"):
        card["dont_ar"] = pack["dont_ar"]
    if pack.get("accepted_state_ar"):
        card["accepted_state_ar"] = pack["accepted_state_ar"]


def _apply_pack_to_guidance_surfaces(guidance: dict[str, Any], pack: Mapping[str, str]) -> None:
    """Rewrite merchant-facing OGL copy only — never ranking family."""
    guidance["merchant_action"] = pack["action_ar"]
    guidance["recommendation"] = pack["dont_ar"]
    guidance["diagnosis"] = pack["diagnosis_ar"]
    guidance["recheck_condition"] = pack["recheck_ar"]
    if pack.get("evidence_ar"):
        guidance["evidence_summary_ar"] = pack["evidence_ar"]
    home = guidance.get("home_surface")
    if isinstance(home, dict):
        if pack.get("evidence_ar"):
            home["what_we_see_ar"] = pack["evidence_ar"]
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


def project_guidance_action_language_v1(
    guidance: dict[str, Any],
    *,
    evidence: Mapping[str, Any] | None = None,
    overlay_family: str | None = None,
) -> dict[str, Any]:
    """Rewrite OGL merchant-facing action fields for contract families only."""
    if not isinstance(guidance, dict):
        return guidance
    fam = _norm(overlay_family) or _OGL_FAMILY_TO_CONTRACT.get(
        _norm(guidance.get("family")), _norm(guidance.get("family"))
    )
    if fam not in CONTRACT_FAMILIES:
        return guidance
    ev = evidence if isinstance(evidence, Mapping) else _evidence_from_ogl(guidance)
    pack = contract_for_family_v1(fam, evidence=ev, reason_label_ar=_reason_label(ev))
    if not pack:
        return guidance
    _apply_pack_to_guidance_surfaces(guidance, pack)
    return guidance


def project_commercial_action_language_v1(body: dict[str, Any]) -> dict[str, Any]:
    """Overlay contract language on a dashboard summary (fail-closed)."""
    if not isinstance(body, dict):
        return body
    col = body.get("commercial_opportunity_layer_v1")
    evidence = None
    by_family: dict[str, Mapping[str, Any]] = {}
    if isinstance(col, dict):
        primary = col.get("primary") if isinstance(col.get("primary"), dict) else None
        by_family = _col_evidence_by_family(col)
        if primary:
            fam = _norm(primary.get("family"))
            evidence = by_family.get(fam)
            _apply_to_opportunity(primary)
        for row in list(col.get("secondaries") or []):
            if isinstance(row, dict):
                _apply_to_opportunity(row)
    cat = body.get("mission_catalog_v1")
    if isinstance(cat, dict):
        primary_c = cat.get("primary") if isinstance(cat.get("primary"), dict) else None
        if primary_c:
            pfam = _norm(primary_c.get("family"))
            _apply_to_catalog_card(primary_c, by_family.get(pfam) or _owned_evidence(primary_c, pfam))
            expl = cat.get("explain")
            if isinstance(expl, dict):
                raw_ex = _norm(expl.get("why_this_one_now_ar"))
                sit = _norm(primary_c.get("title_ar"))
                commitment = (
                    primary_c.get("commitment")
                    if isinstance(primary_c.get("commitment"), dict)
                    else {}
                )
                phase = _norm(primary_c.get("cdc_phase") or commitment.get("phase"))
                if phase == "ACTION_CHOSEN" or ("لا نستبدله" in raw_ex):
                    expl["why_this_one_now_ar"] = ACCEPTED_STATE_AR
                elif sit and (("احتكاك" in raw_ex) or ("يقطع" in raw_ex) or not raw_ex):
                    expl["why_this_one_now_ar"] = sit
        for row in list(cat.get("secondaries") or []):
            if isinstance(row, dict):
                sfam = _norm(row.get("family"))
                _apply_to_catalog_card(
                    row,
                    by_family.get(sfam) or _owned_evidence(row, sfam),
                )
    commercial_fam = ""
    if isinstance(cat, dict):
        primary_c = cat.get("primary") if isinstance(cat.get("primary"), dict) else None
        if primary_c:
            commercial_fam = _norm(primary_c.get("family"))
    if not commercial_fam and isinstance(col, dict):
        primary = col.get("primary") if isinstance(col.get("primary"), dict) else None
        if primary:
            commercial_fam = _norm(primary.get("family"))
    ogl = body.get("operational_guidance_v1")
    if isinstance(ogl, dict):
        ofam = _OGL_FAMILY_TO_CONTRACT.get(_norm(ogl.get("family")), _norm(ogl.get("family")))
        paint_fam = ofam
        # Presentation only: if catalog/COL already has a ready commercial family
        # while OGL ranked wait, Home must not keep wait/widget copy.
        if ofam == FAMILY_WAIT and commercial_fam in (
            FAMILY_SHIPPING,
            FAMILY_PRICE,
            FAMILY_PRODUCT,
        ):
            paint_fam = commercial_fam
        paint_ev = by_family.get(paint_fam) if paint_fam in CONTRACT_FAMILIES else evidence
        if paint_fam in CONTRACT_FAMILIES and not _evidence_matches_family(paint_ev, paint_fam):
            paint_ev = None
        project_guidance_action_language_v1(
            ogl, evidence=paint_ev, overlay_family=paint_fam
        )
        hes = body.get("home_executive_summary_v1")
        if isinstance(hes, dict):
            nested = hes.get("operational_guidance_v1")
            if isinstance(nested, dict) and isinstance(ogl.get("home_surface"), dict):
                nested["home_surface"] = dict(ogl.get("home_surface") or {})
    return body


__all__ = [
    "project_commercial_action_language_v1",
    "project_guidance_action_language_v1",
]
