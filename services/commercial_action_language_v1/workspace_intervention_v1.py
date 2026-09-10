# -*- coding: utf-8 -*-
"""
Project the Commercial Intervention Intelligence contract onto the merchant
Decision Workspace payload.

Presentation projection only. Every input is already on the composed dashboard
summary — COL `truth_class`, Catalog `role`, Portfolio `conflict_type`, CDC
`phase` — so query delta is +0: no DB read, no AI, no external call.

Nothing here decides anything. Diagnosis stays with COL, priority with Mission
Catalog, conflict and capacity with Mission Portfolio, commitment with CDC, and
every eligibility/level/copy decision with `intervention_v1`. This module only
reads those owners and hands the frontend a paintable projection.
"""
from __future__ import annotations

from typing import Any, Mapping

from services.commercial_action_language_v1.contract_v1 import (
    contract_for_family_v1,
)
from services.commercial_action_language_v1.intervention_v1 import (
    DEFERRAL_AR,
    ELIGIBLE,
    compose_merchant_intervention_card_v1,
    economic_manifest_v1,
    intervention_contract_v1,
)
from services.commercial_decision_commitment_v1.contract_v1 import (
    PHASE_ACTION_CHOSEN,
    PHASE_RECHECK_DUE,
    PHASE_UNDER_MEASUREMENT,
)
from services.mission_portfolio_v1.contract_v1 import CONFLICT_SAFE_TO_COEXIST

PROJECTION_VERSION = "commercial_intervention_workspace_v1"

# Shown when the family has no Level 2+ guardrail yet. Never paint a null.
GUARDRAIL_FALLBACK_AR = "لا يوجد مقياس اقتصادي موثوق بعد."

# Merchant-facing labels for the guided decision. Section order is the reading
# order: evidence -> intervention -> safety/limit -> action -> measurement.
LABELS_AR = {
    "see": "ما الذي نراه؟",
    "suggest": "ما التدخل المقترح الآن؟",
    "safe": "لماذا هذا آمن الآن؟",
    "blocked": "لماذا لا نقترح تدخلاً أقوى؟",
    "dont": "لا تفعل الآن",
    "measure": "ماذا سنقيس؟",
    "recheck": "متى نراجع؟",
    "mind_change": "ما الذي سيجعلنا نغيّر رأينا؟",
    "active": "التدخل الجاري",
    "guardrail": "الحد الذي لا نتجاوزه",
}

# The primary heading follows the lifecycle the merchant is actually in, so the
# page never asks "what should we do now?" about a mission already running.
# Presentation mapping over CDC's phase — CDC remains the only lifecycle owner.
STATE_READY = "READY"
STATE_ACTION_CHOSEN = "ACTION_CHOSEN"
STATE_UNDER_MEASUREMENT = "UNDER_MEASUREMENT"
STATE_RECHECK_DUE = "RECHECK_DUE"
STATE_WAIT = "WAIT"

HEADINGS_AR = {
    STATE_READY: "ما التدخل المقترح الآن؟",
    STATE_ACTION_CHOSEN: "ما الذي اعتمدته الآن؟",
    STATE_UNDER_MEASUREMENT: "ما الذي نقيسه الآن؟",
    STATE_RECHECK_DUE: "ماذا أظهرت إعادة المراجعة؟",
    STATE_WAIT: "لماذا ننتظر الآن؟",
}

_PHASE_STATES = {
    PHASE_ACTION_CHOSEN: STATE_ACTION_CHOSEN,
    PHASE_UNDER_MEASUREMENT: STATE_UNDER_MEASUREMENT,
}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _heading_state(cdc_phase: str | None, eligibility_state: str) -> str:
    """Which lifecycle question the merchant is actually looking at."""
    phase = _norm(cdc_phase)
    committed = _PHASE_STATES.get(phase)
    if committed:
        return committed
    if phase == PHASE_RECHECK_DUE:
        return STATE_RECHECK_DUE
    return STATE_READY if eligibility_state == ELIGIBLE else STATE_WAIT


