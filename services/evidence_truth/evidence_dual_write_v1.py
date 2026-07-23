# -*- coding: utf-8 -*-
"""
Evidence dual-write orchestration — Stages 3–4 family publishers.

WP-ET-05: C-13/C-14 · WP-ET-06: C-11/C-12 · WP-ET-07: C-10/C-15

When CARTFLOW_EVIDENCE_DUAL_WRITE is ON:
  Ensure Observation → publish family Evidence → account.

When OFF: no-op (production behaviour unchanged).

Does not activate Bundle, Knowledge, Findings, Guidance, Dashboard, BFSV, or RV.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from services.evidence_truth.accounting_v1 import get_evidence_accounting_ledger_v1
from services.evidence_truth.behaviour_evidence_publisher_v1 import (
    publish_behaviour_evidence_v1,
)
from services.evidence_truth.cart_evidence_publisher_v1 import publish_cart_evidence_v1
from services.evidence_truth.communication_evidence_publisher_v1 import (
    publish_communication_evidence_v1,
)
from services.evidence_truth.flags_v1 import (
    FLAG_EVIDENCE_DUAL_WRITE,
    evidence_truth_flag_enabled,
)
from services.evidence_truth.kernel_v1 import EvidenceValidationError
from services.evidence_truth.observation_normalizer_v1 import normalize_raw_to_observation_v1
from services.evidence_truth.observation_shadow_dual_write_v1 import (
    shadow_dual_write_observation_v1,
)
from services.evidence_truth.observation_store_v1 import get_canonical_observation_store_v1
from services.evidence_truth.observation_types_v1 import (
    CHANNEL_API,
    CHANNEL_SDK,
    CHANNEL_WHATSAPP,
    CHANNEL_WIDGET,
    RAW_KIND_BEHAVIOUR,
    RAW_KIND_CART_EVENT,
    RAW_KIND_COMMUNICATION,
    RAW_KIND_PRODUCT_SIGNAL,
    RAW_KIND_PURCHASE,
    RAW_KIND_RECOVERY,
    RAW_KIND_TRAFFIC,
)
from services.evidence_truth.product_evidence_publisher_v1 import (
    publish_product_evidence_v1,
)
from services.evidence_truth.purchase_evidence_publisher_v1 import (
    publish_purchase_evidence_v1,
)
from services.evidence_truth.recovery_evidence_publisher_v1 import (
    publish_recovery_evidence_v1,
)
from services.evidence_truth.visitor_evidence_publisher_v1 import (
    publish_visitor_evidence_v1,
)
from services.evidence_truth.visitor_proxy_detection_v1 import detect_visitor_proxy_v1

log = logging.getLogger("cartflow.evidence_truth")

_SUPPORTED_EVIDENCE_RAW_KINDS = frozenset(
    {
        RAW_KIND_PURCHASE,
        RAW_KIND_COMMUNICATION,
        RAW_KIND_CART_EVENT,
        RAW_KIND_RECOVERY,
        RAW_KIND_PRODUCT_SIGNAL,
        RAW_KIND_BEHAVIOUR,
        RAW_KIND_TRAFFIC,
    }
)

# Soft-match reuse allowed only for these kinds (wall-clock skew on same call site).
# Communication/recovery/behaviour/traffic status changes must create distinct observations.
_SOFT_MATCH_RAW_KINDS = frozenset(
    {RAW_KIND_PURCHASE, RAW_KIND_CART_EVENT, RAW_KIND_PRODUCT_SIGNAL}
)


def evidence_dual_write_enabled(*, environ: Mapping[str, str] | None = None) -> bool:
    return evidence_truth_flag_enabled(FLAG_EVIDENCE_DUAL_WRITE, environ=environ)


def _default_channel(raw_kind: str) -> str:
    if raw_kind == RAW_KIND_COMMUNICATION:
        return CHANNEL_WHATSAPP
    if raw_kind in {RAW_KIND_CART_EVENT, RAW_KIND_BEHAVIOUR, RAW_KIND_PRODUCT_SIGNAL}:
        return CHANNEL_WIDGET
    if raw_kind == RAW_KIND_TRAFFIC:
        return CHANNEL_SDK
    return CHANNEL_API


def _ensure_observation(
    *,
    raw_kind: str,
    payload: Mapping[str, Any] | None,
    source_channel: str,
    provider: str,
    source: str,
    observation_id: str = "",
) -> dict[str, Any]:
    """
    Ensure a Canonical Observation exists for this Raw sighting.

    Prefer an existing shadow observation (no double raw_in). Otherwise
    materialize via observation dual-write with force=True.
    """
    store = get_canonical_observation_store_v1()
    oid = (observation_id or "").strip()
    if oid:
        hit = store.get(oid)
        if hit is not None:
            return {
                "ok": True,
                "rejected": False,
                "duplicated": True,
                "observation_id": hit.observation_id,
                "raw_ref": hit.raw_ref,
                "reused": True,
            }

    try:
        candidate = normalize_raw_to_observation_v1(
            raw_kind=raw_kind,
            payload=payload,
            source_channel=source_channel,
            provider=provider,
        )
    except EvidenceValidationError as exc:
        return {
            "ok": False,
            "rejected": True,
            "reason_code": exc.reason_code,
            "detail": str(exc),
        }

    existing = store.get_by_raw_ref(candidate.raw_ref) or store.get(candidate.observation_id)
    if existing is None and candidate.raw_kind in _SOFT_MATCH_RAW_KINDS:
        cand_event = str((candidate.payload or {}).get("event") or "").strip().lower()
        for row in reversed(store.list_recent(limit=200, store_slug=candidate.store_slug)):
            if (
                row.subject != candidate.subject
                or row.canonical_family != candidate.canonical_family
                or row.raw_kind != candidate.raw_kind
            ):
                continue
            if candidate.raw_kind in {RAW_KIND_CART_EVENT, RAW_KIND_PRODUCT_SIGNAL}:
                row_event = str((row.payload or {}).get("event") or "").strip().lower()
                if cand_event and row_event and cand_event != row_event:
                    continue
            existing = row
            break
    if existing is not None:
        return {
            "ok": True,
            "rejected": False,
            "duplicated": True,
            "observation_id": existing.observation_id,
            "raw_ref": existing.raw_ref,
            "reused": True,
        }
    return shadow_dual_write_observation_v1(
        raw_kind=raw_kind,
        payload=payload,
        source_channel=source_channel,
        provider=provider,
        source=source,
        force=True,
    )


def _publish_for_kind(kind: str, observation: Any) -> tuple[Any, bool]:
    if kind == RAW_KIND_PURCHASE:
        return publish_purchase_evidence_v1(observation)
    if kind == RAW_KIND_COMMUNICATION:
        return publish_communication_evidence_v1(observation)
    if kind == RAW_KIND_CART_EVENT:
        return publish_cart_evidence_v1(observation)
    if kind == RAW_KIND_RECOVERY:
        return publish_recovery_evidence_v1(observation)
    if kind == RAW_KIND_PRODUCT_SIGNAL:
        return publish_product_evidence_v1(observation)
    if kind == RAW_KIND_BEHAVIOUR:
        return publish_behaviour_evidence_v1(observation)
    if kind == RAW_KIND_TRAFFIC:
        return publish_visitor_evidence_v1(observation)
    raise EvidenceValidationError("schema_invalid", f"unsupported_kind:{kind!r}")


def shadow_dual_write_evidence_v1(
    *,
    raw_kind: str,
    payload: Mapping[str, Any] | None,
    source_channel: str = "",
    provider: str = "",
    source: str = "",
    observation_id: str = "",
    environ: Mapping[str, str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Shadow dual-write Evidence for Stage-3/4 family Raw kinds.

    ``force=True`` bypasses the feature flag (tests / harness only).
    """
    enabled = force or evidence_dual_write_enabled(environ=environ)
    if not enabled:
        return {
            "ok": True,
            "skipped": True,
            "reason": "flag_off",
            "flag": FLAG_EVIDENCE_DUAL_WRITE,
        }

    kind = (raw_kind or "").strip().lower()
    if kind not in _SUPPORTED_EVIDENCE_RAW_KINDS:
        return {
            "ok": False,
            "skipped": False,
            "rejected": True,
            "reason_code": "schema_invalid",
            "detail": f"unsupported_evidence_family_raw:{raw_kind!r}",
        }

    channel = source_channel or _default_channel(kind)

    # Gate B: reject cart/recovery proxies before Visitor materialization
    if kind == RAW_KIND_TRAFFIC:
        proxy = detect_visitor_proxy_v1(payload, raw_kind=kind)
        if proxy:
            get_evidence_accounting_ledger_v1().record_reject(
                "conflict_unresolved", detail=f"visitor_proxy:{proxy}"[:200]
            )
            return {
                "ok": False,
                "skipped": False,
                "rejected": True,
                "reason_code": "conflict_unresolved",
                "detail": f"visitor_proxy_rejected:{proxy}",
            }

    obs_result = _ensure_observation(
        raw_kind=kind,
        payload=payload,
        source_channel=channel,
        provider=provider,
        source=source or f"evidence_dual_write:{kind}",
        observation_id=observation_id,
    )
    if obs_result.get("rejected"):
        return {
            "ok": False,
            "skipped": False,
            "rejected": True,
            "reason_code": obs_result.get("reason_code") or "schema_invalid",
            "detail": obs_result.get("detail") or "observation_rejected",
            "observation": obs_result,
        }

    oid = str(obs_result.get("observation_id") or "")
    store = get_canonical_observation_store_v1()
    observation = store.get(oid) if oid else None
    if observation is None and obs_result.get("raw_ref"):
        observation = store.get_by_raw_ref(str(obs_result.get("raw_ref")))
    if observation is None:
        get_evidence_accounting_ledger_v1().record_reject(
            "missing_sources", detail="observation_missing_after_ensure"
        )
        return {
            "ok": False,
            "skipped": False,
            "rejected": True,
            "reason_code": "missing_sources",
            "detail": "observation_missing_after_ensure",
        }

    try:
        record, created = _publish_for_kind(kind, observation)
    except EvidenceValidationError as exc:
        get_evidence_accounting_ledger_v1().record_reject(
            exc.reason_code, detail=str(exc)[:200]
        )
        return {
            "ok": False,
            "skipped": False,
            "rejected": True,
            "reason_code": exc.reason_code,
            "detail": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        get_evidence_accounting_ledger_v1().record_reject(
            "schema_invalid", detail=f"publish_failed:{exc}"[:200]
        )
        log.warning("evidence dual-write publish failed kind=%s: %s", kind, exc)
        return {
            "ok": False,
            "skipped": False,
            "rejected": True,
            "reason_code": "schema_invalid",
            "detail": str(exc),
        }

    return {
        "ok": True,
        "skipped": False,
        "rejected": False,
        "created": created,
        "duplicated": not created,
        "evidence_id": record.evidence_id,
        "evidence_version": record.evidence_version,
        "evidence_family": record.canonical_family,
        "evidence_type": record.evidence_type,
        "lifecycle_state": record.lifecycle_state,
        "readiness": record.readiness,
        "confidence": record.confidence,
        "consumable": record.consumable,
        "observation_id": observation.observation_id,
        "raw_kind": kind,
    }


def maybe_shadow_dual_write_evidence_v1(
    *,
    raw_kind: str,
    payload: Mapping[str, Any] | None,
    source_channel: str = "",
    provider: str = "",
    source: str = "",
    observation_id: str = "",
) -> Optional[dict[str, Any]]:
    """Production-safe entrypoint — never raises into callers."""
    try:
        return shadow_dual_write_evidence_v1(
            raw_kind=raw_kind,
            payload=payload,
            source_channel=source_channel,
            provider=provider,
            source=source,
            observation_id=observation_id,
        )
    except Exception as exc:  # noqa: BLE001
        try:
            log.warning("evidence shadow dual-write suppressed: %s", exc)
        except Exception:  # noqa: BLE001
            pass
        return {"ok": False, "skipped": True, "reason": "suppressed_error"}


def maybe_publish_purchase_evidence_v1(
    payload: Mapping[str, Any] | None,
    *,
    source: str = "purchase",
    observation_id: str = "",
) -> Optional[dict[str, Any]]:
    return maybe_shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PURCHASE,
        payload=payload,
        source_channel=CHANNEL_API,
        source=source,
        observation_id=observation_id,
    )


