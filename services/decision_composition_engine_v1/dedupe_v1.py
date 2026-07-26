# -*- coding: utf-8 -*-
"""
Gate 2D — Decision Deduplication.

One root cause → one canonical decision. Duplicate business problems are forbidden.
"""
from __future__ import annotations

from typing import Any, Mapping

from services.decision_composition_engine_v1.business_domains_v1 import (
    ROOT_MISSING_CONTACT,
    ROOT_WAITING_INTERVENTION,
    map_finding_to_domain_v1,
    root_cause_for_finding_v1,
)
from services.decision_composition_engine_v1.contract_v1 import (
    DECISION_TYPE_RECOVERABILITY_GAP,
    DECISION_TYPE_WAITING_RECOVERY,
    SUPPRESS_DUPLICATE,
)
from services.decision_composition_engine_v1.suppress_v1 import (
    dedupe_key,
    mark_suppressed,
)

SUPPRESS_SAME_ROOT_CAUSE = "duplicate_root_cause"
SUPPRESS_SUBSUMED_BY_CANONICAL = "subsumed_by_canonical_decision"
SUPPRESS_DUPLICATE_ACTION = "duplicate_recommended_action"


def attach_root_cause_v1(
    candidate: dict[str, Any],
    *,
    domain_pkg: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Stamp business_domain + root_cause_key on a candidate."""
    dtype = str(candidate.get("decision_type") or "").strip()
    slug = str(candidate.get("store_slug") or "").strip()

    if dtype == DECISION_TYPE_RECOVERABILITY_GAP:
        candidate["business_domain"] = "recovery"
        candidate["root_cause_key"] = ROOT_MISSING_CONTACT
        return candidate

    if dtype == DECISION_TYPE_WAITING_RECOVERY:
        signals = (domain_pkg or {}).get("signals") if isinstance(domain_pkg, Mapping) else {}
        if isinstance(signals, Mapping) and signals.get(
            "waiting_collapsed_into_missing_contact"
        ):
            candidate["business_domain"] = "recovery"
            candidate["root_cause_key"] = ROOT_MISSING_CONTACT
        else:
            candidate["business_domain"] = "operations"
            candidate["root_cause_key"] = ROOT_WAITING_INTERVENTION
        return candidate

    # Verified finding path
    finding_like = {
        "finding_type": candidate.get("finding_type"),
        "finding_id": candidate.get("finding_id"),
        "title": candidate.get("title"),
        "product_id": candidate.get("decision_subject_id")
        if candidate.get("decision_subject_type") == "product"
        else "",
        "entity": {"product_id": candidate.get("decision_subject_id")}
        if candidate.get("decision_subject_type") == "product"
        else {},
        "merchant_decision_v1": {"has_decision": True},
    }
    domain = map_finding_to_domain_v1(finding_like)
    candidate["business_domain"] = domain
    candidate["root_cause_key"] = root_cause_for_finding_v1(
        finding_like, store_slug=slug
    )
    return candidate


def _priority_tuple(cand: Mapping[str, Any]) -> tuple:
    band = str(cand.get("priority_band") or "")
    return (
        0 if band == "needs_action_now" else 1,
        -int(cand.get("priority") or 0),
        str(cand.get("decision_id") or ""),
    )


def dedupe_candidates_v1(
    candidates: list[dict[str, Any]],
    *,
    domain_pkg: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Collapse candidates that share a structural key or the same root cause.

    Returns (survivors_for_contract_gate, suppression_registry_rows).
    Survivors may still be suppressed later by contract gate.
    """
    registry: list[dict[str, Any]] = []
    working: list[dict[str, Any]] = []

    for raw in candidates:
        cand = attach_root_cause_v1(dict(raw), domain_pkg=domain_pkg)
        if cand.get("suppressed"):
            registry.append(
                {
                    "decision_id": cand.get("decision_id"),
                    "suppression_reason": cand.get("suppression_reason"),
                    "decision_type": cand.get("decision_type"),
                    "decision_category": cand.get("decision_category"),
                    "root_cause_key": cand.get("root_cause_key"),
                    "business_domain": cand.get("business_domain"),
                }
            )
            continue
        # Waiting collapsed into missing-contact domain → never publish as second.
        if (
            cand.get("decision_type") == DECISION_TYPE_WAITING_RECOVERY
            and cand.get("root_cause_key") == ROOT_MISSING_CONTACT
        ):
            cand = mark_suppressed(cand, SUPPRESS_SUBSUMED_BY_CANONICAL)
            registry.append(
                {
                    "decision_id": cand.get("decision_id"),
                    "suppression_reason": SUPPRESS_SUBSUMED_BY_CANONICAL,
                    "decision_type": cand.get("decision_type"),
                    "root_cause_key": ROOT_MISSING_CONTACT,
                    "business_domain": cand.get("business_domain"),
                }
            )
            continue
        working.append(cand)

    # Prefer recoverability_gap over any other candidate on same root cause.
    type_rank = {
        DECISION_TYPE_RECOVERABILITY_GAP: 0,
        DECISION_TYPE_WAITING_RECOVERY: 1,
        "verified_existing_finding": 2,
    }
    working.sort(
        key=lambda c: (
            type_rank.get(str(c.get("decision_type") or ""), 9),
            *_priority_tuple(c),
        )
    )

    seen_struct: set[str] = set()
    seen_root: set[str] = set()
    survivors: list[dict[str, Any]] = []

    for cand in working:
        struct = dedupe_key(cand)
        root = str(cand.get("root_cause_key") or "").strip()
        if struct in seen_struct:
            cand = mark_suppressed(cand, SUPPRESS_DUPLICATE)
            registry.append(
                {
                    "decision_id": cand.get("decision_id"),
                    "suppression_reason": SUPPRESS_DUPLICATE,
                    "decision_type": cand.get("decision_type"),
                    "root_cause_key": root,
                    "business_domain": cand.get("business_domain"),
                }
            )
            continue
        if root and root in seen_root:
            cand = mark_suppressed(cand, SUPPRESS_SAME_ROOT_CAUSE)
            registry.append(
                {
                    "decision_id": cand.get("decision_id"),
                    "suppression_reason": SUPPRESS_SAME_ROOT_CAUSE,
                    "decision_type": cand.get("decision_type"),
                    "root_cause_key": root,
                    "business_domain": cand.get("business_domain"),
                }
            )
            continue
        seen_struct.add(struct)
        if root:
            seen_root.add(root)
        survivors.append(cand)

    return survivors, registry


def _action_key_v1(cand: Mapping[str, Any]) -> str:
    import re

    text = str(
        cand.get("merchant_decision")
        or cand.get("executive_decision_ar")
        or cand.get("recommended_action")
        or cand.get("title")
        or ""
    ).strip()
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).casefold()