def _conflict_type_for(portfolio: Mapping[str, Any] | None, opportunity_id: str) -> str | None:
    """Portfolio's verdict for this opportunity. Unknown stays unknown."""
    if not isinstance(portfolio, Mapping) or portfolio.get("ok") is False:
        return None
    oid = _norm(opportunity_id)
    if not oid:
        return None
    for bucket in ("deferred", "suppressed"):
        for row in portfolio.get(bucket) or []:
            if isinstance(row, Mapping) and _norm(row.get("opportunity_id")) == oid:
                return row.get("conflict_type")
    for key in ("active_mission", "next_mission"):
        row = portfolio.get(key)
        if isinstance(row, Mapping) and _norm(row.get("opportunity_id")) == oid:
            return CONFLICT_SAFE_TO_COEXIST
    for row in portfolio.get("safe_secondaries") or []:
        if isinstance(row, Mapping) and _norm(row.get("opportunity_id")) == oid:
            return CONFLICT_SAFE_TO_COEXIST
    return None


def _evidence_for_card(body: Mapping[str, Any], card: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """COL owns the evidence bag; prefer its family bag over the card's copy."""
    from services.commercial_action_language_v1.project_v1 import (  # noqa: PLC0415
        _col_evidence_by_family,
    )

    fam = _norm(card.get("family"))
    col = body.get("commercial_opportunity_layer_v1")
    if isinstance(col, Mapping):
        bag = _col_evidence_by_family(col).get(fam)
        if isinstance(bag, Mapping):
            return bag
    own = card.get("evidence")
    return own if isinstance(own, Mapping) else None


def _merchant_blocked(candidates: Any) -> list[dict[str, Any]]:
    """Merchant sees the class and the reason in words — never field names."""
    out: list[dict[str, Any]] = []
    for row in candidates or []:
        if not isinstance(row, Mapping):
            continue
        text = _norm(row.get("merchant_ar"))
        if not text:
            continue
        out.append(
            {
                "class_ar": _norm(row.get("class_ar")),
                "merchant_ar": text,
                "missing_input_count": len(row.get("missing_inputs") or []),
            }
        )
    return out


def build_workspace_intervention_v1(
    *,
    family: str,
    col_truth_class: str | None,
    catalog_role: str | None,
    portfolio_conflict_type: str | None,
    own_cdc_phase: str | None,
    evidence: Mapping[str, Any] | None = None,
    reason_label_ar: str = "",
    situation_ar: str = "",
    evidence_ar: str = "",
    active_action_ar: str = "",
) -> dict[str, Any]:
    """One guided commercial decision, ready to paint. Empty dict when unsupported."""
    fam = _norm(family)
    intervention = intervention_contract_v1(
        family=fam,
        col_truth_class=col_truth_class,
        catalog_role=catalog_role,
        portfolio_conflict_type=portfolio_conflict_type,
        own_cdc_phase=own_cdc_phase,
        manifest=economic_manifest_v1(),
    )
    card = compose_merchant_intervention_card_v1(
        family=fam,
        intervention=intervention,
        evidence=evidence,
        reason_label_ar=reason_label_ar,
    )
    if not card:
        return {}

    # Section 1 wants the diagnosis and its evidence read as two lines rather
    # than the single merged string the card carries. Copy already projected
    # onto the card wins, because that is what every other surface shows.
    base = contract_for_family_v1(fam, evidence=evidence, reason_label_ar=reason_label_ar) or {}
    situation = _norm(situation_ar) or _norm(base.get("situation_ar")) or _norm(
        card.get("what_we_see_ar")
    )
    evidence_line = _norm(evidence_ar) or _norm(base.get("evidence_ar"))
    if not evidence_line:
        merged = _norm(card.get("what_we_see_ar"))
        evidence_line = merged[len(situation):].strip() if merged.startswith(situation) else ""

    state = _norm(card.get("eligibility_state"))
    heading_state = _heading_state(own_cdc_phase, state)
    labels = dict(LABELS_AR)
    labels["suggest"] = HEADINGS_AR[heading_state]
    # Only a READY card is a proposal. Every other state carries the deferral
    # sentence followed by the family's safe action; split them so the state
    # answers the heading and no blocked card ends on an instruction to act.
    committed = heading_state in (STATE_ACTION_CHOSEN, STATE_UNDER_MEASUREMENT)
    suggest = _norm(card.get("what_we_suggest_ar"))
    trailing = ""
    prefix = _norm(DEFERRAL_AR.get(state, ""))
    if prefix and suggest.startswith(prefix):
        trailing, suggest = suggest[len(prefix) :].strip(), prefix
    # The trailing action is only true as context while that work is running.
    active = (trailing or _norm(active_action_ar)) if committed else ""
    return {
        "ok": True,
        "projection_version": PROJECTION_VERSION,
        "layer_version": intervention.get("layer_version"),
        "intervention_id": card.get("intervention_id"),
        "family": fam,
        "recommendation_level": card.get("recommendation_level"),
        "eligibility_state": state,
        "cdc_phase": _norm(own_cdc_phase) or None,
        "heading_state": heading_state,
        "is_new_recommendation": heading_state == STATE_READY,
        "active_intervention_ar": active,
        "conflict_group": card.get("conflict_group"),
        "labels_ar": labels,
        "situation_ar": situation,
        "evidence_ar": evidence_line,
        "what_we_suggest_ar": suggest,
        "why_this_is_safe_ar": _norm(card.get("why_this_is_safe_ar")),
        "blocked_candidates": _merchant_blocked(card.get("blocked_candidates")),
        "dont_do_ar": _norm(card.get("dont_do_ar")),
        "primary_metric": _norm(card.get("primary_metric")),
        "guardrail_metric": _norm(card.get("guardrail_metric")) or GUARDRAIL_FALLBACK_AR,
        "recheck_condition": _norm(card.get("recheck_condition")),
        "mind_change_condition": _norm(card.get("mind_change_condition")),
        "measurement_window_days": card.get("measurement_window_days"),
        # CTA truth is decided by intervention_v1 and only painted downstream.
        "cta_ar": card.get("cta_ar") if state == ELIGIBLE else None,
    }


def attach_intervention_to_summary_v1(body: dict[str, Any]) -> dict[str, Any]:
    """Attach the workspace intervention onto the catalog primary. Fail-closed."""
    if not isinstance(body, dict):
        return body
    catalog = body.get("mission_catalog_v1")
    if not isinstance(catalog, dict) or catalog.get("ok") is False:
        return body
    card = catalog.get("primary")
    if not isinstance(card, dict):
        return body

    commitment = card.get("commitment") if isinstance(card.get("commitment"), Mapping) else {}
    projection = build_workspace_intervention_v1(
        family=card.get("family"),
        col_truth_class=card.get("truth_class"),
        catalog_role=card.get("role"),
        portfolio_conflict_type=_conflict_type_for(
            body.get("mission_portfolio_v1"), card.get("opportunity_id")
        ),
        own_cdc_phase=_norm(card.get("cdc_phase") or commitment.get("phase")) or None,
        evidence=_evidence_for_card(body, card),
        reason_label_ar=_norm(card.get("reason_label_ar")),
        # CAL already projected contract copy onto the card upstream.
        situation_ar=_norm(card.get("title_ar")),
        evidence_ar=_norm(card.get("why_ar")),
        active_action_ar=_norm(card.get("action_ar")),
    )
    if projection:
        card["intervention_v1"] = projection
    return body


__all__ = [
    "GUARDRAIL_FALLBACK_AR",
    "HEADINGS_AR",
    "LABELS_AR",
    "PROJECTION_VERSION",
    "STATE_ACTION_CHOSEN",
    "STATE_READY",
    "STATE_RECHECK_DUE",
    "STATE_UNDER_MEASUREMENT",
    "STATE_WAIT",
    "attach_intervention_to_summary_v1",
    "build_workspace_intervention_v1",
]
