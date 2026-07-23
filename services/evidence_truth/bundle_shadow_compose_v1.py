# -*- coding: utf-8 -*-
"""
Shadow Bundle composition entrypoints — WP-ET-09.

Gated by CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW (default OFF).
CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_CONSUME remains unwired / unauthorized.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.evidence_truth.bundle_composer_v1 import (
    assert_bundle_consume_unauthorized_v1,
    compose_evidence_bundle_v1,
)
from services.evidence_truth.bundle_model_v1 import EvidenceBundleRecordV1
from services.evidence_truth.flags_v1 import (
    FLAG_BUNDLE_COMPOSER_SHADOW,
    evidence_truth_flag_enabled,
)
from services.evidence_truth.kernel_v1 import (
    EvidenceValidationError,
    REJECT_SCHEMA_INVALID,
)


def bundle_composer_shadow_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    return evidence_truth_flag_enabled(FLAG_BUNDLE_COMPOSER_SHADOW, environ=environ)


def maybe_compose_evidence_bundle_v1(
    *,
    store_slug: str,
    window_start: str = "",
    window_end: Optional[str] = None,
    as_of: str = "",
    force: bool = False,
    persist: bool = True,
    environ: Mapping[str, str] | None = None,
    provenance: str = "production_shadow",
) -> dict[str, Any]:
    """
    Flag-gated Bundle composition.

    When flag OFF and force=False → skipped (production unchanged).
    force=True is for harnesses / tests only.
    """
    assert_bundle_consume_unauthorized_v1(environ=environ)
    if not force and not bundle_composer_shadow_enabled(environ=environ):
        return {
            "ok": False,
            "skipped": True,
            "reason": "flag_off",
            "flag": FLAG_BUNDLE_COMPOSER_SHADOW,
            "consumable": False,
        }
    try:
        bundle = compose_evidence_bundle_v1(
            store_slug=store_slug,
            window_start=window_start,
            window_end=window_end,
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
        "bundle_id": bundle.bundle_id,
        "bundle_version": bundle.bundle_version,
        "store_slug": bundle.store_slug,
        "evidence_ref_count": len(bundle.evidence_refs),
        "has_visitor_truth": bundle.has_visitor_truth,
        "visitor_total": bundle.visitor_total,
        "visitor_bundle_fields_authorized": bundle.visitor_bundle_fields_authorized,
        "consumable": False,
        "lifecycle_state": bundle.lifecycle_state,
        "eligibility": bundle.eligibility,
        "bundle": bundle.to_dict(),
    }


def shadow_compose_evidence_bundle_v1(
    *,
    store_slug: str,
    window_start: str = "",
    window_end: Optional[str] = None,
    as_of: str = "",
    force: bool = True,
    persist: bool = True,
    environ: Mapping[str, str] | None = None,
    provenance: str = "synthetic",
) -> EvidenceBundleRecordV1:
    """Direct compose for harnesses (force default True)."""
    assert_bundle_consume_unauthorized_v1(environ=environ)
    if not force and not bundle_composer_shadow_enabled(environ=environ):
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, "bundle_composer_shadow_flag_off"
        )
    return compose_evidence_bundle_v1(
        store_slug=store_slug,
        window_start=window_start,
        window_end=window_end,
        as_of=as_of,
        persist=persist,
        environ=environ,
        provenance=provenance,
    )
