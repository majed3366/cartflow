# -*- coding: utf-8 -*-
"""
Shadow Knowledge composition entrypoints — WP-ET-10.

Gated by CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_SHADOW (default OFF).
CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_INPUT remains unwired / unauthorized.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from services.evidence_truth.bundle_model_v1 import EvidenceBundleRecordV1
from services.evidence_truth.flags_v1 import (
    FLAG_KNOWLEDGE_COMPOSER_SHADOW,
    evidence_truth_flag_enabled,
)
from services.evidence_truth.kernel_v1 import (
    EvidenceValidationError,
    REJECT_SCHEMA_INVALID,
)
from services.evidence_truth.knowledge_composer_v1 import (
    assert_knowledge_consume_unauthorized_v1,
    compose_knowledge_record_v1,
)
from services.evidence_truth.knowledge_model_v1 import (
    KNOWLEDGE_TYPE_FAMILY_PRESENCE,
    KnowledgeRecordV1,
)


def knowledge_composer_shadow_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    return evidence_truth_flag_enabled(FLAG_KNOWLEDGE_COMPOSER_SHADOW, environ=environ)


def maybe_compose_knowledge_record_v1(
    *,
    store_slug: str,
    knowledge_type: str = KNOWLEDGE_TYPE_FAMILY_PRESENCE,
    bundle_ids: Sequence[str] | None = None,
    as_of: str = "",
    force: bool = False,
    persist: bool = True,
    environ: Mapping[str, str] | None = None,
    provenance: str = "production_shadow",
) -> dict[str, Any]:
    """Flag-gated Knowledge composition. force=True for harnesses/tests only."""
    assert_knowledge_consume_unauthorized_v1(environ=environ)
    if not force and not knowledge_composer_shadow_enabled(environ=environ):
        return {
            "ok": False,
            "skipped": True,
            "reason": "flag_off",
            "flag": FLAG_KNOWLEDGE_COMPOSER_SHADOW,
            "consumable": False,
        }
    try:
        record = compose_knowledge_record_v1(
            store_slug=store_slug,
            knowledge_type=knowledge_type,
            bundle_ids=bundle_ids,
            as_of=as_of,
            persist=persist,
            environ=environ,
            provenance=provenance,
        )
    except EvidenceValidationError as exc:
        return {
            "ok": False,
            "skipped": False,
            "reason": exc.reason_code,
            "message": str(exc),
            "consumable": False,
        }
    return {
        "ok": True,
        "skipped": False,
        "knowledge_id": record.knowledge_id,
        "knowledge_version": record.knowledge_version,
        "knowledge_type": record.knowledge_type,
        "store_slug": record.store_slug,
        "bundle_ref_count": len(record.bundle_refs),
        "evidence_ref_count": len(record.evidence_refs),
        "claim_count": len(record.claims),
        "readiness": record.readiness,
        "confidence": record.confidence,
        "consumable": False,
        "lifecycle_state": record.lifecycle_state,
        "record": record.to_dict(),
    }


def shadow_compose_knowledge_record_v1(
    *,
    store_slug: str,
    knowledge_type: str = KNOWLEDGE_TYPE_FAMILY_PRESENCE,
    bundles: Sequence[EvidenceBundleRecordV1] | None = None,
    bundle_ids: Sequence[str] | None = None,
    as_of: str = "",
    force: bool = True,
    persist: bool = True,
    environ: Mapping[str, str] | None = None,
    provenance: str = "synthetic",
) -> KnowledgeRecordV1:
    """Direct compose for harnesses (force default True)."""
    assert_knowledge_consume_unauthorized_v1(environ=environ)
    if not force and not knowledge_composer_shadow_enabled(environ=environ):
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, "knowledge_composer_shadow_flag_off"
        )
    return compose_knowledge_record_v1(
        store_slug=store_slug,
        knowledge_type=knowledge_type,
        bundles=bundles,
        bundle_ids=bundle_ids,
        as_of=as_of,
        persist=persist,
        environ=environ,
        provenance=provenance,
    )