def maybe_publish_communication_evidence_v1(
    payload: Mapping[str, Any] | None,
    *,
    source: str = "whatsapp",
    provider: str = "",
    observation_id: str = "",
) -> Optional[dict[str, Any]]:
    return maybe_shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_COMMUNICATION,
        payload=payload,
        source_channel=CHANNEL_WHATSAPP,
        provider=provider,
        source=source,
        observation_id=observation_id,
    )


def maybe_publish_cart_evidence_v1(
    payload: Mapping[str, Any] | None,
    *,
    source: str = "cart_event",
    observation_id: str = "",
) -> Optional[dict[str, Any]]:
    return maybe_shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_CART_EVENT,
        payload=payload,
        source_channel=CHANNEL_WIDGET,
        source=source,
        observation_id=observation_id,
    )


def maybe_publish_recovery_evidence_v1(
    payload: Mapping[str, Any] | None,
    *,
    source: str = "recovery_timeline",
    observation_id: str = "",
) -> Optional[dict[str, Any]]:
    return maybe_shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_RECOVERY,
        payload=payload,
        source_channel=CHANNEL_API,
        source=source,
        observation_id=observation_id,
    )


def maybe_publish_product_evidence_v1(
    payload: Mapping[str, Any] | None,
    *,
    source: str = "product_signal",
    observation_id: str = "",
) -> Optional[dict[str, Any]]:
    return maybe_shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_PRODUCT_SIGNAL,
        payload=payload,
        source_channel=CHANNEL_WIDGET,
        source=source,
        observation_id=observation_id,
    )


def maybe_publish_behaviour_evidence_v1(
    payload: Mapping[str, Any] | None,
    *,
    source: str = "hesitation",
    observation_id: str = "",
) -> Optional[dict[str, Any]]:
    return maybe_shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_BEHAVIOUR,
        payload=payload,
        source_channel=CHANNEL_WIDGET,
        source=source,
        observation_id=observation_id,
    )


def maybe_publish_visitor_evidence_v1(
    payload: Mapping[str, Any] | None,
    *,
    source: str = "traffic",
    observation_id: str = "",
) -> Optional[dict[str, Any]]:
    """
    Visitor Evidence dual-write helper (WP-ET-08).

    Ready for attach when a durable traffic/presence Raw ingress owner exists.
    Idle by default (flag OFF). No production call site in WP-ET-08.
    """
    return maybe_shadow_dual_write_evidence_v1(
        raw_kind=RAW_KIND_TRAFFIC,
        payload=payload,
        source_channel=CHANNEL_SDK,
        source=source,
        observation_id=observation_id,
    )
