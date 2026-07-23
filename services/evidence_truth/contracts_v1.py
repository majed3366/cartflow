# -*- coding: utf-8 -*-
"""
C-01 contract vocabulary — OE / EB / BK / KF / FG rule IDs (Blueprint §5).

Library constants only. No enforcement wiring in WP-ET-01 beyond enum presence.
"""
from __future__ import annotations

# Observation → Evidence
OE_1_SOURCES = "OE-1"
OE_2_PERIOD_CONTAINMENT = "OE-2"
OE_3_DEDUPE = "OE-3"
OE_4_OUT_OF_ORDER = "OE-4"
OE_5_READINESS = "OE-5"
OE_6_IDENTITY = "OE-6"
OE_7_NO_GUIDANCE_TEXT = "OE-7"

# Evidence → EvidenceBundle
EB_1_PROJECTION_ONLY = "EB-1"
EB_2_NO_ZERO_FILL = "EB-2"
EB_3_HAS_FLAGS = "EB-3"
EB_4_EVIDENCE_REFS = "EB-4"
EB_5_SCHEMA_VERSION = "EB-5"
EB_6_CACHE_INVALIDATION = "EB-6"
EB_7_NO_RAW_AUTHORITY = "EB-7"
EB_8_DEMO_PROVENANCE = "EB-8"

# EvidenceBundle → Knowledge
BK_1_REQUIRED_FAMILIES = "BK-1"
BK_2_READINESS_GATE = "BK-2"
BK_3_CLAIM_EVIDENCE_ID = "BK-3"
BK_4_NO_EVIDENCE_WRITE = "BK-4"
BK_5_ROUTING_AFTER_PRODUCE = "BK-5"

# Knowledge/Bundle → Business Findings
KF_1_BUNDLE_PREDICATES = "KF-1"
KF_2_INSUFFICIENT_VALID = "KF-2"
KF_3_VISITOR_NONE_NE_ZERO = "KF-3"
KF_4_ONE_MEANING = "KF-4"
KF_5_EXPLAINABILITY = "KF-5"

# Findings → Guidance
FG_1_FINDING_REQUIRED = "FG-1"
FG_2_TRUST_PRIVILEGE = "FG-2"
FG_3_NO_UPSTREAM_MUTATE = "FG-3"
FG_4_SURFACES_CONSUME_ROUTED = "FG-4"

CONTRACT_RULE_IDS_V1: frozenset[str] = frozenset(
    {
        OE_1_SOURCES,
        OE_2_PERIOD_CONTAINMENT,
        OE_3_DEDUPE,
        OE_4_OUT_OF_ORDER,
        OE_5_READINESS,
        OE_6_IDENTITY,
        OE_7_NO_GUIDANCE_TEXT,
        EB_1_PROJECTION_ONLY,
        EB_2_NO_ZERO_FILL,
        EB_3_HAS_FLAGS,
        EB_4_EVIDENCE_REFS,
        EB_5_SCHEMA_VERSION,
        EB_6_CACHE_INVALIDATION,
        EB_7_NO_RAW_AUTHORITY,
        EB_8_DEMO_PROVENANCE,
        BK_1_REQUIRED_FAMILIES,
        BK_2_READINESS_GATE,
        BK_3_CLAIM_EVIDENCE_ID,
        BK_4_NO_EVIDENCE_WRITE,
        BK_5_ROUTING_AFTER_PRODUCE,
        KF_1_BUNDLE_PREDICATES,
        KF_2_INSUFFICIENT_VALID,
        KF_3_VISITOR_NONE_NE_ZERO,
        KF_4_ONE_MEANING,
        KF_5_EXPLAINABILITY,
        FG_1_FINDING_REQUIRED,
        FG_2_TRUST_PRIVILEGE,
        FG_3_NO_UPSTREAM_MUTATE,
        FG_4_SURFACES_CONSUME_ROUTED,
    }
)

CONTRACT_STAGE_PREFIXES_V1: frozenset[str] = frozenset({"OE", "EB", "BK", "KF", "FG"})


def is_known_contract_rule_id(rule_id: str) -> bool:
    return (rule_id or "").strip().upper() in CONTRACT_RULE_IDS_V1