def dedupe_published_by_action_v1(
    decisions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    After executive titles are stamped: merge decisions that require the same
    merchant action (F3). Priority labels must never distinguish duplicates.
    """
    registry: list[dict[str, Any]] = []
    working = [dict(d) for d in decisions if isinstance(d, Mapping) and not d.get("suppressed")]
    working.sort(key=_priority_tuple)
    seen_action: set[str] = set()
    survivors: list[dict[str, Any]] = []
    for cand in working:
        key = _action_key_v1(cand)
        subject = str(
            cand.get("decision_subject_id")
            or cand.get("situation_id")
            or cand.get("product_id")
            or ""
        ).strip()
        # Same action + same/empty subject → duplicate. Distinct product subjects may share
        # generic verbs only when actions differ after normalization.
        composite = f"{key}|{subject}" if subject else key
        if key and (key in seen_action or composite in seen_action):
            # If identical action text regardless of subject — suppress (F3).
            if key in seen_action:
                cand = mark_suppressed(cand, SUPPRESS_DUPLICATE_ACTION)
                registry.append(
                    {
                        "decision_id": cand.get("decision_id"),
                        "suppression_reason": SUPPRESS_DUPLICATE_ACTION,
                        "decision_type": cand.get("decision_type"),
                        "root_cause_key": cand.get("root_cause_key"),
                        "business_domain": cand.get("business_domain"),
                        "duplicate_action_ar": str(
                            cand.get("merchant_decision") or ""
                        ).strip(),
                    }
                )
                continue
        if key:
            seen_action.add(key)
            if composite:
                seen_action.add(composite)
        survivors.append(cand)
    return survivors, registry


__all__ = [
    "SUPPRESS_DUPLICATE_ACTION",
    "SUPPRESS_SAME_ROOT_CAUSE",
    "SUPPRESS_SUBSUMED_BY_CANONICAL",
    "attach_root_cause_v1",
    "dedupe_candidates_v1",
    "dedupe_published_by_action_v1",
]
