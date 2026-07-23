# -*- coding: utf-8 -*-
"""
WP-ET-03 Observation Normalizer shadow dual-write.

When CARTFLOW_EVIDENCE_OBSERVATION_DUAL_WRITE is ON:
  Raw sighting → accounting raw_in → normalize → store observation → accounting observation_out
  Identity/schema failures → reject audited; no observation written.

When OFF: no-op (production behaviour unchanged).

Does not activate Family Authorities, Bundle, Knowledge, or Findings.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from services.evidence_truth.accounting_v1 import (
    STAGE_OBSERVATION_OUT,
    STAGE_RAW_IN,
    get_evidence_accounting_ledger_v1,
)
from services.evidence_truth.flags_v1 import (
    FLAG_OBSERVATION_DUAL_WRITE,
    evidence_truth_flag_enabled,
)
from services.evidence_truth.kernel_v1 import EvidenceValidationError
from services.evidence_truth.observation_model_v1 import CanonicalObservationV1
from services.evidence_truth.observation_normalizer_v1 import normalize_raw_to_observation_v1
from services.evidence_truth.observation_store_v1 import get_canonical_observation_store_v1
from services.evidence_truth.observation_types_v1 import (
    CHANNEL_API,
    CHANNEL_SDK,
    CHANNEL_UNKNOWN,
    CHANNEL_WHATSAPP,
    CHANNEL_WIDGET,
    OBS_ACCOUNTING_RECORDED,
    RAW_KIND_BEHAVIOUR,
    RAW_KIND_CART_EVENT,
    RAW_KIND_COMMUNICATION,
    RAW_KIND_PRODUCT_SIGNAL,
    RAW_KIND_PURCHASE,
    RAW_KIND_RECOVERY,
    RAW_KIND_TRAFFIC,
)


def _with_accounting_recorded(observation: CanonicalObservationV1) -> CanonicalObservationV1:
    """Mark observation accounting_status=recorded after successful dual-write."""
    if observation.accounting_status == OBS_ACCOUNTING_RECORDED:
        return observation
    return CanonicalObservationV1(
        observation_id=observation.observation_id,
        observation_type=observation.observation_type,
        store_slug=observation.store_slug,
        subject=observation.subject,
        observed_at=observation.observed_at,
        source_channel=observation.source_channel,
        raw_kind=observation.raw_kind,
        raw_ref=observation.raw_ref,
        owner=observation.owner,
        canonical_family=observation.canonical_family,
        timestamp_authority=observation.timestamp_authority,
        version=observation.version,
        confidence_state=observation.confidence_state,
        readiness_state=observation.readiness_state,
        accounting_status=OBS_ACCOUNTING_RECORDED,
        observability_status=observation.observability_status,
        provider=observation.provider,
        canonical_store_id=observation.canonical_store_id,
        payload=observation.payload,
        provenance=observation.provenance,
        schema_version=observation.schema_version,
    )

log = logging.getLogger("cartflow.evidence_truth")


def observation_dual_write_enabled(*, environ: Mapping[str, str] | None = None) -> bool:
    return evidence_truth_flag_enabled(FLAG_OBSERVATION_DUAL_WRITE, environ=environ)


def shadow_dual_write_observation_v1(
    *,
    raw_kind: str,
    payload: Mapping[str, Any] | None,
    source_channel: str = CHANNEL_UNKNOWN,
    provider: str = "",
    source: str = "",
    environ: Mapping[str, str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Shadow dual-write one Raw sighting into Canonical Observation + accounting.

    ``force=True`` bypasses the feature flag (tests / Gate A harness only).
    """
    enabled = force or observation_dual_write_enabled(environ=environ)
    if not enabled:
        return {
            "ok": True,
            "skipped": True,
            "reason": "flag_off",
            "flag": FLAG_OBSERVATION_DUAL_WRITE,
        }

    ledger = get_evidence_accounting_ledger_v1()
    ledger.increment_stage(
        STAGE_RAW_IN,
        n=1,
        detail=f"shadow:{raw_kind}:{source or source_channel}",
    )

    try:
        observation = normalize_raw_to_observation_v1(
            raw_kind=raw_kind,
            payload=payload,
            source_channel=source_channel,
            provider=provider,
        )
    except EvidenceValidationError as exc:
        ledger.record_reject(exc.reason_code, detail=str(exc)[:200])
        return {
            "ok": False,
            "skipped": False,
            "rejected": True,
            "reason_code": exc.reason_code,
            "detail": str(exc),
            "raw_kind": raw_kind,
        }
    except Exception as exc:  # noqa: BLE001
        ledger.record_reject("schema_invalid", detail=f"normalize_failed:{exc}"[:200])
        log.warning("observation shadow normalize failed kind=%s: %s", raw_kind, exc)
        return {
            "ok": False,
            "skipped": False,
            "rejected": True,
            "reason_code": "schema_invalid",
            "detail": str(exc),
            "raw_kind": raw_kind,
        }

    store = get_canonical_observation_store_v1()
    prior = store.get_by_raw_ref(observation.raw_ref)
    to_store = _with_accounting_recorded(observation)
    stored = store.put(to_store)
    if prior is None:
        ledger.increment_stage(
            STAGE_OBSERVATION_OUT,
            n=1,
            detail=f"obs:{stored.observation_type}",
        )
        duplicated = False
    else:
        # Idempotent re-delivery: raw counted, observation not double-counted
        duplicated = True

    return {
        "ok": True,
        "skipped": False,
        "rejected": False,
        "duplicated": duplicated,
        "observation_id": stored.observation_id,
        "observation_type": stored.observation_type,
        "store_slug": stored.store_slug,
        "subject": stored.subject,
        "raw_kind": raw_kind,
        "raw_ref": stored.raw_ref,
    }


