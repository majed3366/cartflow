# -*- coding: utf-8 -*-
"""
Surface Composition Foundation V1 — compose merchant surfaces from governed outputs.

Consumes Merchant Presentation + Knowledge + Operational Truth packages.
Does not decide routing. No UI, pixels, CSS, AI, or page implementation.
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import SurfaceComposition
from schema_surface_composition_v1 import ensure_surface_composition_schema
from services.product_data.knowledge_foundation_v1 import generate_knowledge_v1
from services.product_data.merchant_presentation_foundation_v1 import (
    generate_merchant_presentations_v1,
)
from services.product_data.merchant_presentation_types_v1 import (
    STATE_BLOCKED,
    STATE_DEFERRED,
    STATE_EXPIRED,
    STATE_FAILED,
    STATE_INSUFFICIENT,
    STATE_MONITORING,
    STATE_READY,
)
from services.product_data.surface_composition_flag_v1 import (
    surface_composition_v1_enabled,
)
from services.product_data.surface_composition_registry_v1 import (
    DUPLICATE_OWNER_BY_CLASS_V1,
    EMPTY_STATE_KEYS_V1,
    PRESENTATION_CLASS_MAP_V1,
    SURFACE_REGISTRY_V1,
    get_surface_registry_entry_v1,
    list_surfaces_v1,
    surface_registry_valid_v1,
)
from services.product_data.surface_composition_types_v1 import (
    ACCT_COLLAPSED,
    ACCT_COMPOSED,
    ACCT_DEFERRED,
    ACCT_EXPIRED,
    ACCT_FAILED,
    ACCT_REJECTED,
    ACCT_SUPPRESSED,
    CLASS_EMPTY_STATE,
    CLASS_KNOWLEDGE,
    COMPOSITION_VERSION_V1,
    FRESH_AGING,
    FRESH_EXPIRED,
    FRESH_FRESH,
    FRESH_STALE,
    GENERATION_VERSION_V1,
    INTENT_HERO,
    INTENT_INFORMATION,
    INTENT_INSIGHT_CARD,
    INTENT_REFERENCE,
    INTENT_SUMMARY_CARD,
    INTENT_WARNING,
    CLASS_CRITICAL_ATTENTION,
    CLASS_OPERATIONAL_HEALTH,
    CLASS_RECOVERY_HEALTH,
    INTENT_OPERATIONAL_STATE,
    INTENT_PRIORITY_CARD,
    KNOWLEDGE_SOURCE_CONTRACT_VERSION_V1,
    OPERATIONAL_TRUTH_SOURCE_CONTRACT_VERSION_V1,
    SOURCE_CONTRACT_VERSION_V1,
    SOURCE_EMPTY_STATE,
    SOURCE_KNOWLEDGE,
    SOURCE_MERCHANT_PRESENTATION,
    SOURCE_OPERATIONAL_TRUTH,
    SURFACE_HOME,
    SURFACE_REGISTRY_VERSION_V1,
    VIS_COLLAPSED,
    VIS_EXPIRED,
    VIS_SUPPRESSED,
    VIS_VISIBLE,
)

log = logging.getLogger("cartflow")


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _floor_second(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.replace(microsecond=0)


def _as_of_key(dt: datetime) -> str:
    return _floor_second(dt).strftime("%Y%m%d%H%M%S")


def _sha(payload: dict[str, Any] | str) -> str:
    if isinstance(payload, str):
        raw = payload
    else:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _parse_iso(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _floor_second(value)
    try:
        return _floor_second(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


def freshness_state_v1(*, valid_until: datetime, as_of: datetime) -> str:
    """Deterministic freshness from validity window."""
    delta = (valid_until - as_of).total_seconds()
    if delta <= 0:
        return FRESH_EXPIRED
    if delta > 3 * 86400:
        return FRESH_FRESH
    if delta > 86400:
        return FRESH_AGING
    return FRESH_STALE


def priority_score_v1(
    *,
    information_class: str,
    route_role: str,
    presentation_state: str,
    freshness: str,
    evidence_state: str,
    presentation_type: str,
) -> int:
    """Deterministic ordering inputs — pages must never invent ordering."""
    role_scores = {
        "critical": 40,
        "action": 30,
        "review": 28,
        "awareness": 20,
        "monitor": 15,
        "suppressed": 0,
    }
    state_scores = {
        STATE_READY: 20,
        STATE_MONITORING: 12,
        STATE_DEFERRED: 6,
        STATE_INSUFFICIENT: 8,
        STATE_BLOCKED: 4,
        STATE_FAILED: 0,
        STATE_EXPIRED: 0,
    }
    fresh_scores = {
        FRESH_FRESH: 15,
        FRESH_AGING: 10,
        FRESH_STALE: 5,
        FRESH_EXPIRED: 0,
    }
    evidence_scores = {
        "sufficient_evidence": 10,
        "limited_evidence": 6,
        "continued_observation": 5,
        "insufficient_evidence": 2,
    }
    class_boost = {
        "critical_attention": 8,
        "executive_summary": 6,
        "commercial_guidance": 5,
        "operational_health": 5,
        "evidence_gap": 3,
        "knowledge": 2,
        "empty_state": 0,
    }
    severity = 10 if presentation_type == "operational_notice" else 0
    score = (
        role_scores.get(str(route_role or ""), 10)
        + state_scores.get(str(presentation_state or ""), 0)
        + fresh_scores.get(str(freshness or ""), 0)
        + evidence_scores.get(str(evidence_state or ""), 3)
        + class_boost.get(str(information_class or ""), 0)
        + severity
    )
    return int(score)


def _map_presentation(pres: dict[str, Any]) -> tuple[str, str]:
    ptype = str(pres.get("presentation_type") or "")
    mapped = PRESENTATION_CLASS_MAP_V1.get(ptype)
    if mapped:
        return mapped
    return ("observation", INTENT_INFORMATION)


def _accounting_for_visibility(visibility: str, presentation_state: str) -> str:
    if visibility == VIS_EXPIRED:
        return ACCT_EXPIRED
    if visibility == VIS_SUPPRESSED:
        return ACCT_SUPPRESSED
    if visibility == VIS_COLLAPSED:
        return ACCT_COLLAPSED
    if presentation_state == STATE_DEFERRED:
        return ACCT_DEFERRED
    if presentation_state == STATE_FAILED:
        return ACCT_FAILED
    if presentation_state in {STATE_BLOCKED, STATE_INSUFFICIENT}:
        return ACCT_COMPOSED
    return ACCT_COMPOSED


def _failed_composition(
    *,
    store_slug: str,
    surface_id: str,
    source_type: str,
    source_id: str,
    as_of: datetime,
    generated_at: datetime,
    reason: str,
) -> dict[str, Any]:
    cid = _sha(
        {
            "v": COMPOSITION_VERSION_V1,
            "fail": reason,
            "surface": surface_id,
            "source": source_id,
            "as_of": _as_of_key(as_of),
        }
    )[:32]
    rec = {
        "composition_id": cid,
        "surface_id": surface_id,
        "store_slug": store_slug,
        "source_type": source_type,
        "source_id": source_id,
        "source_lineage": {"failure_reason": reason},
        "information_class": CLASS_EMPTY_STATE,
        "presentation_intent": INTENT_WARNING,
        "merchant_value": "failure_isolation",
        "urgency": 0,
        "freshness_state": FRESH_EXPIRED,
        "confidence": "none",
        "expiry": as_of.isoformat(sep=" "),
        "visibility": VIS_SUPPRESSED,
        "visibility_reason": reason,
        "destination_surfaces": [surface_id],
        "duplicate_group": f"fail:{source_id}",
        "owns_full_explanation": False,
        "suppression_rules": [reason],
        "priority": 0,
        "accounting_outcome": ACCT_FAILED,
        "lifecycle": "create",
        "valid_from": as_of.isoformat(sep=" "),
        "valid_until": as_of.isoformat(sep=" "),
        "is_current": True,
        "composition_version": COMPOSITION_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "surface_registry_version": SURFACE_REGISTRY_VERSION_V1,
        "source_contract_version": SOURCE_CONTRACT_VERSION_V1,
        "input_fingerprint": "",
        "as_of": as_of.isoformat(sep=" "),
        "created_at": generated_at.isoformat(sep=" "),
        "refreshed_at": generated_at.isoformat(sep=" "),
        "superseded_at": None,
        "failure_reason": reason,
    }
    rec["fingerprint"] = _sha(
        {k: v for k, v in rec.items() if k != "fingerprint"}
    )
    return rec


def evaluate_presentation_composition_v1(
    *,
    presentation: dict[str, Any],
    as_of: datetime,
    generated_at: datetime,
) -> dict[str, Any]:
    """Compose one item from one merchant presentation contract."""
    surface_id = str(presentation.get("surface_key") or "")
    store = str(presentation.get("store_slug") or "")
    info_class, intent = _map_presentation(presentation)
    valid_until = _parse_iso(presentation.get("valid_until")) or as_of
    freshness = freshness_state_v1(valid_until=valid_until, as_of=as_of)
    state = str(presentation.get("presentation_state") or "")
    evidence = str(presentation.get("evidence_state") or "")
    role = str(presentation.get("route_role") or "")
    guidance_id = str(presentation.get("guidance_id") or "")
    route_id = str(presentation.get("route_id") or "")
    presentation_id = str(presentation.get("presentation_id") or "")
    # Class-scoped group: same guidance may legitimately appear as different
    # information classes (e.g. Home executive summary vs Decision critical).
    duplicate_group = f"guidance:{guidance_id or presentation_id}:{info_class}"
    owner = DUPLICATE_OWNER_BY_CLASS_V1.get(info_class, surface_id)
    owns_full = surface_id == owner

    priority = priority_score_v1(
        information_class=info_class,
        route_role=role,
        presentation_state=state,
        freshness=freshness,
        evidence_state=evidence,
        presentation_type=str(presentation.get("presentation_type") or ""),
    )

    visibility = VIS_VISIBLE
    visibility_reason = "eligible"
    suppression_rules: list[str] = []
    accounting = ACCT_COMPOSED

    if freshness == FRESH_EXPIRED or state == STATE_EXPIRED:
        visibility = VIS_EXPIRED
        visibility_reason = "expired"
        accounting = ACCT_EXPIRED
        suppression_rules.append("expiry")
    elif state == STATE_FAILED:
        visibility = VIS_SUPPRESSED
        visibility_reason = "source_failed"
        accounting = ACCT_FAILED
        suppression_rules.append("source_failed")
    elif state == STATE_DEFERRED:
        visibility = VIS_COLLAPSED
        visibility_reason = "deferred_source"
        accounting = ACCT_DEFERRED
        suppression_rules.append("deferred")
    elif not owns_full and surface_id != SURFACE_HOME:
        # Non-owner surfaces keep a reference, not the full explanation.
        intent = INTENT_REFERENCE
        visibility_reason = "duplicate_reference"
        suppression_rules.append("duplicate_group_reference")

    registry = get_surface_registry_entry_v1(surface_id)
    if registry is None:
        return _failed_composition(
            store_slug=store,
            surface_id=surface_id or "unknown",
            source_type=SOURCE_MERCHANT_PRESENTATION,
            source_id=presentation_id,
            as_of=as_of,
            generated_at=generated_at,
            reason="unsupported_surface",
        )
    if info_class not in (registry.get("supported_information_classes") or []):
        visibility = VIS_SUPPRESSED
        visibility_reason = "class_not_supported_on_surface"
        accounting = ACCT_REJECTED
        suppression_rules.append("unsupported_class")

    input_fingerprint = _sha(
        {
            "presentation_id": presentation_id,
            "presentation_fingerprint": presentation.get("presentation_fingerprint"),
            "route_id": route_id,
            "surface": surface_id,
            "class": info_class,
            "as_of": _as_of_key(as_of),
        }
    )
    composition_id = _sha(
        {
            "v": COMPOSITION_VERSION_V1,
            "gen": GENERATION_VERSION_V1,
            "presentation_id": presentation_id,
            "surface": surface_id,
            "class": info_class,
            "as_of": _as_of_key(as_of),
            "input": input_fingerprint,
        }
    )[:32]

    if accounting == ACCT_COMPOSED:
        accounting = _accounting_for_visibility(visibility, state)

    record = {
        "composition_id": composition_id,
        "surface_id": surface_id,
        "store_slug": store,
        "source_type": SOURCE_MERCHANT_PRESENTATION,
        "source_id": presentation_id,
        "source_lineage": {
            "presentation_id": presentation_id,
            "route_id": route_id,
            "guidance_id": guidance_id,
            "guidance_key": presentation.get("guidance_key"),
            "subject_type": presentation.get("subject_type"),
            "subject_id": presentation.get("subject_id"),
        },
        "information_class": info_class,
        "presentation_intent": intent,
        "merchant_value": str(presentation.get("merchant_relevance_key") or info_class),
        "urgency": min(100, priority),
        "freshness_state": freshness,
        "confidence": evidence or "unknown",
        "expiry": valid_until.isoformat(sep=" "),
        "visibility": visibility,
        "visibility_reason": visibility_reason,
        "destination_surfaces": [surface_id],
        "duplicate_group": duplicate_group,
        "owns_full_explanation": owns_full,
        "suppression_rules": suppression_rules,
        "priority": priority,
        "accounting_outcome": accounting,
        "lifecycle": "create",
        "valid_from": as_of.isoformat(sep=" "),
        "valid_until": valid_until.isoformat(sep=" "),
        "is_current": True,
        "composition_version": COMPOSITION_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "surface_registry_version": SURFACE_REGISTRY_VERSION_V1,
        "source_contract_version": SOURCE_CONTRACT_VERSION_V1,
        "input_fingerprint": input_fingerprint,
        "as_of": as_of.isoformat(sep=" "),
        "created_at": generated_at.isoformat(sep=" "),
        "refreshed_at": generated_at.isoformat(sep=" "),
        "superseded_at": None,
        "failure_reason": "",
        "route_role": role,
        "presentation_state": state,
        "presentation_type": str(presentation.get("presentation_type") or ""),
        "evidence_state": evidence,
    }
    record["fingerprint"] = _sha(
        {k: v for k, v in record.items() if k != "fingerprint"}
    )
    return record


def evaluate_operational_truth_composition_v1(
    *,
    package: dict[str, Any],
    surface_id: str,
    as_of: datetime,
    generated_at: datetime,
) -> dict[str, Any]:
    """Compose one Operational Truth package onto an allowed surface."""
    store = str(package.get("store_slug") or "")
    tid = str(package.get("truth_id") or "")
    pkg_id = str(package.get("package_id") or tid)
    info_class = str(
        package.get("information_class") or CLASS_OPERATIONAL_HEALTH
    )
    severity = str(package.get("severity") or "informational")
    freshness = FRESH_FRESH
    route_role = (
        "critical"
        if severity == "critical"
        else ("review" if severity == "warning" else "awareness")
    )
    priority = priority_score_v1(
        information_class=info_class,
        route_role=route_role,
        presentation_state=STATE_READY,
        freshness=freshness,
        evidence_state="sufficient_evidence",
        presentation_type="operational_truth",
    )
    # Severity boost for OT.
    if severity == "critical":
        priority += 12
    elif severity == "warning":
        priority += 6

    visibility = VIS_VISIBLE
    visibility_reason = "operational_truth_exposed"
    accounting = ACCT_COMPOSED
    suppression: list[str] = []
    if package.get("visibility") != "expose":
        visibility = VIS_SUPPRESSED
        visibility_reason = f"ot_{package.get('visibility_reason') or 'suppressed'}"
        accounting = ACCT_SUPPRESSED
        suppression.append("ot_visibility")

    owner = DUPLICATE_OWNER_BY_CLASS_V1.get(info_class, surface_id)
    owns_full = surface_id == owner
    if info_class == CLASS_CRITICAL_ATTENTION:
        intent = INTENT_PRIORITY_CARD if owns_full else INTENT_REFERENCE
    elif info_class in {CLASS_OPERATIONAL_HEALTH, CLASS_RECOVERY_HEALTH}:
        intent = INTENT_OPERATIONAL_STATE if owns_full else INTENT_REFERENCE
    else:
        intent = INTENT_WARNING if severity != "informational" else INTENT_INFORMATION

    explain = dict(package.get("explainability") or {})
    input_fingerprint = _sha(
        {
            "package_id": pkg_id,
            "truth_id": tid,
            "surface": surface_id,
            "count": package.get("count"),
            "severity": severity,
            "as_of": _as_of_key(as_of),
        }
    )
    composition_id = _sha(
        {
            "v": COMPOSITION_VERSION_V1,
            "gen": GENERATION_VERSION_V1,
            "ot": tid,
            "surface": surface_id,
            "as_of": _as_of_key(as_of),
            "input": input_fingerprint,
        }
    )[:32]
    # Keep OT fresh for the generation window (7d) for display freshness.
    valid_until = as_of + timedelta(days=7)
    freshness = freshness_state_v1(valid_until=valid_until, as_of=as_of)
    return {
        "composition_id": composition_id,
        "surface_id": surface_id,
        "store_slug": store,
        "source_type": SOURCE_OPERATIONAL_TRUTH,
        "source_id": pkg_id,
        "source_lineage": {
            "truth_id": tid,
            "package_id": pkg_id,
            "metric_key": package.get("metric_key"),
            "count": package.get("count"),
            "severity": severity,
            "stability": package.get("stability"),
            "evidence": package.get("evidence"),
            "explainability": explain,
        },
        "information_class": info_class,
        "presentation_intent": intent,
        "merchant_value": explain.get("what_happened_ar")
        or f"operational_truth:{tid}",
        "urgency": min(100, priority),
        "freshness_state": freshness,
        "confidence": package.get("confidence") or "high",
        "expiry": valid_until.isoformat(sep=" "),
        "visibility": visibility,
        "visibility_reason": visibility_reason,
        "destination_surfaces": [surface_id],
        "duplicate_group": f"operational_truth:{tid}:{info_class}",
        "owns_full_explanation": owns_full,
        "suppression_rules": suppression,
        "priority": priority,
        "accounting_outcome": accounting,
        "lifecycle": "create",
        "valid_from": as_of.isoformat(sep=" "),
        "valid_until": valid_until.isoformat(sep=" "),
        "is_current": True,
        "composition_version": COMPOSITION_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "surface_registry_version": SURFACE_REGISTRY_VERSION_V1,
        "source_contract_version": OPERATIONAL_TRUTH_SOURCE_CONTRACT_VERSION_V1,
        "input_fingerprint": input_fingerprint,
        "as_of": as_of.isoformat(sep=" "),
        "created_at": generated_at.isoformat(sep=" "),
        "refreshed_at": generated_at.isoformat(sep=" "),
        "superseded_at": None,
        "failure_reason": "",
        "route_role": route_role,
        "presentation_state": STATE_READY,
        "presentation_type": "operational_truth",
        "evidence_state": "sufficient_evidence",
        "fingerprint": "",
        "requires_merchant_attention": bool(
            package.get("requires_merchant_attention")
        ),
    }


def evaluate_knowledge_composition_v1(
    *,
    statement: dict[str, Any],
    surface_id: str,
    as_of: datetime,
    generated_at: datetime,
) -> dict[str, Any]:
    """Compose one Knowledge-class item for an allowed surface."""
    store = str(statement.get("store_slug") or "")
    kid = str(statement.get("knowledge_id") or "")
    valid_until = _parse_iso(statement.get("valid_until")) or as_of
    freshness = freshness_state_v1(valid_until=valid_until, as_of=as_of)
    confidence = str(statement.get("confidence_level") or "unknown")
    priority = priority_score_v1(
        information_class=CLASS_KNOWLEDGE,
        route_role="awareness",
        presentation_state=STATE_READY,
        freshness=freshness,
        evidence_state="sufficient_evidence"
        if confidence in {"high", "medium"}
        else "limited_evidence",
        presentation_type="knowledge",
    )
    visibility = VIS_VISIBLE
    visibility_reason = "eligible"
    accounting = ACCT_COMPOSED
    suppression: list[str] = []
    if freshness == FRESH_EXPIRED:
        visibility = VIS_EXPIRED
        visibility_reason = "expired"
        accounting = ACCT_EXPIRED
        suppression.append("expiry")

    owner = DUPLICATE_OWNER_BY_CLASS_V1[CLASS_KNOWLEDGE]
    owns_full = surface_id == owner
    intent = INTENT_INSIGHT_CARD if owns_full else INTENT_REFERENCE

    input_fingerprint = _sha(
        {
            "knowledge_id": kid,
            "fingerprint": statement.get("fingerprint"),
            "surface": surface_id,
            "as_of": _as_of_key(as_of),
        }
    )
    composition_id = _sha(
        {
            "v": COMPOSITION_VERSION_V1,
            "gen": GENERATION_VERSION_V1,
            "knowledge_id": kid,
            "surface": surface_id,
            "as_of": _as_of_key(as_of),
            "input": input_fingerprint,
        }
    )[:32]
    return {
        "composition_id": composition_id,
        "surface_id": surface_id,
        "store_slug": store,
        "source_type": SOURCE_KNOWLEDGE,
        "source_id": kid,
        "source_lineage": {
            "knowledge_id": kid,
            "knowledge_type": statement.get("knowledge_type"),
            "evidence_confidence_id": statement.get("evidence_confidence_id"),
            "subject_type": statement.get("subject_type"),
            "subject_id": statement.get("subject_id"),
        },
        "information_class": CLASS_KNOWLEDGE,
        "presentation_intent": intent,
        "merchant_value": "knowledge_highlight",
        "urgency": min(100, priority),
        "freshness_state": freshness,
        "confidence": confidence,
        "expiry": valid_until.isoformat(sep=" "),
        "visibility": visibility,
        "visibility_reason": visibility_reason,
        "destination_surfaces": [surface_id],
        "duplicate_group": f"knowledge:{kid}",
        "owns_full_explanation": owns_full,
        "suppression_rules": suppression,
        "priority": priority,
        "accounting_outcome": accounting,
        "lifecycle": "create",
        "valid_from": as_of.isoformat(sep=" "),
        "valid_until": valid_until.isoformat(sep=" "),
        "is_current": True,
        "composition_version": COMPOSITION_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "surface_registry_version": SURFACE_REGISTRY_VERSION_V1,
        "source_contract_version": KNOWLEDGE_SOURCE_CONTRACT_VERSION_V1,
        "input_fingerprint": input_fingerprint,
        "as_of": as_of.isoformat(sep=" "),
        "created_at": generated_at.isoformat(sep=" "),
        "refreshed_at": generated_at.isoformat(sep=" "),
        "superseded_at": None,
        "failure_reason": "",
        "route_role": "awareness",
        "presentation_state": STATE_READY,
        "presentation_type": "knowledge",
        "evidence_state": confidence,
        "fingerprint": "",
    }


def _empty_state_composition(
    *,
    store_slug: str,
    surface_id: str,
    empty_key: str,
    as_of: datetime,
    generated_at: datetime,
) -> dict[str, Any]:
    """Truthful empty states — never fabricate commercial guidance."""
    valid_until = as_of
    input_fingerprint = _sha(
        {
            "empty": empty_key,
            "surface": surface_id,
            "store": store_slug,
            "as_of": _as_of_key(as_of),
        }
    )
    composition_id = _sha(
        {
            "v": COMPOSITION_VERSION_V1,
            "empty": empty_key,
            "surface": surface_id,
            "as_of": _as_of_key(as_of),
            "input": input_fingerprint,
        }
    )[:32]
    return {
        "composition_id": composition_id,
        "surface_id": surface_id,
        "store_slug": store_slug,
        "source_type": SOURCE_EMPTY_STATE,
        "source_id": empty_key,
        "source_lineage": {"empty_state_key": empty_key},
        "information_class": CLASS_EMPTY_STATE,
        "presentation_intent": INTENT_INFORMATION,
        "merchant_value": empty_key,
        "urgency": 0,
        "freshness_state": FRESH_FRESH,
        "confidence": "n/a",
        "expiry": valid_until.isoformat(sep=" "),
        "visibility": VIS_VISIBLE,
        "visibility_reason": f"empty_state:{empty_key}",
        "destination_surfaces": [surface_id],
        "duplicate_group": f"empty:{surface_id}:{empty_key}",
        "owns_full_explanation": True,
        "suppression_rules": [],
        "priority": 1,
        "accounting_outcome": ACCT_COMPOSED,
        "lifecycle": "create",
        "valid_from": as_of.isoformat(sep=" "),
        "valid_until": valid_until.isoformat(sep=" "),
        "is_current": True,
        "composition_version": COMPOSITION_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "surface_registry_version": SURFACE_REGISTRY_VERSION_V1,
        "source_contract_version": SOURCE_CONTRACT_VERSION_V1,
        "input_fingerprint": input_fingerprint,
        "as_of": as_of.isoformat(sep=" "),
        "created_at": generated_at.isoformat(sep=" "),
        "refreshed_at": generated_at.isoformat(sep=" "),
        "superseded_at": None,
        "failure_reason": "",
        "route_role": "",
        "presentation_state": "",
        "presentation_type": "empty_state",
        "evidence_state": "",
        "fingerprint": "",
    }


def _apply_duplicate_governance(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Within each surface, one winner per duplicate_group; cross-surface owner keeps full."""
    by_surface_group: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        key = (str(item.get("surface_id")), str(item.get("duplicate_group")))
        by_surface_group[key].append(item)

    winners: set[str] = set()
    for group_items in by_surface_group.values():
        ordered = sorted(
            group_items,
            key=lambda x: (
                -int(x.get("priority") or 0),
                str(x.get("composition_id") or ""),
            ),
        )
        winners.add(str(ordered[0]["composition_id"]))
        for loser in ordered[1:]:
            loser["visibility"] = VIS_SUPPRESSED
            loser["visibility_reason"] = "duplicate_within_surface"
            loser["accounting_outcome"] = ACCT_SUPPRESSED
            rules = list(loser.get("suppression_rules") or [])
            rules.append("duplicate_within_surface")
            loser["suppression_rules"] = rules
            loser["presentation_intent"] = INTENT_REFERENCE

    # Across surfaces: non-owner full explanations become references.
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        if item.get("accounting_outcome") == ACCT_FAILED:
            continue
        by_group[str(item.get("duplicate_group"))].append(item)
    for group, group_items in by_group.items():
        if group.startswith("empty:") or group.startswith("fail:"):
            continue
        owners = [i for i in group_items if i.get("owns_full_explanation")]
        if not owners:
            continue
        owner_id = str(
            sorted(
                owners,
                key=lambda x: (
                    -int(x.get("priority") or 0),
                    str(x.get("composition_id") or ""),
                ),
            )[0]["composition_id"]
        )
        for item in group_items:
            cid = str(item.get("composition_id"))
            if cid == owner_id:
                continue
            if item.get("visibility") in {VIS_EXPIRED, VIS_SUPPRESSED}:
                continue
            if item.get("owns_full_explanation"):
                item["owns_full_explanation"] = False
                item["presentation_intent"] = INTENT_REFERENCE
                item["visibility_reason"] = "owned_elsewhere"
                rules = list(item.get("suppression_rules") or [])
                if "owned_elsewhere" not in rules:
                    rules.append("owned_elsewhere")
                item["suppression_rules"] = rules
    return items


