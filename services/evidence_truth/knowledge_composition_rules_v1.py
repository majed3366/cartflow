# -*- coding: utf-8 -*-
"""
BK-1…BK-5 composition helpers — WP-ET-10 (Blueprint §5.3).

Knowledge patterns only. No Findings / Guidance / merchant speech.
"""
from __future__ import annotations

from typing import Mapping

from services.evidence_truth.bundle_composition_rules_v1 import readiness_rank_v1
from services.evidence_truth.contracts_v1 import (
    BK_1_REQUIRED_FAMILIES,
    BK_2_READINESS_GATE,
    BK_3_CLAIM_EVIDENCE_ID,
    BK_4_NO_EVIDENCE_WRITE,
    BK_5_ROUTING_AFTER_PRODUCE,
)
from services.evidence_truth.kernel_v1 import (
    CONFIDENCE_INSUFFICIENT,
    CONFIDENCE_UNKNOWN,
    READINESS_INSUFFICIENT,
    READINESS_READY,
    READINESS_TRUSTED,
    READINESS_UNKNOWN,
)
from services.evidence_truth.knowledge_model_v1 import (
    KNOWLEDGE_TYPE_FAMILY_PRESENCE,
    KNOWLEDGE_TYPE_READY_FAMILY_SET,
)

BK_RULES_ENFORCED_V1: frozenset[str] = frozenset(
    {
        BK_1_REQUIRED_FAMILIES,
        BK_2_READINESS_GATE,
        BK_3_CLAIM_EVIDENCE_ID,
        BK_4_NO_EVIDENCE_WRITE,
        BK_5_ROUTING_AFTER_PRODUCE,
    }
)

# BK-1: declared families each knowledge type may reference
KNOWLEDGE_REQUIRED_FAMILIES_V1: dict[str, frozenset[str]] = {
    KNOWLEDGE_TYPE_FAMILY_PRESENCE: frozenset(),  # any present family; none required to start
    KNOWLEDGE_TYPE_READY_FAMILY_SET: frozenset(),  # may be empty → insufficient pattern
}

READY_OR_TRUSTED = frozenset({READINESS_READY, READINESS_TRUSTED})


def conservative_readiness_v1(readiness_values: list[str]) -> str:
    """BK-2: Knowledge readiness never exceeds weakest supporting Evidence."""
    if not readiness_values:
        return READINESS_UNKNOWN
    return min(readiness_values, key=readiness_rank_v1)


def conservative_confidence_v1(confidence_values: list[str], *, readiness: str) -> str:
    """BK-2: if readiness below Ready, confidence cannot be confirmed/high."""
    if readiness not in READY_OR_TRUSTED:
        if readiness in {READINESS_INSUFFICIENT, READINESS_UNKNOWN}:
            return CONFIDENCE_INSUFFICIENT if readiness == READINESS_INSUFFICIENT else CONFIDENCE_UNKNOWN
        return CONFIDENCE_UNKNOWN
    if not confidence_values:
        return CONFIDENCE_UNKNOWN
    # Prefer weakest confidence — never invent higher certainty
    order = (
        "unknown",
        "insufficient",
        "low",
        "medium",
        "high",
        "confirmed",
    )
    rank = {name: i for i, name in enumerate(order)}

    def _rank(c: str) -> int:
        return int(rank.get((c or "").strip().lower(), 0))

    return min(confidence_values, key=_rank)


def knowledge_type_allows_families_v1(
    knowledge_type: str, families: Mapping[str, object]
) -> bool:
    """BK-1: undeclared knowledge types blocked; declared required families checked."""
    required = KNOWLEDGE_REQUIRED_FAMILIES_V1.get(knowledge_type)
    if required is None:
        return False
    if not required:
        return True
    return all(fam in families for fam in required)


def assert_no_evidence_write_imports_in_module_source_v1(source: str) -> list[str]:
    """
    BK-4: Knowledge Composer must not write Evidence / dual-write publish.

    Scans import lines only.
    """
    banned = (
        "evidence_dual_write",
        "maybe_publish_",
        "shadow_dual_write_evidence",
        "purchase_evidence_publisher",
        "visitor_evidence_publisher",
        "from sqlalchemy",
        "import sqlalchemy",
    )
    offenders: list[str] = []
    for line in (source or "").splitlines():
        stripped = line.strip()
        if not (stripped.startswith("import ") or stripped.startswith("from ")):
            continue
        for marker in banned:
            if marker in stripped:
                offenders.append(f"{marker}:{stripped}")
    return offenders


def routing_authorized_v1() -> bool:
    """BK-5: routing after produce is not authorized in WP-ET-10."""
    return False
