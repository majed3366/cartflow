# -*- coding: utf-8 -*-
"""
C-16 Evidence Bundle Composer — WP-ET-09 shadow foundation.

Projects Evidence Truth → Evidence Bundle. No Raw authority. No interpretation.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.evidence_truth.accounting_v1 import (
    STAGE_BUNDLE_PROJECTION_OUT,
    get_evidence_accounting_ledger_v1,
)
from services.evidence_truth.bundle_composition_rules_v1 import (
    has_ready_flag_v1,
    missing_family_slice_defaults_v1,
    project_safe_facts_v1,
    provenance_is_demo_v1,
)
from services.evidence_truth.bundle_model_v1 import (
    BUNDLE_COMPOSER_OWNER,
    BUNDLE_ELIGIBILITY_NOT_CONSUMABLE,
    BUNDLE_ELIGIBILITY_SHADOW_ONLY,
    BUNDLE_LIFECYCLE_SHADOW,
    BUNDLE_SCHEMA_VERSION_V1,
    BundleEvidenceRefV1,
    BundleFamilySliceV1,
    EvidenceBundleRecordV1,
    validate_evidence_bundle_constitutional_v1,
)
from services.evidence_truth.bundle_store_v1 import get_evidence_bundle_store_v1
from services.evidence_truth.evidence_model_v1 import EvidenceTruthRecordV1
from services.evidence_truth.evidence_store_v1 import (
    EvidenceTruthStoreV1,
    get_evidence_truth_store_v1,
)
from services.evidence_truth.families_v1 import (
    EVIDENCE_FAMILIES_V1,
    FAMILY_VISITOR,
    list_evidence_families,
)
from services.evidence_truth.flags_v1 import (
    FLAG_BUNDLE_COMPOSER_CONSUME,
    FLAG_VISITOR_BUNDLE_FIELDS,
    evidence_truth_flag_enabled,
)
from services.evidence_truth.kernel_v1 import (
    EvidenceValidationError,
    REJECT_MISSING_SOURCES,
    REJECT_SCHEMA_INVALID,
)
from services.evidence_truth.ownership_v1 import owner_for_family


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def bundle_consume_wired_v1(*, environ: Mapping[str, str] | None = None) -> bool:
    """
    WP-ET-09: Bundle CONSUME is declared but unwired.

    Even if CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_CONSUME is toggled ON, this package
    never authorizes Knowledge / Findings / UI consumption.
    """
    _ = environ  # reserved for future cutover wiring
    return False


def assert_bundle_consume_unauthorized_v1(
    *, environ: Mapping[str, str] | None = None
) -> None:
    """Runtime guard: consumption remains unauthorized in WP-ET-09."""
    if bundle_consume_wired_v1(environ=environ):
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID,
            "bundle_composer_consume_not_wired_in_wp_et_09",
        )
    # Flag may be ON in env for soak prep, but consumable path stays closed.
    _ = evidence_truth_flag_enabled(FLAG_BUNDLE_COMPOSER_CONSUME, environ=environ)


def _observation_refs_from_record(record: EvidenceTruthRecordV1) -> tuple[str, ...]:
    refs = []
    for src in record.envelope.sources or ():
        ref = (src.observation_ref or "").strip()
        if ref:
            refs.append(ref)
    # Prefer explicit source_observations when present
    for oid in record.source_observations or ():
        s = (oid or "").strip()
        if s and s not in refs:
            refs.append(s)
    return tuple(refs)


def _build_evidence_ref(record: EvidenceTruthRecordV1) -> BundleEvidenceRefV1:
    obs_refs = _observation_refs_from_record(record)
    return BundleEvidenceRefV1(
        evidence_id=record.evidence_id,
        evidence_version=int(record.evidence_version),
        family=record.canonical_family,
        evidence_type=record.evidence_type,
        owner=record.owner,
        readiness=record.readiness,
        confidence=record.confidence,
        source_observations=tuple(record.source_observations or ()),
        observation_refs=obs_refs,
    )


def _select_latest_by_family(
    store: EvidenceTruthStoreV1,
    *,
    store_slug: str,
    window_start: str = "",
    window_end: Optional[str] = None,
) -> dict[str, EvidenceTruthRecordV1]:
    rows = store.list_recent(limit=500, store_slug=store_slug)
    best: dict[str, EvidenceTruthRecordV1] = {}
    ws = (window_start or "").strip()
    we = (window_end or "").strip() if window_end else ""
    for rec in rows:
        observed = (rec.envelope.freshness.observed_at or rec.envelope.as_of or "").strip()
        if ws and observed and observed < ws:
            continue
        if we and observed and observed >= we:
            continue
        fam = rec.canonical_family
        prev = best.get(fam)
        if prev is None:
            best[fam] = rec
            continue
        # Prefer higher version, then newer as_of
        if int(rec.evidence_version) > int(prev.evidence_version):
            best[fam] = rec
        elif int(rec.evidence_version) == int(prev.evidence_version):
            if (rec.envelope.as_of or "") > (prev.envelope.as_of or ""):
                best[fam] = rec
    return best


def _bundle_id_v1(
    *,
    store_slug: str,
    window_start: str,
    window_end: Optional[str],
    as_of: str,
    evidence_keys: tuple[str, ...],
) -> str:
    material = "|".join(
        [
            store_slug.strip().lower(),
            window_start,
            window_end or "",
            as_of,
            ",".join(evidence_keys),
        ]
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"ebundle_{digest}"


def compose_evidence_bundle_v1(
    *,
    store_slug: str,
    window_start: str = "",
    window_end: Optional[str] = None,
    as_of: str = "",
    evidence_store: Optional[EvidenceTruthStoreV1] = None,
    persist: bool = True,
    environ: Mapping[str, str] | None = None,
    provenance: str = "production_shadow",
) -> EvidenceBundleRecordV1:
    """
    Compose one Evidence Bundle from published Evidence Truth for a store.

    Fail closed when no Evidence exists for the store (no fabricated Bundle).
    Visitor Bundle fields remain unauthorized unless FLAG_VISITOR_BUNDLE_FIELDS.
    """
    assert_bundle_consume_unauthorized_v1(environ=environ)

    slug = (store_slug or "").strip().lower()
    if not slug:
        raise EvidenceValidationError(REJECT_SCHEMA_INVALID, "store_slug_required")

    estore = evidence_store or get_evidence_truth_store_v1()
    as_of_s = (as_of or "").strip() or _utc_now_iso()
    ws = (window_start or "").strip() or "1970-01-01T00:00:00+00:00"
    we = (window_end or "").strip() or None

    by_family = _select_latest_by_family(
        estore, store_slug=slug, window_start=ws if window_start else "", window_end=we
    )
    if not by_family:
        raise EvidenceValidationError(
            REJECT_MISSING_SOURCES,
            "no_evidence_truth_for_store",
        )

    visitor_fields_authorized = evidence_truth_flag_enabled(
        FLAG_VISITOR_BUNDLE_FIELDS, environ=environ or {}
    )

    families: dict[str, BundleFamilySliceV1] = {}
    refs: list[BundleEvidenceRefV1] = []
    readiness_summary: dict[str, str] = {}
    evidence_keys: list[str] = []

    for fam_entry in list_evidence_families():
        fam = fam_entry.family
        owner = owner_for_family(fam) or fam_entry.owner_module
        rec = by_family.get(fam)
        if rec is None:
            defaults = missing_family_slice_defaults_v1(fam, owner=owner)
            families[fam] = BundleFamilySliceV1(**defaults)
            readiness_summary[fam] = defaults["readiness"]
            continue

        ref = _build_evidence_ref(rec)
        if not ref.source_observations and not ref.observation_refs:
            raise EvidenceValidationError(
                REJECT_MISSING_SOURCES,
                f"evidence_missing_observation_trace:{rec.evidence_id}",
            )
        refs.append(ref)
        evidence_keys.append(f"{rec.evidence_id}:{rec.evidence_version}")

        facts = project_safe_facts_v1(rec.envelope.payload)
        ready = has_ready_flag_v1(rec.readiness)

        # Visitor slice: never expose visitor truth to Bundle consumers unless authorized
        notes: dict[str, Any] = {
            "eb_1_projection_only": True,
            "source_evidence_readiness": rec.readiness,
            "source_evidence_confidence": rec.confidence,
        }
        if fam == FAMILY_VISITOR and not visitor_fields_authorized:
            notes["visitor_bundle_fields_deferred"] = True
            notes["cartflow_evidence_visitor_bundle_fields"] = False
            # Keep projected visitor facts internal to slice for ops/shadow inspect,
            # but has_ready / has_visitor_truth stay false for consumer-facing flags.
            families[fam] = BundleFamilySliceV1(
                family=fam,
                present=True,
                has_ready=False,
                readiness=rec.readiness,
                confidence=rec.confidence,
                owner=rec.owner,
                evidence_ref=ref,
                projected_facts=facts,
                notes=notes,
            )
        else:
            families[fam] = BundleFamilySliceV1(
                family=fam,
                present=True,
                has_ready=ready,
                readiness=rec.readiness,
                confidence=rec.confidence,
                owner=rec.owner,
                evidence_ref=ref,
                projected_facts=facts,
                notes=notes,
            )
        readiness_summary[fam] = rec.readiness

    # Visitor honesty fields at Bundle root (EB-3 / KF-3)
    visitor_slice = families.get(FAMILY_VISITOR)
    has_visitor_truth = False
    visitor_total: Any = None
    if (
        visitor_fields_authorized
        and visitor_slice is not None
        and visitor_slice.present
        and has_ready_flag_v1(visitor_slice.readiness)
    ):
        has_visitor_truth = True
        # Project total only if Evidence payload already carries it — never invent/zero-fill
        if "visitor_total" in (visitor_slice.projected_facts or {}):
            visitor_total = visitor_slice.projected_facts.get("visitor_total")
        elif "presence_count" in (visitor_slice.projected_facts or {}):
            visitor_total = visitor_slice.projected_facts.get("presence_count")

    if provenance_is_demo_v1(provenance):
        # EB-8: demo must never be marked production Trusted at Bundle layer
        for fam, sl in list(families.items()):
            if sl.readiness == "trusted":
                families[fam] = BundleFamilySliceV1(
                    family=sl.family,
                    present=sl.present,
                    has_ready=False,
                    readiness="insufficient",
                    confidence=sl.confidence,
                    owner=sl.owner,
                    evidence_ref=sl.evidence_ref,
                    projected_facts=sl.projected_facts,
                    notes={**dict(sl.notes or {}), "eb_8_demo_not_trusted": True},
                )
                readiness_summary[fam] = "insufficient"

    bundle_id = _bundle_id_v1(
        store_slug=slug,
        window_start=ws,
        window_end=we,
        as_of=as_of_s,
        evidence_keys=tuple(sorted(evidence_keys)),
    )

    # Version: supersede prior store latest when content changes (EB-6)
    bstore = get_evidence_bundle_store_v1()
    prior = bstore.latest_for_store(slug)
    bundle_version = 1
    if prior is not None and prior.bundle_id == bundle_id:
        bundle_version = int(prior.bundle_version)
    elif prior is not None:
        bundle_version = int(prior.bundle_version) + 1

    bundle = EvidenceBundleRecordV1(
        bundle_id=bundle_id,
        bundle_version=bundle_version,
        schema_version=BUNDLE_SCHEMA_VERSION_V1,
        store_slug=slug,
        window_start=ws,
        window_end=we,
        as_of=as_of_s,
        composer_owner=BUNDLE_COMPOSER_OWNER,
        families=families,
        evidence_refs=tuple(refs),
        has_visitor_truth=has_visitor_truth,
        visitor_total=visitor_total,
        visitor_bundle_fields_authorized=visitor_fields_authorized,
        readiness_summary=readiness_summary,
        provenance=provenance,
        eligibility=BUNDLE_ELIGIBILITY_SHADOW_ONLY,
        lifecycle_state=BUNDLE_LIFECYCLE_SHADOW,
        consumable=False,
        composition_notes={
            "eb_rules": sorted(
                [
                    "EB-1",
                    "EB-2",
                    "EB-3",
                    "EB-4",
                    "EB-5",
                    "EB-6",
                    "EB-7",
                    "EB-8",
                ]
            ),
            "families_present": sorted(by_family.keys()),
            "families_registered": sorted(EVIDENCE_FAMILIES_V1.keys()),
            "consume_authorized": False,
            "eligibility_consume": BUNDLE_ELIGIBILITY_NOT_CONSUMABLE,
            "knowledge_connected": False,
            "findings_connected": False,
        },
    )
    validate_evidence_bundle_constitutional_v1(bundle)

    if persist:
        bstore.put(bundle)
        get_evidence_accounting_ledger_v1().increment_stage(
            STAGE_BUNDLE_PROJECTION_OUT, n=1
        )

    return bundle