def _apply_cognitive_load(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enforce per-surface class/intent limits; overflow → collapsed."""
    by_surface: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_surface[str(item.get("surface_id"))].append(item)

    for surface_id, surface_items in by_surface.items():
        registry = get_surface_registry_entry_v1(surface_id) or {}
        limits = dict(registry.get("maximum_cognitive_load") or {})
        counters: dict[str, int] = defaultdict(int)
        hero_used = 0
        ordered = sorted(
            surface_items,
            key=lambda x: (
                -int(x.get("priority") or 0),
                str(x.get("composition_id") or ""),
            ),
        )
        for item in ordered:
            if item.get("visibility") not in {VIS_VISIBLE}:
                continue
            info_class = str(item.get("information_class") or "")
            intent = str(item.get("presentation_intent") or "")

            # Hero: at most one on Home.
            if surface_id == SURFACE_HOME and intent != INTENT_REFERENCE:
                hero_limit = int(limits.get(INTENT_HERO) or 0)
                if (
                    hero_limit
                    and hero_used == 0
                    and info_class
                    in {
                        "executive_summary",
                        "critical_attention",
                        "commercial_guidance",
                    }
                ):
                    item["presentation_intent"] = INTENT_HERO
                    hero_used = 1
                elif intent == INTENT_HERO and hero_used >= hero_limit:
                    item["presentation_intent"] = INTENT_SUMMARY_CARD

            limit_key = info_class
            limit = limits.get(limit_key)
            if limit is None:
                continue
            if counters[limit_key] >= int(limit):
                item["visibility"] = VIS_COLLAPSED
                item["visibility_reason"] = "cognitive_load_overflow"
                item["accounting_outcome"] = ACCT_COLLAPSED
                rules = list(item.get("suppression_rules") or [])
                rules.append("cognitive_load_overflow")
                item["suppression_rules"] = rules
            else:
                counters[limit_key] += 1
    return items


def _finalize_fingerprints(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for item in items:
        item["fingerprint"] = _sha(
            {k: v for k, v in item.items() if k != "fingerprint"}
        )
    return items


def generate_surface_compositions_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    """Generate surface compositions from Presentation + Knowledge + Operational Truth."""
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or "d7").strip().lower()
    reg_ok, reg_errors = surface_registry_valid_v1()
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "assembly_window": window,
        "as_of": None,
        "composition_version": COMPOSITION_VERSION_V1,
        "generation_version": GENERATION_VERSION_V1,
        "surface_registry_version": SURFACE_REGISTRY_VERSION_V1,
        "compositions": [],
        "composition_count": 0,
        "expected_input_count": 0,
        "accounted_count": 0,
        "canonical_fingerprint": "",
        "errors": list(reg_errors),
        "inputs": {
            "merchant_presentation": True,
            "knowledge": True,
            "operational_truth": True,
            "guidance_routing_via_presentation": True,
            "no_raw_events": True,
            "no_cis": True,
            "no_widget_events": True,
            "no_whatsapp_events": True,
        },
        "registries_valid": bool(reg_ok),
        "surfaces": list_surfaces_v1(),
        "accounting": {k: 0 for k in (
            ACCT_COMPOSED,
            ACCT_COLLAPSED,
            ACCT_SUPPRESSED,
            ACCT_EXPIRED,
            ACCT_DEFERRED,
            ACCT_REJECTED,
            ACCT_FAILED,
        )},
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not reg_ok:
        out["errors"].append("invalid_registry")
        return out

    from services.product_data.time_authority_binding_resolve_v1 import (  # noqa: PLC0415
        resolve_bound_as_of_v1,
    )

    anchor = resolve_bound_as_of_v1(as_of)
    out["as_of"] = anchor.isoformat(sep=" ")

    presentations_report = generate_merchant_presentations_v1(
        slug, assembly_window=window, as_of=anchor
    )
    if not presentations_report.get("ok") and not presentations_report.get(
        "presentations"
    ):
        out["errors"].extend(
            [
                f"presentation:{e}"
                for e in (presentations_report.get("errors") or ["failed"])
            ]
        )
        return out

    presentations = list(presentations_report.get("presentations") or [])
    knowledge_report = generate_knowledge_v1(
        slug, assembly_window=window, as_of=anchor
    )
    statements = list(knowledge_report.get("statements") or [])
    if not knowledge_report.get("ok") and knowledge_report.get("errors"):
        # Knowledge failure is isolated — do not fail entire composition.
        out["errors"].extend(
            [f"knowledge:{e}" for e in (knowledge_report.get("errors") or [])]
        )

    # Operational Truth packages (governed; failure isolated).
    ot_packages: list[dict[str, Any]] = []
    try:
        from services.product_data.operational_truth_flag_v1 import (  # noqa: PLC0415
            operational_truth_v1_enabled,
        )
        from services.product_data.operational_truth_foundation_v1 import (  # noqa: PLC0415
            generate_operational_truth_v1,
        )

        if operational_truth_v1_enabled():
            ot_report = generate_operational_truth_v1(
                slug, assembly_window=window, as_of=anchor
            )
            ot_packages = [
                p
                for p in list(ot_report.get("packages") or [])
                if p.get("visibility") == "expose"
            ]
            if not ot_report.get("ok") and ot_report.get("errors"):
                out["errors"].extend(
                    [f"operational_truth:{e}" for e in (ot_report.get("errors") or [])]
                )
            out["operational_truth_exposed"] = int(ot_report.get("exposed_count") or 0)
    except Exception as ot_exc:  # noqa: BLE001
        out["errors"].append(f"operational_truth:{type(ot_exc).__name__}")
        log.warning("scf operational truth intake failed: %s", ot_exc)

    expected = len(presentations) + len(statements) + len(ot_packages)
    out["expected_input_count"] = expected

    compositions: list[dict[str, Any]] = []
    for pres in sorted(
        presentations,
        key=lambda p: (
            str(p.get("surface_key") or ""),
            str(p.get("presentation_id") or ""),
        ),
    ):
        try:
            compositions.append(
                evaluate_presentation_composition_v1(
                    presentation=pres, as_of=anchor, generated_at=anchor
                )
            )
        except Exception as exc:  # noqa: BLE001
            compositions.append(
                _failed_composition(
                    store_slug=slug,
                    surface_id=str(pres.get("surface_key") or "unknown"),
                    source_type=SOURCE_MERCHANT_PRESENTATION,
                    source_id=str(pres.get("presentation_id") or ""),
                    as_of=anchor,
                    generated_at=anchor,
                    reason=f"exception:{type(exc).__name__}",
                )
            )
            out["errors"].append(
                f"compose_fail:{pres.get('surface_key')}:{type(exc).__name__}"
            )

    # Knowledge highlights — Home only (registry owner).
    for stmt in sorted(
        statements, key=lambda s: str(s.get("knowledge_id") or "")
    ):
        try:
            item = evaluate_knowledge_composition_v1(
                statement=stmt,
                surface_id=SURFACE_HOME,
                as_of=anchor,
                generated_at=anchor,
            )
            # fingerprint filled later
            item["fingerprint"] = _sha(
                {k: v for k, v in item.items() if k != "fingerprint"}
            )
            compositions.append(item)
        except Exception as exc:  # noqa: BLE001
            compositions.append(
                _failed_composition(
                    store_slug=slug,
                    surface_id=SURFACE_HOME,
                    source_type=SOURCE_KNOWLEDGE,
                    source_id=str(stmt.get("knowledge_id") or ""),
                    as_of=anchor,
                    generated_at=anchor,
                    reason=f"exception:{type(exc).__name__}",
                )
            )

    # Operational Truth → destination surfaces (packages only; no raw tables in SCF).
    for pkg in sorted(
        ot_packages,
        key=lambda p: (str(p.get("truth_id") or ""), str(p.get("package_id") or "")),
    ):
        for surface_id in sorted(pkg.get("destination_surfaces") or []):
            try:
                item = evaluate_operational_truth_composition_v1(
                    package=pkg,
                    surface_id=str(surface_id),
                    as_of=anchor,
                    generated_at=anchor,
                )
                item["fingerprint"] = _sha(
                    {k: v for k, v in item.items() if k != "fingerprint"}
                )
                compositions.append(item)
            except Exception as exc:  # noqa: BLE001
                compositions.append(
                    _failed_composition(
                        store_slug=slug,
                        surface_id=str(surface_id),
                        source_type=SOURCE_OPERATIONAL_TRUTH,
                        source_id=str(pkg.get("package_id") or ""),
                        as_of=anchor,
                        generated_at=anchor,
                        reason=f"exception:{type(exc).__name__}",
                    )
                )
                out["errors"].append(
                    f"compose_fail:ot:{pkg.get('truth_id')}:{type(exc).__name__}"
                )

    compositions = _apply_duplicate_governance(compositions)
    compositions = _apply_cognitive_load(compositions)

    # Empty-state governance per surface with no visible non-empty items.
    ot_surfaces_with_truth = {
        str(s)
        for p in ot_packages
        for s in (p.get("destination_surfaces") or [])
    }
    for surface_id in list_surfaces_v1():
        visible = [
            c
            for c in compositions
            if c.get("surface_id") == surface_id
            and c.get("visibility") == VIS_VISIBLE
            and c.get("information_class") != CLASS_EMPTY_STATE
        ]
        if visible:
            continue
        # OT prevents false "no operational issues" when durable ops exist.
        if surface_id in ot_surfaces_with_truth:
            continue
        # Choose truthful empty key from presentation/knowledge reality.
        surface_pres = [
            p for p in presentations if p.get("surface_key") == surface_id
        ]
        if not presentations and not statements and not ot_packages:
            empty_key = "evidence_still_growing"
        elif any(
            p.get("presentation_state") == STATE_INSUFFICIENT for p in surface_pres
        ):
            empty_key = "insufficient_evidence"
        elif surface_id in {"carts", "communication"} and not surface_pres:
            empty_key = "no_operational_issues"
        else:
            empty_key = "nothing_requiring_action"
        if empty_key not in EMPTY_STATE_KEYS_V1:
            empty_key = "nothing_requiring_action"
        empty = _empty_state_composition(
            store_slug=slug,
            surface_id=surface_id,
            empty_key=empty_key,
            as_of=anchor,
            generated_at=anchor,
        )
        empty["fingerprint"] = _sha(
            {k: v for k, v in empty.items() if k != "fingerprint"}
        )
        compositions.append(empty)
        expected += 1

    compositions = _finalize_fingerprints(compositions)
    compositions.sort(
        key=lambda c: (
            str(c.get("surface_id") or ""),
            -int(c.get("priority") or 0),
            str(c.get("composition_id") or ""),
        )
    )

    accounting = {k: 0 for k in out["accounting"]}
    for c in compositions:
        outcome = str(c.get("accounting_outcome") or ACCT_FAILED)
        if outcome not in accounting:
            outcome = ACCT_FAILED
            c["accounting_outcome"] = outcome
        accounting[outcome] += 1

    out["compositions"] = compositions
    out["composition_count"] = len(compositions)
    out["expected_input_count"] = expected
    out["accounted_count"] = sum(accounting.values())
    out["accounting"] = accounting
    out["canonical_fingerprint"] = _sha(
        {
            "v": GENERATION_VERSION_V1,
            "store": slug,
            "as_of": out["as_of"],
            "compositions": [
                {
                    "composition_id": c["composition_id"],
                    "surface_id": c["surface_id"],
                    "visibility": c["visibility"],
                    "accounting_outcome": c["accounting_outcome"],
                    "fingerprint": c.get("fingerprint") or "",
                }
                for c in compositions
            ],
        }
    )
    out["ok"] = (
        out["accounted_count"] == out["composition_count"]
        and out["composition_count"] >= len(SURFACE_REGISTRY_V1)
        and not any(str(e).startswith("compose_fail:") for e in out["errors"])
    )
    if out["accounted_count"] != out["composition_count"]:
        out["errors"].append("composition_accounting_mismatch")
    return out


def materialize_surface_compositions_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    if not surface_composition_v1_enabled():
        return {
            "ok": False,
            "skipped_disabled": True,
            "upserted": 0,
            "superseded": 0,
            "errors": ["surface_composition_disabled"],
        }

    report = generate_surface_compositions_v1(
        store_slug, assembly_window=assembly_window, as_of=as_of
    )
    if report.get("composition_count", 0) == 0 and not report.get("ok"):
        return {
            "ok": False,
            "upserted": 0,
            "superseded": 0,
            "errors": list(report.get("errors") or []),
            "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        }

    ensure_surface_composition_schema(db)
    anchor = _parse_iso(report.get("as_of")) or _floor_second(as_of or _utc_naive_now())
    as_key = _as_of_key(anchor)
    now = _utc_naive_now()
    upserted = 0
    superseded = 0
    errors: list[str] = list(report.get("errors") or [])

    for rec in report.get("compositions") or []:
        surface = str(rec.get("surface_id") or "")
        try:
            cid = str(rec["composition_id"])
            store = str(rec["store_slug"])
            source_id = str(rec.get("source_id") or "")

            currents = (
                db.session.query(SurfaceComposition)
                .filter(
                    SurfaceComposition.store_slug == store,
                    SurfaceComposition.surface_id == surface,
                    SurfaceComposition.source_type == str(rec.get("source_type") or ""),
                    SurfaceComposition.source_id == source_id,
                    SurfaceComposition.is_current.is_(True),
                    SurfaceComposition.composition_id != cid,
                )
                .all()
            )
            for row in currents:
                row.is_current = False
                row.lifecycle = "supersede"
                row.superseded_at = now
                superseded += 1

            existing = (
                db.session.query(SurfaceComposition)
                .filter(SurfaceComposition.composition_id == cid)
                .first()
            )
            fields = dict(
                surface_id=surface,
                store_slug=store,
                source_type=str(rec.get("source_type") or ""),
                source_id=source_id,
                source_lineage_json=json.dumps(
                    rec.get("source_lineage") or {},
                    sort_keys=True,
                    ensure_ascii=False,
                ),
                information_class=str(rec.get("information_class") or ""),
                presentation_intent=str(rec.get("presentation_intent") or ""),
                merchant_value=str(rec.get("merchant_value") or ""),
                urgency=int(rec.get("urgency") or 0),
                freshness_state=str(rec.get("freshness_state") or ""),
                confidence=str(rec.get("confidence") or ""),
                expiry=_parse_iso(rec.get("expiry")) or anchor,
                visibility=str(rec.get("visibility") or ""),
                visibility_reason=str(rec.get("visibility_reason") or ""),
                destination_surfaces_json=json.dumps(
                    rec.get("destination_surfaces") or [],
                    sort_keys=True,
                    ensure_ascii=False,
                ),
                duplicate_group=str(rec.get("duplicate_group") or ""),
                owns_full_explanation=bool(rec.get("owns_full_explanation")),
                suppression_rules_json=json.dumps(
                    rec.get("suppression_rules") or [],
                    sort_keys=True,
                    ensure_ascii=False,
                ),
                priority=int(rec.get("priority") or 0),
                accounting_outcome=str(rec.get("accounting_outcome") or ""),
                lifecycle=str(rec.get("lifecycle") or "create"),
                valid_from=anchor,
                valid_until=_parse_iso(rec.get("valid_until")) or anchor,
                is_current=True,
                composition_version=COMPOSITION_VERSION_V1,
                generation_version=GENERATION_VERSION_V1,
                surface_registry_version=SURFACE_REGISTRY_VERSION_V1,
                source_contract_version=str(
                    rec.get("source_contract_version") or SOURCE_CONTRACT_VERSION_V1
                ),
                input_fingerprint=str(rec.get("input_fingerprint") or ""),
                fingerprint=str(rec.get("fingerprint") or ""),
                failure_reason=str(rec.get("failure_reason") or ""),
                as_of=anchor,
                as_of_key=as_key,
                created_at=existing.created_at if existing else now,
                refreshed_at=now,
                superseded_at=None,
            )
            if existing is None:
                db.session.add(SurfaceComposition(composition_id=cid, **fields))
            else:
                fields["lifecycle"] = "update"
                for k, v in fields.items():
                    setattr(existing, k, v)
            db.session.commit()
            upserted += 1
        except SQLAlchemyError as exc:
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass
            errors.append(f"materialize:{surface}:{type(exc).__name__}")
            log.debug("surface composition materialize failed: %s", exc)

    return {
        "ok": bool(report.get("ok") and upserted > 0),
        "upserted": upserted,
        "superseded": superseded,
        "errors": errors,
        "canonical_fingerprint": report.get("canonical_fingerprint") or "",
        "composition_count": report.get("composition_count") or 0,
        "accounted_count": report.get("accounted_count") or 0,
        "expected_input_count": report.get("expected_input_count") or 0,
        "accounting": report.get("accounting") or {},
        "store_slug": report.get("store_slug"),
        "as_of": report.get("as_of"),
    }


def verify_surface_composition_determinism_v1(
    store_slug: str,
    *,
    assembly_window: str = "d7",
    as_of: Optional[datetime] = None,
) -> dict[str, Any]:
    from services.product_data.time_authority_binding_resolve_v1 import (  # noqa: PLC0415
        resolve_bound_as_of_v1,
    )

    anchor = resolve_bound_as_of_v1(as_of)
    a = generate_surface_compositions_v1(
        store_slug, assembly_window=assembly_window, as_of=anchor
    )
    b = generate_surface_compositions_v1(
        store_slug, assembly_window=assembly_window, as_of=anchor
    )
    match = bool(
        a.get("ok")
        and b.get("ok")
        and a.get("canonical_fingerprint")
        and a.get("canonical_fingerprint") == b.get("canonical_fingerprint")
    )
    return {
        "ok": match,
        "deterministic": match,
        "as_of": anchor.isoformat(sep=" "),
        "fingerprint_a": a.get("canonical_fingerprint") or "",
        "fingerprint_b": b.get("canonical_fingerprint") or "",
        "composition_count": a.get("composition_count") or 0,
        "accounted_count": a.get("accounted_count") or 0,
        "errors": list(a.get("errors") or []) + list(b.get("errors") or []),
    }


__all__ = [
    "freshness_state_v1",
    "priority_score_v1",
    "evaluate_presentation_composition_v1",
    "evaluate_knowledge_composition_v1",
    "generate_surface_compositions_v1",
    "materialize_surface_compositions_v1",
    "verify_surface_composition_determinism_v1",
]
