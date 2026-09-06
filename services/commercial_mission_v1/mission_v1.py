# -*- coding: utf-8 -*-
"""
Commercial Mission — thin orchestration over COL + CDC.

Generic lifecycle for all registered mission families.
Family-specific behavior lives only in MissionFamilyProfile (A/B/C).
No family-specific state machine (D = 0).
No WON/LOST/LEARNED. No Scheduler.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Optional

from services.commercial_decision_commitment_v1 import (
    CommitmentError,
    accept_commitment,
    close_commitment,
    derive_commitment_state,
    get_active_commitment,
    start_measurement,
)
from services.commercial_decision_commitment_v1.contract_v1 import (
    PHASE_ACTION_CHOSEN,
    PHASE_RECHECK_DUE,
    PHASE_UNDER_MEASUREMENT,
)
from services.commercial_mission_v1.contract_v1 import (
    MATERIAL_SHARE_DELTA,
    MISSION_FAMILY,
    MISSION_VERSION,
    MissionFamilyProfile,
    get_mission_profile,
    opportunity_key_for_store,
)


class MissionError(CommitmentError):
    """Mission-scoped error (same codes / HTTP as CDC where applicable)."""


def _top_share_from_col(col_package: Mapping[str, Any]) -> Optional[float]:
    primary = col_package.get("primary") if isinstance(col_package, Mapping) else None
    if not isinstance(primary, Mapping):
        return None
    ev = primary.get("evidence") if isinstance(primary.get("evidence"), Mapping) else {}
    counts = ev.get("counts") if isinstance(ev.get("counts"), Mapping) else {}
    share = counts.get("top_share")
    if share is None:
        return None
    try:
        return float(share)
    except (TypeError, ValueError):
        return None


def _signal_counts_from_col(col_package: Mapping[str, Any]) -> dict[str, float]:
    primary = col_package.get("primary") if isinstance(col_package, Mapping) else None
    if not isinstance(primary, Mapping):
        return {}
    ev = primary.get("evidence") if isinstance(primary.get("evidence"), Mapping) else {}
    counts = ev.get("counts") if isinstance(ev.get("counts"), Mapping) else {}
    out: dict[str, float] = {}
    for k in ("hesitation_total", "top_count", "top_share"):
        if k in counts:
            try:
                out[k] = float(counts[k])
            except (TypeError, ValueError):
                continue
    return out


def _resolve_profile_for_primary(
    primary: Mapping[str, Any],
) -> MissionFamilyProfile:
    family = str(primary.get("family") or "")
    profile = get_mission_profile(family)
    if profile is None:
        raise MissionError("mission_family_unsupported", http_status=409)
    return profile


def assert_mission_opportunity(
    col_package: Mapping[str, Any],
    *,
    store_slug: str,
    expected_family: Optional[str] = None,
) -> tuple[dict[str, Any], MissionFamilyProfile]:
    """Require live COL primary to be a registered mission family for this store."""
    primary = col_package.get("primary") if isinstance(col_package, Mapping) else None
    if not isinstance(primary, Mapping):
        raise MissionError("mission_opportunity_missing", http_status=409)
    profile = _resolve_profile_for_primary(primary)
    if expected_family and profile.family != expected_family:
        raise MissionError("mission_family_mismatch", http_status=409)
    oid = str(primary.get("opportunity_id") or "")
    expected = opportunity_key_for_store(
        store_slug, family=profile.family, reason=profile.reason
    )
    if oid != expected:
        if not oid.startswith(f"col:{profile.family}:") or not oid.endswith(
            f":{store_slug}"
        ):
            raise MissionError("mission_opportunity_key_mismatch", http_status=409)
    return dict(primary), profile


def accept_mission(
    *,
    store_slug: str,
    col_package: Mapping[str, Any],
    expected_family: Optional[str] = None,
) -> dict[str, Any]:
    primary, profile = assert_mission_opportunity(
        col_package, store_slug=store_slug, expected_family=expected_family
    )
    key = str(
        primary.get("opportunity_id")
        or opportunity_key_for_store(
            store_slug, family=profile.family, reason=profile.reason
        )
    )
    out = accept_commitment(
        store_slug=store_slug,
        opportunity_key=key,
        col_package=dict(col_package),
        action_summary=profile.action_summary_ar,
        proposed_metric_key=profile.metric_key,
    )
    out["mission"] = {
        "version": MISSION_VERSION,
        "family": profile.family,
        "opportunity_key": key,
        "execution_authority": profile.execution_authority,
        "metric_key": profile.metric_key,
        "recheck_condition": profile.recheck_condition,
    }
    return out


def confirm_mission_execution(
    *,
    store_slug: str,
    commitment_id: str,
    col_package: Mapping[str, Any],
) -> dict[str, Any]:
    """
    EXECUTION_PROOF → UNDER_MEASUREMENT.

    Authority from family profile (must already be CDC-allowlisted).
    Freezes baseline from live COL top_share.
    """
    from extensions import db
    from models import CommercialDecisionCommitment

    row = (
        db.session.query(CommercialDecisionCommitment)
        .filter(
            CommercialDecisionCommitment.id == str(commitment_id),
            CommercialDecisionCommitment.store_slug == store_slug,
            CommercialDecisionCommitment.closed_at.is_(None),
        )
        .first()
    )
    if row is None:
        # Fallback: active row matching COL primary key when id omitted/stale
        primary = (
            col_package.get("primary") if isinstance(col_package, Mapping) else None
        )
        if isinstance(primary, Mapping):
            key = str(primary.get("opportunity_id") or "")
            if key:
                row = get_active_commitment(store_slug, key)
    if row is None:
        raise MissionError("commitment_not_found", http_status=404)

    profile = get_mission_profile(str(row.opportunity_family or ""))
    if profile is None:
        raise MissionError("mission_family_unsupported", http_status=409)

    phase = derive_commitment_state(row)
    if phase not in (PHASE_ACTION_CHOSEN, PHASE_UNDER_MEASUREMENT):
        if phase == PHASE_RECHECK_DUE:
            raise MissionError("mission_already_recheck_due", http_status=409)
        raise MissionError("mission_phase_invalid", http_status=409)

    share = _top_share_from_col(col_package)
    signals = _signal_counts_from_col(col_package)
    primary = col_package.get("primary") if isinstance(col_package, Mapping) else {}
    truth = ""
    if isinstance(primary, Mapping):
        truth = str(primary.get("truth_class") or "")

    out = start_measurement(
        store_slug=store_slug,
        commitment_id=str(commitment_id or row.id),
        authority=profile.execution_authority,
        measurement_start_ref=profile.execution_confirm_note,
        metric_key=profile.metric_key,
        metric_value=share,
        truth_class_at_start=truth,
        recheck_condition=profile.recheck_condition,
        signal_counts=signals,
    )
    out["mission"] = {
        "version": MISSION_VERSION,
        "family": profile.family,
        "execution_authority": profile.execution_authority,
        "baseline_share": share,
    }
    return out


def recheck_mission(
    *,
    store_slug: str,
    commitment_id: str,
    col_package: Mapping[str, Any],
) -> dict[str, Any]:
    """
    At RECHECK_DUE: re-read COL. No WON/LOST/LEARNED. No auto-close.
    Lifecycle is family-agnostic; compares live family to commitment family.
    """
    from extensions import db
    from models import CommercialDecisionCommitment

    row = (
        db.session.query(CommercialDecisionCommitment)
        .filter(
            CommercialDecisionCommitment.id == str(commitment_id),
            CommercialDecisionCommitment.store_slug == store_slug,
        )
        .first()
    )
    if row is None:
        raise MissionError("commitment_not_found", http_status=404)
    phase = derive_commitment_state(row)
    if row.closed_at is not None:
        raise MissionError("commitment_closed", http_status=409)

    committed_family = str(row.opportunity_family or "")
    primary = col_package.get("primary") if isinstance(col_package, Mapping) else None
    live_family = (
        str((primary or {}).get("family") or "") if isinstance(primary, Mapping) else ""
    )
    live_truth = (
        str((primary or {}).get("truth_class") or "")
        if isinstance(primary, Mapping)
        else ""
    )
    live_key = (
        str((primary or {}).get("opportunity_id") or "")
        if isinstance(primary, Mapping)
        else ""
    )
    live_share = _top_share_from_col(col_package)

    baseline_share = None
    try:
        if row.baseline_snapshot_json:
            base = json.loads(row.baseline_snapshot_json)
            if isinstance(base, dict) and base.get("metric_value") is not None:
                baseline_share = float(base["metric_value"])
    except (TypeError, ValueError, json.JSONDecodeError):
        baseline_share = row.baseline_metric_value

    delta = None
    if live_share is not None and baseline_share is not None:
        delta = abs(float(live_share) - float(baseline_share))

    material = bool(delta is not None and delta >= MATERIAL_SHARE_DELTA)
    still_same_family = bool(live_family and live_family == committed_family)
    weaker = live_truth in ("INSUFFICIENT",) or not still_same_family
    stronger = live_truth == "PRODUCTION_TRUTH_READY" and still_same_family
    conflicting = bool(live_key and live_key != row.opportunity_key and still_same_family)

    return {
        "ok": True,
        "mission_version": MISSION_VERSION,
        "commitment_id": row.id,
        "phase": phase,
        "remains_open": row.closed_at is None,
        "col_reread": {
            "opportunity_key": live_key or None,
            "family": live_family or None,
            "truth_class": live_truth or None,
            "top_share": live_share,
            # Backward-compatible alias (same value; not a lifecycle branch)
            "shipping_share": live_share,
        },
        "baseline_share": baseline_share,
        "share_delta_abs": delta,
        "signals": {
            "material_share_change": material,
            "weaker_evidence": weaker,
            "stronger_same_family": stronger,
            "conflicting_opportunity_id": conflicting,
            "won": False,
            "lost": False,
            "learned": False,
        },
        "note": "Recheck re-reads COL only — no outcome claim.",
    }


def abandon_mission(
    *,
    store_slug: str,
    commitment_id: str,
) -> dict[str, Any]:
    return close_commitment(
        store_slug=store_slug,
        commitment_id=commitment_id,
        close_reason="merchant_abandon",
        actor="merchant",
        close_note="commercial_mission_v1_abandon",
    )


# --- V1 shipping aliases (thin wrappers; same generic path) ---


def assert_shipping_mission_opportunity(
    col_package: Mapping[str, Any],
    *,
    store_slug: str,
) -> dict[str, Any]:
    primary, _ = assert_mission_opportunity(
        col_package, store_slug=store_slug, expected_family=MISSION_FAMILY
    )
    return primary


def accept_shipping_mission(
    *,
    store_slug: str,
    col_package: Mapping[str, Any],
) -> dict[str, Any]:
    return accept_mission(
        store_slug=store_slug,
        col_package=col_package,
        expected_family=MISSION_FAMILY,
    )


def confirm_shipping_execution(
    *,
    store_slug: str,
    commitment_id: str,
    col_package: Mapping[str, Any],
) -> dict[str, Any]:
    return confirm_mission_execution(
        store_slug=store_slug,
        commitment_id=commitment_id,
        col_package=col_package,
    )


def recheck_shipping_mission(
    *,
    store_slug: str,
    commitment_id: str,
    col_package: Mapping[str, Any],
) -> dict[str, Any]:
    return recheck_mission(
        store_slug=store_slug,
        commitment_id=commitment_id,
        col_package=col_package,
    )


def abandon_shipping_mission(
    *,
    store_slug: str,
    commitment_id: str,
) -> dict[str, Any]:
    return abandon_mission(store_slug=store_slug, commitment_id=commitment_id)


# Price aliases (V2 surface; same generic path)


def accept_price_mission(
    *,
    store_slug: str,
    col_package: Mapping[str, Any],
) -> dict[str, Any]:
    return accept_mission(
        store_slug=store_slug,
        col_package=col_package,
        expected_family="price_hesitation",
    )


def confirm_price_execution(
    *,
    store_slug: str,
    commitment_id: str,
    col_package: Mapping[str, Any],
) -> dict[str, Any]:
    return confirm_mission_execution(
        store_slug=store_slug,
        commitment_id=commitment_id,
        col_package=col_package,
    )


def recheck_price_mission(
    *,
    store_slug: str,
    commitment_id: str,
    col_package: Mapping[str, Any],
) -> dict[str, Any]:
    return recheck_mission(
        store_slug=store_slug,
        commitment_id=commitment_id,
        col_package=col_package,
    )


# Merchandising aliases (same generic path)


def accept_product_confidence_mission(
    *,
    store_slug: str,
    col_package: Mapping[str, Any],
) -> dict[str, Any]:
    return accept_mission(
        store_slug=store_slug,
        col_package=col_package,
        expected_family="product_confidence",
    )


def confirm_product_confidence_execution(
    *,
    store_slug: str,
    commitment_id: str,
    col_package: Mapping[str, Any],
) -> dict[str, Any]:
    return confirm_mission_execution(
        store_slug=store_slug,
        commitment_id=commitment_id,
        col_package=col_package,
    )


def accept_product_focus_mission(
    *,
    store_slug: str,
    col_package: Mapping[str, Any],
) -> dict[str, Any]:
    return accept_mission(
        store_slug=store_slug,
        col_package=col_package,
        expected_family="product_opportunity_focus",
    )


def confirm_product_focus_execution(
    *,
    store_slug: str,
    commitment_id: str,
    col_package: Mapping[str, Any],
) -> dict[str, Any]:
    return confirm_mission_execution(
        store_slug=store_slug,
        commitment_id=commitment_id,
        col_package=col_package,
    )


__all__ = [
    "MissionError",
    "abandon_mission",
    "abandon_shipping_mission",
    "accept_mission",
    "accept_price_mission",
    "accept_product_confidence_mission",
    "accept_product_focus_mission",
    "accept_shipping_mission",
    "assert_mission_opportunity",
    "assert_shipping_mission_opportunity",
    "confirm_mission_execution",
    "confirm_price_execution",
    "confirm_product_confidence_execution",
    "confirm_product_focus_execution",
    "confirm_shipping_execution",
    "recheck_mission",
    "recheck_price_mission",
    "recheck_shipping_mission",
]
