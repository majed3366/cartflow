# -*- coding: utf-8 -*-
"""
C-01 schema registry — version documentation for Evidence Truth envelopes/types.

Code-versioned registry (Blueprint C-01: versions documented in schema registry).
No DB persistence. No production publish path in WP-ET-01.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.evidence_truth.kernel_v1 import EVIDENCE_KERNEL_SCHEMA_VERSION


@dataclass(frozen=True)
class EvidenceSchemaEntryV1:
    schema_id: str
    schema_version: str
    kind: str  # envelope | family_evidence
    status: str  # current | reserved
    description: str


# Envelope + per-family evidence schemas (aligned with type_registry scaffold)
EVIDENCE_SCHEMA_REGISTRY_V1: dict[str, EvidenceSchemaEntryV1] = {
    EVIDENCE_KERNEL_SCHEMA_VERSION: EvidenceSchemaEntryV1(
        schema_id=EVIDENCE_KERNEL_SCHEMA_VERSION,
        schema_version=EVIDENCE_KERNEL_SCHEMA_VERSION,
        kind="envelope",
        status="current",
        description="Normative EvidenceEnvelopeV1 record shape (Architecture §2.0)",
    ),
    "visitor_evidence_v1": EvidenceSchemaEntryV1(
        schema_id="visitor_evidence_v1",
        schema_version="visitor_evidence_v1",
        kind="family_evidence",
        status="current",
        description="Visitor family evidence payload schema (publish deferred)",
    ),
    "product_evidence_v1": EvidenceSchemaEntryV1(
        schema_id="product_evidence_v1",
        schema_version="product_evidence_v1",
        kind="family_evidence",
        status="current",
        description="Product family evidence payload schema (publish deferred)",
    ),
    "cart_evidence_v1": EvidenceSchemaEntryV1(
        schema_id="cart_evidence_v1",
        schema_version="cart_evidence_v1",
        kind="family_evidence",
        status="current",
        description="Cart family evidence payload schema (publish deferred)",
    ),
    "recovery_evidence_v1": EvidenceSchemaEntryV1(
        schema_id="recovery_evidence_v1",
        schema_version="recovery_evidence_v1",
        kind="family_evidence",
        status="current",
        description="Recovery family evidence payload schema (publish deferred)",
    ),
    "purchase_evidence_v1": EvidenceSchemaEntryV1(
        schema_id="purchase_evidence_v1",
        schema_version="purchase_evidence_v1",
        kind="family_evidence",
        status="current",
        description="Purchase family evidence payload schema (publish deferred)",
    ),
    "communication_evidence_v1": EvidenceSchemaEntryV1(
        schema_id="communication_evidence_v1",
        schema_version="communication_evidence_v1",
        kind="family_evidence",
        status="current",
        description="Communication family evidence payload schema (publish deferred)",
    ),
    "behaviour_evidence_v1": EvidenceSchemaEntryV1(
        schema_id="behaviour_evidence_v1",
        schema_version="behaviour_evidence_v1",
        kind="family_evidence",
        status="current",
        description="Behaviour family evidence payload schema (publish deferred)",
    ),
}


def get_evidence_schema(schema_id: str) -> Optional[EvidenceSchemaEntryV1]:
    return EVIDENCE_SCHEMA_REGISTRY_V1.get((schema_id or "").strip())


def require_evidence_schema(schema_id: str) -> EvidenceSchemaEntryV1:
    entry = get_evidence_schema(schema_id)
    if entry is None:
        raise KeyError(f"unknown_evidence_schema:{schema_id!r}")
    return entry


def list_evidence_schemas(*, kind: str | None = None) -> list[EvidenceSchemaEntryV1]:
    rows = list(EVIDENCE_SCHEMA_REGISTRY_V1.values())
    if kind:
        k = kind.strip().lower()
        rows = [r for r in rows if r.kind == k]
    return sorted(rows, key=lambda r: r.schema_id)