def maybe_shadow_dual_write_observation_v1(
    *,
    raw_kind: str,
    payload: Mapping[str, Any] | None,
    source_channel: str = CHANNEL_UNKNOWN,
    provider: str = "",
    source: str = "",
) -> Optional[dict[str, Any]]:
    """
    Production-safe entrypoint (journey-identity style).

    Never raises into callers. No-op when flag OFF.
    """
    try:
        return shadow_dual_write_observation_v1(
            raw_kind=raw_kind,
            payload=payload,
            source_channel=source_channel,
            provider=provider,
            source=source,
        )
    except Exception as exc:  # noqa: BLE001
        try:
            log.warning("observation shadow dual-write suppressed: %s", exc)
        except Exception:  # noqa: BLE001
            pass
        return {"ok": False, "skipped": True, "reason": "suppressed_error"}


# --- Typed helpers for priority Raw kinds (Stage 2) ---


def maybe_shadow_cart_event_observation_v1(
    payload: Mapping[str, Any] | None, *, source: str = "cart_event"
) -> Optional[dict[str, Any]]:
    return maybe_shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_CART_EVENT,
        payload=payload,
        source_channel=CHANNEL_WIDGET,
        source=source,
    )


def maybe_shadow_purchase_observation_v1(
    payload: Mapping[str, Any] | None, *, source: str = "purchase"
) -> Optional[dict[str, Any]]:
    return maybe_shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload=payload,
        source_channel=CHANNEL_API,
        source=source,
    )


def maybe_shadow_communication_observation_v1(
    payload: Mapping[str, Any] | None,
    *,
    source: str = "whatsapp",
    provider: str = "",
) -> Optional[dict[str, Any]]:
    return maybe_shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_COMMUNICATION,
        payload=payload,
        source_channel=CHANNEL_WHATSAPP,
        provider=provider,
        source=source,
    )


def maybe_shadow_product_signal_observation_v1(
    payload: Mapping[str, Any] | None, *, source: str = "product_signal"
) -> Optional[dict[str, Any]]:
    return maybe_shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_PRODUCT_SIGNAL,
        payload=payload,
        source_channel=CHANNEL_WIDGET,
        source=source,
    )


def maybe_shadow_traffic_observation_v1(
    payload: Mapping[str, Any] | None, *, source: str = "traffic"
) -> Optional[dict[str, Any]]:
    """Traffic producer helper — call when traffic Raw ingress exists."""
    return maybe_shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_TRAFFIC,
        payload=payload,
        source_channel=CHANNEL_SDK,
        source=source,
    )


def maybe_shadow_recovery_observation_v1(
    payload: Mapping[str, Any] | None, *, source: str = "recovery_timeline"
) -> Optional[dict[str, Any]]:
    """Recovery timeline → Observation shadow (WP-ET-06 / C-12 input)."""
    return maybe_shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_RECOVERY,
        payload=payload,
        source_channel=CHANNEL_API,
        source=source,
    )


def maybe_shadow_behaviour_observation_v1(
    payload: Mapping[str, Any] | None, *, source: str = "hesitation"
) -> Optional[dict[str, Any]]:
    """Behaviour / hesitation → Observation shadow (WP-ET-07 / C-15 input)."""
    return maybe_shadow_dual_write_observation_v1(
        raw_kind=RAW_KIND_BEHAVIOUR,
        payload=payload,
        source_channel=CHANNEL_WIDGET,
        source=source,
    )
