# -*- coding: utf-8 -*-
"""
C-07 Observation Normalizer — map Raw → Canonical Observation (WP-ET-03).

Fail closed on identity mismatch. Never invents subjects.
Does not publish Evidence. Does not change Raw persistence.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.evidence_truth.kernel_v1 import (
    REJECT_IDENTITY_MISMATCH,
    REJECT_SCHEMA_INVALID,
    EvidenceValidationError,
)
from services.evidence_truth.observation_model_v1 import (
    CanonicalObservationV1,
    observation_governance_defaults_v1,
    validate_observation_constitutional_metadata_v1,
)
from services.evidence_truth.observation_types_v1 import (
    CHANNEL_UNKNOWN,
    PRIORITY_RAW_KINDS_V1,
    RAW_KIND_TO_FAMILY_V1,
    RAW_KIND_TO_OBSERVATION_TYPE_V1,
    RAW_KIND_BEHAVIOUR,
    RAW_KIND_CART_EVENT,
    RAW_KIND_COMMUNICATION,
    RAW_KIND_PRODUCT_SIGNAL,
    RAW_KIND_PURCHASE,
    RAW_KIND_RECOVERY,
    RAW_KIND_TRAFFIC,
)
from services.evidence_truth.ownership_v1 import owner_for_family


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _norm(value: Any) -> str:
    return str(value or "").strip()


def extract_store_slug_v1(payload: Mapping[str, Any] | None) -> str:
    if not isinstance(payload, Mapping):
        return ""
    return _norm(payload.get("store_slug") or payload.get("store") or payload.get("slug"))


def extract_subject_v1(raw_kind: str, payload: Mapping[str, Any] | None) -> str:
    """Derive subject without inventing — empty if insufficient identity."""
    if not isinstance(payload, Mapping):
        return ""
    kind = (raw_kind or "").strip().lower()
    session = _norm(payload.get("session_id") or payload.get("recovery_session_id"))
    cart = _norm(payload.get("cart_id") or payload.get("zid_cart_id"))
    recovery_key = _norm(payload.get("recovery_key"))
    product = _norm(payload.get("product_id") or payload.get("productId"))
    if not product:
        lines = payload.get("lines") or payload.get("cart") or []
        if isinstance(lines, list) and lines:
            first = lines[0]
            if isinstance(first, Mapping):
                product = _norm(first.get("product_id") or first.get("id") or first.get("sku"))
    message = _norm(
        payload.get("message_sid")
        or payload.get("MessageSid")
        or payload.get("provider_message_id")
        or payload.get("message_id")
    )
    visitor = _norm(payload.get("visitor_id") or payload.get("anonymous_id"))

    if kind == RAW_KIND_PURCHASE:
        return recovery_key or (f"session:{session}" if session else "") or (
            f"cart:{cart}" if cart else ""
        )
    if kind == RAW_KIND_RECOVERY:
        return recovery_key or (f"session:{session}" if session else "")
    if kind == RAW_KIND_CART_EVENT:
        return (f"session:{session}" if session else "") or (f"cart:{cart}" if cart else "")
    if kind == RAW_KIND_COMMUNICATION:
        return (f"message:{message}" if message else "") or recovery_key or (
            f"session:{session}" if session else ""
        )
    if kind == RAW_KIND_PRODUCT_SIGNAL:
        if product and session:
            return f"product:{product}|session:{session}"
        return (f"product:{product}" if product else "") or (
            f"session:{session}" if session else ""
        )
    if kind == RAW_KIND_BEHAVIOUR:
        return (f"session:{session}" if session else "") or recovery_key or (
            f"cart:{cart}" if cart else ""
        )
    if kind == RAW_KIND_TRAFFIC:
        return (f"visitor:{visitor}" if visitor else "") or (
            f"session:{session}" if session else ""
        )
    return recovery_key or session or cart or product or message or visitor


def build_raw_ref_v1(
    *,
    raw_kind: str,
    store_slug: str,
    subject: str,
    observed_at: str,
    payload: Mapping[str, Any] | None = None,
) -> str:
    """Stable raw_ref for idempotent dual-write."""
    extra = ""
    if isinstance(payload, Mapping):
        for key in (
            "event",
            "MessageStatus",
            "status",
            "timeline_status",
            "product_id",
            "raw_event_id",
            "reason",
            "signal_class",
            "capture_source",
        ):
            val = _norm(payload.get(key))
            if val:
                extra = val
                break
    basis = "|".join(
        [
            (raw_kind or "").strip().lower(),
            (store_slug or "").strip().lower(),
            (subject or "").strip(),
            (observed_at or "").strip(),
            extra,
        ]
    )
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]
    return f"raw:{digest}"


def build_observation_id_v1(*, observation_type: str, raw_ref: str) -> str:
    digest = hashlib.sha256(f"{observation_type}|{raw_ref}".encode("utf-8")).hexdigest()[:24]
    return f"obs:{digest}"


def normalize_raw_to_observation_v1(
    *,
    raw_kind: str,
    payload: Mapping[str, Any] | None,
    source_channel: str = CHANNEL_UNKNOWN,
    provider: str = "",
    observed_at: str | None = None,
    raw_ref: str | None = None,
) -> CanonicalObservationV1:
    """
    Map a Raw payload into a CanonicalObservationV1.

    Raises EvidenceValidationError(identity_mismatch|schema_invalid) on failure.
    """
    kind = (raw_kind or "").strip().lower()
    if kind not in PRIORITY_RAW_KINDS_V1:
        raise EvidenceValidationError(
            REJECT_SCHEMA_INVALID, f"unsupported_raw_kind:{raw_kind!r}"
        )
    obs_type = RAW_KIND_TO_OBSERVATION_TYPE_V1[kind]
    store_slug = extract_store_slug_v1(payload)
    if not store_slug:
        raise EvidenceValidationError(
            REJECT_IDENTITY_MISMATCH, "store_slug_required"
        )
    subject = extract_subject_v1(kind, payload)
    if not subject:
        raise EvidenceValidationError(
            REJECT_IDENTITY_MISMATCH, "subject_required"
        )
    ts = (observed_at or "").strip() or _utc_now_iso()
    # Prefer payload timestamp when present and non-empty
    if isinstance(payload, Mapping):
        for key in ("observed_at", "event_at", "created_at", "timestamp"):
            cand = _norm(payload.get(key))
            if cand:
                ts = cand
                break
    ref = (raw_ref or "").strip() or build_raw_ref_v1(
        raw_kind=kind,
        store_slug=store_slug,
        subject=subject,
        observed_at=ts,
        payload=payload,
    )
    oid = build_observation_id_v1(observation_type=obs_type, raw_ref=ref)
    # Keep a bounded, non-authoritative payload slice for traceability
    safe_payload: dict[str, Any] = {}
    if isinstance(payload, Mapping):
        for key in (
            "event",
            "session_id",
            "cart_id",
            "product_id",
            "recovery_key",
            "MessageStatus",
            "status",
            "timeline_status",
            "source",
            "reason",
            "sub_reason",
            "signal_class",
            "capture_source",
            "visitor_id",
            "anonymous_id",
            "channel_available",
            "channel_status",
        ):
            if key in payload and payload.get(key) is not None:
                safe_payload[key] = payload.get(key)
    family = RAW_KIND_TO_FAMILY_V1.get(kind) or ""
    owner = owner_for_family(family) or ""
    if not family or not owner:
        raise EvidenceValidationError(
            REJECT_IDENTITY_MISMATCH, f"family_or_owner_missing:{kind!r}"
        )
    gov = observation_governance_defaults_v1()
    observation = CanonicalObservationV1(
        observation_id=oid,
        observation_type=obs_type,
        store_slug=store_slug,
        subject=subject,
        observed_at=ts,
        source_channel=(source_channel or CHANNEL_UNKNOWN).strip() or CHANNEL_UNKNOWN,
        raw_kind=kind,
        raw_ref=ref,
        owner=owner,
        canonical_family=family,
        timestamp_authority=str(gov["timestamp_authority"]),
        version=int(gov["version"]),
        confidence_state=str(gov["confidence_state"]),
        readiness_state=str(gov["readiness_state"]),
        accounting_status=str(gov["accounting_status"]),
        observability_status=str(gov["observability_status"]),
        provider=(provider or "").strip(),
        payload=safe_payload,
        provenance="shadow_dual_write",
    )
    validate_observation_constitutional_metadata_v1(observation)
    return observation
