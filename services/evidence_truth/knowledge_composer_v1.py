# -*- coding: utf-8 -*-
"""
C-18 Knowledge Composer — WP-ET-10 shadow foundation.

Consumes Evidence Bundle only. Never Raw / Observation / Evidence Truth directly.
Produces pattern Knowledge Records — not Findings / Guidance.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Mapping, Optional, Sequence

from services.evidence_truth.accounting_v1 import (
    STAGE_KNOWLEDGE_OUT,
    get_evidence_accounting_ledger_v1,
)
from services.evidence_truth.bundle_model_v1 import EvidenceBundleRecordV1
from services.evidence_truth.bundle_store_v1 import (
    EvidenceBundleStoreV1,
    get_evidence_bundle_store_v1,
)
from services.evidence_truth.flags_v1 import (
    FLAG_KNOWLEDGE_COMPOSER_INPUT,
    evidence_truth_flag_enabled,
)
from services.evidence_truth.kernel_v1 import (
    CONFIDENCE_INSUFFICIENT,
    CONFIDENCE_UNKNOWN,
    READINESS_INSUFFICIENT,
    READINESS_UNKNOWN,
    EvidenceValidationError,
    REJECT_MISSING_SOURCES,
    REJECT_SCHEMA_INVALID,
)
from services.evidence_truth.knowledge_composition_rules_v1 import (
    conservative_confidence_v1,
    conservative_readiness_v1,
    knowledge_type_allows_families_v1,
    routing_authorized_v1,
)
from services.evidence_truth.knowledge_model_v1 import (
    KNOWLEDGE_COMPOSER_OWNER,
    KNOWLEDGE_ELIGIBILITY_SHADOW_ONLY,
    KNOWLEDGE_LIFECYCLE_SHADOW,
    KNOWLEDGE_SCHEMA_VERSION_V1,
    KNOWLEDGE_TYPE_FAMILY_PRESENCE,
    KNOWLEDGE_TYPE_READY_FAMILY_SET,
    KnowledgeBundleRefV1,
    KnowledgeClaimRefV1,
    KnowledgeEvidenceRefV1,
    KnowledgeRecordV1,
    validate_knowledge_record_constitutional_v1,
)
from services.evidence_truth.knowledge_store_v1 import get_knowledge_record_store_v1


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def knowledge_consume_wired_v1(*, environ: Mapping[str, str] | None = None) -> bool:
    """
    WP-ET-10: Knowledge INPUT / Home / Findings consumption remains unwired.

    Even if CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_INPUT is toggled ON, this package
    never authorizes production Knowledge Layer / Home / Findings consumers.
    """
    _ = environ
    return False


def assert_knowledge_consume_unauthorized_v1(
    *, environ: Mapping[str, str] | None = None
) -> None:
    if knowledge_consume_wired_v1(environ=environ):
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            "knowledge_composer_input_not_wired_in_wp_et_10",
        )
    _ = evidence_truth_flag_enabled(FLAG_KNOWLEDGE_COMPOSER_INPUT, environ=environ)
    if routing_authorized_v1():
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            "knowledge_routing_not_authorized_in_wp_et_10",
        )


def _knowledge_id_v1(
    *,
    store_slug: str,
    knowledge_type: str,
    as_of: str,
    bundle_keys: tuple[str, ...],
) -> str:
    material = "|".join(
        [store_slug.strip().lower(), knowledge_type, as_of, ",".join(bundle_keys)]
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"krec_{digest}"


def _resolve_bundles(
    *,
    store_slug: str,
    bundle_ids: Sequence[str] | None,
    bundle_store: EvidenceBundleStoreV1,
    bundles: Sequence[EvidenceBundleRecordV1] | None,
) -> list[EvidenceBundleRecordV1]:
    if bundles:
        out = [b for b in bundles if (b.store_slug or "").strip().lower() == store_slug]
        if not out:
            raise EvidenceValidationError(
                REJECT_MISSING_SOURCES, "no_bundles_for_store"
            )
        return list(out)
    resolved: list[EvidenceBundleRecordV1] = []
    if bundle_ids:
        for bid in bundle_ids:
            b = bundle_store.get(bid)
            if b is None:
                raise EvidenceValidationError(
                    REJECT_MISSING_SOURCES, f"bundle_not_found:{bid}"
                )
            if (b.store_slug or "").strip().lower() != store_slug:
                raise EvidenceValidationError(
                    REJECT_SCHEMA_INVALID, f"bundle_store_mismatch:{bid}"
                )
            resolved.append(b)
        return resolved
    latest = bundle_store.latest_for_store(store_slug)
    if latest is None:
        raise EvidenceValidationError(
            REJECT_MISSING_SOURCES, "no_evidence_bundle_for_store"
        )
    return [latest]


def _collect_evidence_refs(
    bundles: Sequence[EvidenceBundleRecordV1],
) -> list[KnowledgeEvidenceRefV1]:
    refs: list[KnowledgeEvidenceRefV1] = []
    seen: set[str] = set()
    for bundle in bundles:
        for eref in bundle.evidence_refs:
            key = f"{eref.evidence_id}:{eref.evidence_version}"
            if key in seen:
                continue
            seen.add(key)
            refs.append(
                KnowledgeEvidenceRefV1(
                    evidence_id=eref.evidence_id,
                    evidence_version=int(eref.evidence_version),
                    family=eref.family,
                    readiness=eref.readiness,
                    confidence=eref.confidence,
                    bundle_id=bundle.bundle_id,
                )
            )
    return refs


def _compose_family_presence(
    bundles: Sequence[EvidenceBundleRecordV1],
) -> tuple[list[KnowledgeClaimRefV1], dict, str, str]:
    """Pattern: which families are present across Bundles (not commercial meaning)."""
    present: dict[str, dict] = {}
    readiness_vals: list[str] = []
    confidence_vals: list[str] = []
    claims: list[KnowledgeClaimRefV1] = []

    for bundle in bundles:
        for fam, slice_ in (bundle.families or {}).items():
            if not slice_.present or slice_.evidence_ref is None:
                continue
            eref = slice_.evidence_ref
            readiness_vals.append(eref.readiness)
            confidence_vals.append(eref.confidence)
            present[fam] = {
                "present": True,
                "has_ready": bool(slice_.has_ready),
                "readiness": eref.readiness,
                "confidence": eref.confidence,
                "evidence_id": eref.evidence_id,
            }
            claims.append(
                KnowledgeClaimRefV1(
                    claim_id=f"presence:{fam}:{eref.evidence_id}",
                    claim_kind="family_present",
                    evidence_ids=(eref.evidence_id,),
                    bundle_ids=(bundle.bundle_id,),
                    readiness=eref.readiness,
                    confidence=eref.confidence,
                    payload={
                        "family": fam,
                        "present": True,
                        "has_ready": bool(slice_.has_ready),
                    },
                )
            )

    if not claims:
        return (
            [],
            {"families_present": [], "pattern": "family_presence", "empty": True},
            READINESS_INSUFFICIENT,
            CONFIDENCE_INSUFFICIENT,
        )

    readiness = conservative_readiness_v1(readiness_vals)
    confidence = conservative_confidence_v1(confidence_vals, readiness=readiness)
    summary = {
        "pattern": "family_presence",
        "families_present": sorted(present.keys()),
        "family_count": len(present),
        "by_family": present,
    }
    return claims, summary, readiness, confidence


def _compose_ready_family_set(
    bundles: Sequence[EvidenceBundleRecordV1],
) -> tuple[list[KnowledgeClaimRefV1], dict, str, str]:
    """Pattern: set of families with has_ready from Bundle (BK-2 gated)."""
    ready_families: list[str] = []
    claims: list[KnowledgeClaimRefV1] = []
    readiness_vals: list[str] = []
    confidence_vals: list[str] = []

    for bundle in bundles:
        for fam, slice_ in (bundle.families or {}).items():
            if not slice_.present or slice_.evidence_ref is None:
                continue
            if not slice_.has_ready:
                continue
            eref = slice_.evidence_ref
            ready_families.append(fam)
            readiness_vals.append(eref.readiness)
            confidence_vals.append(eref.confidence)
            claims.append(
                KnowledgeClaimRefV1(
                    claim_id=f"ready:{fam}:{eref.evidence_id}",
                    claim_kind="family_ready",
                    evidence_ids=(eref.evidence_id,),
                    bundle_ids=(bundle.bundle_id,),
                    readiness=eref.readiness,
                    confidence=eref.confidence,
                    payload={"family": fam, "has_ready": True},
                )
            )

    if not claims:
        # Honest insufficient pattern — no Ready families (e.g. visitor unauthorized)
        return (
            [
                KnowledgeClaimRefV1(
                    claim_id="ready:none",
                    claim_kind="ready_family_set_empty",
                    evidence_ids=tuple(
                        r.evidence_id
                        for b in bundles
                        for r in b.evidence_refs
                    )[:1]
                    or ("",),
                    bundle_ids=tuple(b.bundle_id for b in bundles),
                    readiness=READINESS_INSUFFICIENT,
                    confidence=CONFIDENCE_INSUFFICIENT,
                    payload={"ready_families": [], "empty": True},
                )
            ],
            {
                "pattern": "ready_family_set",
                "ready_families": [],
                "empty": True,
            },
            READINESS_INSUFFICIENT,
            CONFIDENCE_INSUFFICIENT,
        )

    # Fix empty evidence_ids edge — validator requires evidence_ids
    readiness = conservative_readiness_v1(readiness_vals)
    confidence = conservative_confidence_v1(confidence_vals, readiness=readiness)
    summary = {
        "pattern": "ready_family_set",
        "ready_families": sorted(set(ready_families)),
        "count": len(set(ready_families)),
    }
    return claims, summary, readiness, confidence


def compose_knowledge_record_v1(
    *,
    store_slug: str,
    knowledge_type: str = KNOWLEDGE_TYPE_FAMILY_PRESENCE,
    bundle_ids: Sequence[str] | None = None,
    bundles: Sequence[EvidenceBundleRecordV1] | None = None,
    as_of: str = "",
    persist: bool = True,
    environ: Mapping[str, str] | None = None,
    provenance: str = "production_shadow",
    bundle_store: Optional[EvidenceBundleStoreV1] = None,
) -> KnowledgeRecordV1:
    """
    Compose one Knowledge Record from one or more Evidence Bundles.

    Fail closed without Bundle / without Evidence refs. Never upgrades certainty.
    """
    assert_knowledge_consume_unauthorized_v1(environ=environ)

    slug = (store_slug or "").strip().lower()
    if not slug:
        raise EvidenceValidationError(REJECT_SCHEMA_INVALID, "store_slug_required")
    if knowledge_type not in {
        KNOWLEDGE_TYPE_FAMILY_PRESENCE,
        KNOWLEDGE_TYPE_READY_FAMILY_SET,
    }:
        raise EvidenceValidationError(REJECT_SCHEMA_INVALID, "unknown_knowledge_type")

    bstore = bundle_store or get_evidence_bundle_store_v1()
    resolved = _resolve_bundles(
        store_slug=slug,
        bundle_ids=bundle_ids,
        bundle_store=bstore,
        bundles=bundles,
    )

    # BK-1 family declaration gate
    family_map = {}
    for b in resolved:
        family_map.update(b.families or {})
    if not knowledge_type_allows_families_v1(knowledge_type, family_map):
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, "bk1_required_families_unsatisfied"
        )

    evidence_refs = _collect_evidence_refs(resolved)
    if not evidence_refs:
        raise EvidenceValidationError(
            REJECT_MISSING_SOURCES, "bundle_has_no_evidence_refs"
        )

    if knowledge_type == KNOWLEDGE_TYPE_READY_FAMILY_SET:
        claims, summary, readiness, confidence = _compose_ready_family_set(resolved)
    else:
        claims, summary, readiness, confidence = _compose_family_presence(resolved)

    # Empty presence → fail closed (no orphan pattern without claims+refs)
    if knowledge_type == KNOWLEDGE_TYPE_FAMILY_PRESENCE and not claims:
        raise EvidenceValidationError(
            REJECT_MISSING_SOURCES, "no_present_families_for_knowledge"
        )

    # ready set empty claim must still have evidence_ids — repair if blank
    fixed_claims: list[KnowledgeClaimRefV1] = []
    fallback_eid = evidence_refs[0].evidence_id
    for claim in claims:
        eids = tuple(e for e in claim.evidence_ids if (e or "").strip())
        if not eids:
            eids = (fallback_eid,)
        fixed_claims.append(
            KnowledgeClaimRefV1(
                claim_id=claim.claim_id,
                claim_kind=claim.claim_kind,
                evidence_ids=eids,
                bundle_ids=claim.bundle_ids,
                readiness=claim.readiness,
                confidence=claim.confidence,
                payload=claim.payload,
            )
        )

    as_of_s = (as_of or "").strip() or _utc_now_iso()
    bundle_refs = tuple(
        KnowledgeBundleRefV1(
            bundle_id=b.bundle_id,
            bundle_version=int(b.bundle_version),
            store_slug=b.store_slug,
            schema_version=b.schema_version,
        )
        for b in resolved
    )
    bundle_keys = tuple(sorted(f"{b.bundle_id}:{b.bundle_version}" for b in resolved))
    knowledge_id = _knowledge_id_v1(
        store_slug=slug,
        knowledge_type=knowledge_type,
        as_of=as_of_s,
        bundle_keys=bundle_keys,
    )

    kstore = get_knowledge_record_store_v1()
    prior = kstore.latest_for_store(slug)
    knowledge_version = 1
    if prior is not None and prior.knowledge_id == knowledge_id:
        knowledge_version = int(prior.knowledge_version)
    elif prior is not None:
        knowledge_version = int(prior.knowledge_version) + 1

    window_start = resolved[0].window_start
    window_end = resolved[0].window_end

    record = KnowledgeRecordV1(
        knowledge_id=knowledge_id,
        knowledge_version=knowledge_version,
        knowledge_type=knowledge_type,
        schema_version=KNOWLEDGE_SCHEMA_VERSION_V1,
        store_slug=slug,
        window_start=window_start,
        window_end=window_end,
        as_of=as_of_s,
        composer_owner=KNOWLEDGE_COMPOSER_OWNER,
        bundle_refs=bundle_refs,
        evidence_refs=tuple(evidence_refs),
        claims=tuple(fixed_claims),
        readiness=readiness or READINESS_UNKNOWN,
        confidence=confidence or CONFIDENCE_UNKNOWN,
        pattern_summary=summary,
        provenance=provenance,
        eligibility=KNOWLEDGE_ELIGIBILITY_SHADOW_ONLY,
        lifecycle_state=KNOWLEDGE_LIFECYCLE_SHADOW,
        consumable=False,
        composition_notes={
            "bk_rules": ["BK-1", "BK-2", "BK-3", "BK-4", "BK-5"],
            "input": "evidence_bundle_only",
            "consume_authorized": False,
            "routing_authorized": False,
            "findings_connected": False,
            "home_connected": False,
            "bundle_count": len(resolved),
        },
    )
    validate_knowledge_record_constitutional_v1(record)

    if persist:
        kstore.put(record)
        get_evidence_accounting_ledger_v1().increment_stage(STAGE_KNOWLEDGE_OUT, n=1)

    return record
