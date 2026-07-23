# -*- coding: utf-8 -*-
"""
EB-1…EB-8 composition helpers — WP-ET-09 (Blueprint §5.2).

Rules are enforced by the Composer. No interpretation / recommendations.
"""
from __future__ import annotations

from typing import Any, Mapping

from services.evidence_truth.contracts_v1 import (
    EB_1_PROJECTION_ONLY,
    EB_2_NO_ZERO_FILL,
    EB_3_HAS_FLAGS,
    EB_4_EVIDENCE_REFS,
    EB_5_SCHEMA_VERSION,
    EB_6_CACHE_INVALIDATION,
    EB_7_NO_RAW_AUTHORITY,
    EB_8_DEMO_PROVENANCE,
)
from services.evidence_truth.kernel_v1 import (
    CONFIDENCE_UNKNOWN,
    FORBIDDEN_EVIDENCE_PAYLOAD_KEYS_V1,
    READINESS_READY,
    READINESS_TRUSTED,
    READINESS_UNAVAILABLE,
)

# Readiness ranks — Bundle slice must never exceed source Evidence certainty.
_READINESS_RANK = {
    "unknown": 0,
    "unavailable": 1,
    "insufficient": 2,
    "conflicting": 3,
    "ready": 4,
    "trusted": 5,
}

READY_OR_TRUSTED = frozenset({READINESS_READY, READINESS_TRUSTED})

EB_RULES_ENFORCED_V1: frozenset[str] = frozenset(
    {
        EB_1_PROJECTION_ONLY,
        EB_2_NO_ZERO_FILL,
        EB_3_HAS_FLAGS,
        EB_4_EVIDENCE_REFS,
        EB_5_SCHEMA_VERSION,
        EB_6_CACHE_INVALIDATION,
        EB_7_NO_RAW_AUTHORITY,
        EB_8_DEMO_PROVENANCE,
    }
)


def readiness_rank_v1(readiness: str) -> int:
    return int(_READINESS_RANK.get((readiness or "").strip().lower(), 0))


def has_ready_flag_v1(readiness: str) -> bool:
    """EB-3: has_* true only when readiness ≥ Ready."""
    return (readiness or "").strip().lower() in READY_OR_TRUSTED


def project_safe_facts_v1(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """
    EB-1 / OE-7: copy only non-guidance payload keys.

    Composer projects facts; never invents keys absent from Evidence.
    """
    out: dict[str, Any] = {}
    for key, value in dict(payload or {}).items():
        if key in FORBIDDEN_EVIDENCE_PAYLOAD_KEYS_V1:
            continue
        if key.startswith("_"):
            continue
        out[str(key)] = value
    return out


def missing_family_slice_defaults_v1(family: str, *, owner: str) -> dict[str, Any]:
    """EB-2: Unavailable/Unknown honesty — never zero-fill."""
    return {
        "family": family,
        "present": False,
        "has_ready": False,
        "readiness": READINESS_UNAVAILABLE,
        "confidence": CONFIDENCE_UNKNOWN,
        "owner": owner,
        "evidence_ref": None,
        "projected_facts": {},
        "notes": {
            "eb_2_no_zero_fill": True,
            "reason": "no_evidence_truth_for_family",
        },
    }


def provenance_is_demo_v1(provenance: str) -> bool:
    return (provenance or "").strip().lower() in {"demo", "fixture", "synthetic"}


def assert_no_raw_authority_imports_in_module_source_v1(source: str) -> list[str]:
    """
    EB-7 static-ish guard for tests: Composer source must not treat Raw as authority.

    Scans import / from-import lines only so string literals documenting banned
    modules do not false-positive.
    """
    banned_substrings = (
        "purchase_truth",
        "recovery_truth",
        "sqlalchemy",
        "ProductSignalEvent",
        "raw_traffic",
        "load_evidence_bundle_from_db",
    )
    offenders: list[str] = []
    for line in (source or "").splitlines():
        stripped = line.strip()
        if not (stripped.startswith("import ") or stripped.startswith("from ")):
            continue
        # Composer may only import evidence_truth / stdlib — flag Raw authorities
        for marker in banned_substrings:
            if marker in stripped:
                offenders.append(f"{marker}:{stripped}")
    return offenders
