# -*- coding: utf-8 -*-
"""
C-02 Evidence Type Registry (technical) — WP-ET-01 complete.

Catalog of evidence_family + evidence_type + schema + dedupe + TTL + owner.
Not the merchant presentation registry.

Types must be registered before first publish (Blueprint C-02).
WP-ET-01 does not publish evidence and wires no production path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.evidence_truth.families_v1 import (
    FAMILY_BEHAVIOUR,
    FAMILY_CART,
    FAMILY_COMMUNICATION,
    FAMILY_PRODUCT,
    FAMILY_PURCHASE,
    FAMILY_RECOVERY,
    FAMILY_VISITOR,
    require_evidence_family,
)
from services.evidence_truth.kernel_v1 import (
    REJECT_OWNER_MISSING,
    REJECT_UNKNOWN_TYPE,
    EvidenceValidationError,
)
from services.evidence_truth.ownership_v1 import owner_for_family
from services.evidence_truth.schema_registry_v1 import require_evidence_schema

STATUS_DECLARED = "declared"  # registered; not yet published by an authority
STATUS_ACTIVE = "active"  # later WPs when publishers exist


@dataclass(frozen=True)
class EvidenceTypeEntryV1:
    evidence_family: str
    evidence_type: str
    schema_version: str
    dedupe_key_template: str
    default_ttl_seconds: Optional[int]
    owner_module: str
    status: str = STATUS_DECLARED
    description: str = ""


def _entry(
    family: str,
    evidence_type: str,
    *,
    schema_version: str,
    dedupe_key_template: str,
    default_ttl_seconds: Optional[int],
    description: str,
    status: str = STATUS_DECLARED,
) -> EvidenceTypeEntryV1:
    require_evidence_family(family)
    owner = owner_for_family(family) or ""
    return EvidenceTypeEntryV1(
        evidence_family=family,
        evidence_type=evidence_type,
        schema_version=schema_version,
        dedupe_key_template=dedupe_key_template,
        default_ttl_seconds=default_ttl_seconds,
        owner_module=owner,
        status=status,
        description=description,
    )


# Scaffold types — one primary declared type per family (expand in later WPs)
_EVIDENCE_TYPES_V1: dict[str, EvidenceTypeEntryV1] = {}


def _type_key(family: str, evidence_type: str) -> str:
    return f"{(family or '').strip().lower()}:{(evidence_type or '').strip()}"


def _register(entry: EvidenceTypeEntryV1) -> None:
    key = _type_key(entry.evidence_family, entry.evidence_type)
    if key in _EVIDENCE_TYPES_V1:
        raise ValueError(f"duplicate_evidence_type:{key}")
    if not entry.owner_module:
        raise ValueError(f"owner_missing:{key}")
    # Fail closed: schema must be documented in schema registry
    require_evidence_schema(entry.schema_version)
    _EVIDENCE_TYPES_V1[key] = entry


def register_evidence_type_v1(
    *,
    evidence_family: str,
    evidence_type: str,
    schema_version: str,
    dedupe_key_template: str,
    default_ttl_seconds: Optional[int] = None,
    description: str = "",
    status: str = STATUS_DECLARED,
    owner_module: str | None = None,
) -> EvidenceTypeEntryV1:
    """
    Authority registration API (Blueprint C-02 inputs).

    Idempotent for identical entries; rejects duplicate keys with different
    definitions. Does not publish evidence.
    """
    require_evidence_family(evidence_family)
    expected_owner = owner_for_family(evidence_family) or ""
    owner = (owner_module or expected_owner).strip()
    if not owner:
        raise EvidenceValidationError(
            REJECT_OWNER_MISSING, f"owner_missing:{evidence_family!r}"
        )
    if expected_owner and owner != expected_owner:
        raise EvidenceValidationError(
            REJECT_OWNER_MISSING,
            f"owner_mismatch:got={owner!r} expected={expected_owner!r}",
        )
    if status not in {STATUS_DECLARED, STATUS_ACTIVE}:
        raise ValueError(f"invalid_type_status:{status!r}")

    key = _type_key(evidence_family, evidence_type)
    existing = _EVIDENCE_TYPES_V1.get(key)
    entry = EvidenceTypeEntryV1(
        evidence_family=(evidence_family or "").strip().lower(),
        evidence_type=(evidence_type or "").strip(),
        schema_version=(schema_version or "").strip(),
        dedupe_key_template=(dedupe_key_template or "").strip(),
        default_ttl_seconds=default_ttl_seconds,
        owner_module=owner,
        status=status,
        description=description or "",
    )
    if not entry.evidence_type:
        raise ValueError("evidence_type_required")
    if not entry.dedupe_key_template:
        raise ValueError("dedupe_key_template_required")
    require_evidence_schema(entry.schema_version)

    if existing is not None:
        if existing == entry:
            return existing
        raise ValueError(f"duplicate_evidence_type:{key}")

    _EVIDENCE_TYPES_V1[key] = entry
    return entry


def require_evidence_type_for_publish_v1(family: str, evidence_type: str) -> EvidenceTypeEntryV1:
    """
    Fail-closed publish guard (Blueprint C-02 consumer contract).

    Library only — no production publisher calls this in WP-ET-01.
    """
    entry = get_evidence_type(family, evidence_type)
    if entry is None:
        raise EvidenceValidationError(
            REJECT_UNKNOWN_TYPE,
            f"unknown_type:{family!r}:{evidence_type!r}",
        )
    if not entry.owner_module:
        raise EvidenceValidationError(
            REJECT_OWNER_MISSING,
            f"owner_missing:{family!r}:{evidence_type!r}",
        )
    require_evidence_schema(entry.schema_version)
    return entry


def _bootstrap() -> None:
    if _EVIDENCE_TYPES_V1:
        return
    specs = (
        _entry(
            FAMILY_VISITOR,
            "store_visitor_window_v1",
            schema_version="visitor_evidence_v1",
            dedupe_key_template="{store}:{type}:{window}",
            default_ttl_seconds=86400,
            description="Windowed store visitor presence (authority not publishing yet)",
        ),
        _entry(
            FAMILY_PRODUCT,
            "product_interest_window_v1",
            schema_version="product_evidence_v1",
            dedupe_key_template="{store}:{type}:{product}:{window}",
            default_ttl_seconds=86400,
            description="Product interest / view window (authority not publishing yet)",
        ),
        _entry(
            FAMILY_CART,
            "cart_state_v1",
            schema_version="cart_evidence_v1",
            dedupe_key_template="{store}:{type}:{subject}",
            default_ttl_seconds=3600,
            description="Cart composition / abandon state (authority not publishing yet)",
        ),
        _entry(
            FAMILY_RECOVERY,
            "recovery_progression_v1",
            schema_version="recovery_evidence_v1",
            dedupe_key_template="{store}:{type}:{recovery_key}",
            default_ttl_seconds=None,
            description="Recovery lifecycle progression (authority not publishing yet)",
        ),
        _entry(
            FAMILY_PURCHASE,
            "purchase_confirmed_v1",
            schema_version="purchase_evidence_v1",
            dedupe_key_template="{store}:{type}:{subject}",
            default_ttl_seconds=None,
            description="Proven purchase / conversion (authority not publishing yet)",
        ),
        _entry(
            FAMILY_COMMUNICATION,
            "message_lifecycle_v1",
            schema_version="communication_evidence_v1",
            dedupe_key_template="{store}:{type}:{message_ref}",
            default_ttl_seconds=None,
            description="Message accepted/delivered/failed/replied (not publishing yet)",
        ),
        _entry(
            FAMILY_BEHAVIOUR,
            "hesitation_reason_v1",
            schema_version="behaviour_evidence_v1",
            dedupe_key_template="{store}:{type}:{subject}",
            default_ttl_seconds=None,
            description="Hesitation / reason capture (authority not publishing yet)",
        ),
    )
    for spec in specs:
        _register(spec)


_bootstrap()


def list_evidence_types(*, family: str | None = None) -> list[EvidenceTypeEntryV1]:
    fam = (family or "").strip().lower() or None
    rows = list(_EVIDENCE_TYPES_V1.values())
    if fam:
        rows = [r for r in rows if r.evidence_family == fam]
    return sorted(rows, key=lambda r: (r.evidence_family, r.evidence_type))


def get_evidence_type(family: str, evidence_type: str) -> Optional[EvidenceTypeEntryV1]:
    key = f"{(family or '').strip().lower()}:{(evidence_type or '').strip()}"
    return _EVIDENCE_TYPES_V1.get(key)


def require_evidence_type(family: str, evidence_type: str) -> EvidenceTypeEntryV1:
    entry = get_evidence_type(family, evidence_type)
    if entry is None:
        raise KeyError(f"unknown_evidence_type:{family!r}:{evidence_type!r}")
    return entry
