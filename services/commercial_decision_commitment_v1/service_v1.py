# -*- coding: utf-8 -*-
"""Commercial Decision Commitment V1 — accept / start / close / derive."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from sqlalchemy.exc import IntegrityError

from extensions import db
from models import CommercialDecisionCommitment
from schema_commercial_decision_commitment_v1 import (
    ensure_commercial_decision_commitment_schema,
)
from services.commercial_decision_commitment_v1.contract_v1 import (
    AUTHORITIES,
    AUTHORITY_CARTFLOW_EXECUTION,
    AUTHORITY_MERCHANT_EXECUTION_CONFIRM,
    CLOSE_REASONS,
    CLOSE_REASONS_MERCHANT,
    CLOSE_REASONS_SYSTEM,
    FORBIDDEN_CLOSE_REASONS,
    LAYER_VERSION,
    MERCHANT_CONFIRM_FAMILY_ALLOWLIST,
    PHASE_ACTION_CHOSEN,
    PHASE_RECHECK_DUE,
    PHASE_TO_CONSOLE_MODE,
    PHASE_UNDER_MEASUREMENT,
    resolve_measurement_window,
    resolve_measurement_window_days,
)
from services.commercial_decision_commitment_v1.snapshots_v1 import (
    SnapshotContractError,
    build_baseline_snapshot,
    build_decision_snapshot,
    validate_metric_key,
)


class CommitmentError(Exception):
    def __init__(self, code: str, *, http_status: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.http_status = http_status


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def derive_commitment_state(
    row: CommercialDecisionCommitment, *, now: Optional[datetime] = None
) -> Optional[str]:
    """Authoritative derived phase. None if closed."""
    if row.closed_at is not None:
        return None
    if row.action_chosen_at is None:
        return None
    if row.measurement_started_at is None:
        return PHASE_ACTION_CHOSEN
    due = _aware(row.measurement_due_at)
    started = _aware(row.measurement_started_at)
    if started is None or due is None:
        return PHASE_ACTION_CHOSEN
    clock = _aware(now) or _utcnow()
    if clock < due:
        return PHASE_UNDER_MEASUREMENT
    return PHASE_RECHECK_DUE


def get_active_commitment(
    store_slug: str, opportunity_key: str
) -> Optional[CommercialDecisionCommitment]:
    slug = str(store_slug or "").strip()[:191]
    key = str(opportunity_key or "").strip()[:255]
    if not slug or not key:
        return None
    ensure_commercial_decision_commitment_schema(db)
    return (
        db.session.query(CommercialDecisionCommitment)
        .filter(
            CommercialDecisionCommitment.store_slug == slug,
            CommercialDecisionCommitment.opportunity_key == key,
            CommercialDecisionCommitment.closed_at.is_(None),
        )
        .first()
    )


def list_open_commitments(store_slug: str) -> list[CommercialDecisionCommitment]:
    slug = str(store_slug or "").strip()[:191]
    if not slug:
        return []
    ensure_commercial_decision_commitment_schema(db)
    return (
        db.session.query(CommercialDecisionCommitment)
        .filter(
            CommercialDecisionCommitment.store_slug == slug,
            CommercialDecisionCommitment.closed_at.is_(None),
        )
        .all()
    )


def _parse_opportunity_key(opportunity_key: str) -> tuple[str, str]:
    # col:{family}:{reason}:{store}
    parts = str(opportunity_key or "").split(":")
    if len(parts) < 4 or parts[0] != "col":
        raise CommitmentError("invalid_opportunity_key", http_status=400)
    family = parts[1][:64]
    reason = parts[2][:128]
    if not family or not reason:
        raise CommitmentError("invalid_opportunity_key", http_status=400)
    return family, reason


def _find_col_opportunity(
    col_pkg: Mapping[str, Any] | None, opportunity_key: str
) -> Optional[dict[str, Any]]:
    if not isinstance(col_pkg, Mapping):
        return None
    key = str(opportunity_key)
    primary = col_pkg.get("primary")
    if isinstance(primary, Mapping) and str(primary.get("opportunity_id") or "") == key:
        return dict(primary)
    secs = col_pkg.get("secondaries") or []
    if isinstance(secs, list):
        for s in secs:
            if isinstance(s, Mapping) and str(s.get("opportunity_id") or "") == key:
                return dict(s)
    return None


def _row_public(row: CommercialDecisionCommitment, *, now: Optional[datetime] = None) -> dict[str, Any]:
    phase = derive_commitment_state(row, now=now)
    return {
        "commitment_id": row.id,
        "store_slug": row.store_slug,
        "opportunity_key": row.opportunity_key,
        "opportunity_family": row.opportunity_family,
        "opportunity_reason": row.opportunity_reason,
        "phase": phase,
        "console_mode": PHASE_TO_CONSOLE_MODE.get(phase or "", None),
        "action_chosen_at": row.action_chosen_at.isoformat() if row.action_chosen_at else None,
        "measurement_started_at": (
            row.measurement_started_at.isoformat() if row.measurement_started_at else None
        ),
        "measurement_due_at": (
            row.measurement_due_at.isoformat() if row.measurement_due_at else None
        ),
        "measurement_start_authority": row.measurement_start_authority,
        "metric_key": row.metric_key,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        "close_reason": row.close_reason,
        "layer_version": LAYER_VERSION,
    }


def accept_commitment(
    *,
    store_slug: str,
    opportunity_key: str,
    col_package: Mapping[str, Any] | None,
    action_summary: str = "",
    proposed_metric_key: Optional[str] = None,
) -> dict[str, Any]:
    """READY → ACTION_CHOSEN. Does NOT start measurement."""
    slug = str(store_slug or "").strip()[:191]
    key = str(opportunity_key or "").strip()[:255]
    if not slug or not key:
        raise CommitmentError("missing_store_or_key", http_status=400)

    existing = get_active_commitment(slug, key)
    if existing is not None:
        return {"ok": True, "idempotent": True, "commitment": _row_public(existing)}

    opp = _find_col_opportunity(col_package, key)
    if opp is None:
        raise CommitmentError("stale_opportunity", http_status=409)

    family, reason = _parse_opportunity_key(key)
    if str(opp.get("family") or "") and str(opp.get("family")) != family:
        family = str(opp.get("family"))[:64]

    now = _utcnow()
    counts = None
    ev = opp.get("evidence") if isinstance(opp.get("evidence"), Mapping) else {}
    if isinstance(ev, Mapping) and isinstance(ev.get("counts"), Mapping):
        counts = ev.get("counts")

    try:
        decision_json = build_decision_snapshot(
            opportunity_key=key,
            opportunity_family=family,
            opportunity_reason=reason,
            truth_class=str(opp.get("truth_class") or ""),
            accepted_at=now.isoformat(),
            action_code=str(opp.get("family") or family)[:64],
            proposed_metric_key=proposed_metric_key,
            signal_counts=counts,
        )
    except SnapshotContractError as exc:
        raise CommitmentError(str(exc), http_status=400) from exc

    summary = (action_summary or str(opp.get("action_ar") or "") or family)[:512]
    # Strip UI essay — keep short token-like summary
    if len(summary) > 200:
        summary = summary[:197] + "…"

    row = CommercialDecisionCommitment(
        id=str(uuid.uuid4()),
        store_slug=slug,
        opportunity_key=key,
        opportunity_family=family,
        opportunity_reason=reason,
        active_opportunity_key=key,
        action_chosen_at=now,
        action_summary=summary,
        decision_snapshot_json=decision_json,
        measurement_started_at=None,
        measurement_due_at=None,
        baseline_snapshot_json=None,
        created_at=now,
        updated_at=now,
        closed_at=None,
    )
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raced = get_active_commitment(slug, key)
        if raced is not None:
            return {"ok": True, "idempotent": True, "commitment": _row_public(raced)}
        raise CommitmentError("active_uniqueness_violation", http_status=409)

    return {"ok": True, "idempotent": False, "commitment": _row_public(row)}


def start_measurement(
    *,
    store_slug: str,
    commitment_id: str,
    authority: str,
    measurement_start_ref: str = "",
    metric_key: str,
    metric_value: Optional[float] = None,
    truth_class_at_start: str = "",
    recheck_condition: str = "",
    signal_counts: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    slug = str(store_slug or "").strip()[:191]
    cid = str(commitment_id or "").strip()
    auth = str(authority or "").strip()
    if not slug or not cid:
        raise CommitmentError("missing_store_or_id", http_status=400)
    if auth not in AUTHORITIES:
        raise CommitmentError("measurement_authority_refused", http_status=400)

    ensure_commercial_decision_commitment_schema(db)
    row = (
        db.session.query(CommercialDecisionCommitment)
        .filter(
            CommercialDecisionCommitment.id == cid,
            CommercialDecisionCommitment.store_slug == slug,
        )
        .first()
    )
    if row is None:
        raise CommitmentError("commitment_not_found", http_status=404)
    if row.closed_at is not None:
        raise CommitmentError("commitment_closed", http_status=409)

    if row.measurement_started_at is not None:
        return {"ok": True, "idempotent": True, "commitment": _row_public(row)}

    if auth == AUTHORITY_MERCHANT_EXECUTION_CONFIRM:
        if row.opportunity_family not in MERCHANT_CONFIRM_FAMILY_ALLOWLIST:
            raise CommitmentError("merchant_confirm_not_allowlisted", http_status=400)
    if auth == AUTHORITY_CARTFLOW_EXECUTION:
        if not str(measurement_start_ref or "").strip():
            raise CommitmentError("execution_ref_required", http_status=400)

    try:
        mk = validate_metric_key(metric_key)
    except SnapshotContractError as exc:
        raise CommitmentError(str(exc), http_status=400) from exc

    now = _utcnow()
    window = resolve_measurement_window(row.opportunity_family)
    due = now + window
    days = resolve_measurement_window_days(row.opportunity_family)

    try:
        baseline = build_baseline_snapshot(
            opportunity_key=row.opportunity_key,
            metric_key=mk,
            started_at=now.isoformat(),
            window_days=days,
            truth_class_at_start=truth_class_at_start,
            metric_value=metric_value,
            signal_counts=signal_counts,
        )
    except SnapshotContractError as exc:
        raise CommitmentError(str(exc), http_status=400) from exc

    recheck = str(recheck_condition or "").strip()[:2000]
    if not recheck:
        recheck = "recheck_when_window_elapsed"

    row.measurement_started_at = now
    row.measurement_due_at = due
    row.measurement_start_authority = auth
    row.measurement_start_ref = str(measurement_start_ref or "").strip()[:191] or None
    row.baseline_snapshot_json = baseline
    row.metric_key = mk
    row.baseline_metric_value = float(metric_value) if metric_value is not None else None
    row.recheck_condition_frozen = recheck
    row.updated_at = now
    db.session.commit()
    return {"ok": True, "idempotent": False, "commitment": _row_public(row)}


def close_commitment(
    *,
    store_slug: str,
    commitment_id: str,
    close_reason: str,
    actor: str = "merchant",
    close_note: str = "",
    superseded_by_id: Optional[str] = None,
) -> dict[str, Any]:
    slug = str(store_slug or "").strip()[:191]
    cid = str(commitment_id or "").strip()
    reason = str(close_reason or "").strip()
    if not slug or not cid:
        raise CommitmentError("missing_store_or_id", http_status=400)
    if reason in FORBIDDEN_CLOSE_REASONS or reason not in CLOSE_REASONS:
        raise CommitmentError("invalid_close_reason", http_status=400)
    if actor == "merchant" and reason not in CLOSE_REASONS_MERCHANT:
        raise CommitmentError("close_reason_not_merchant_allowed", http_status=403)
    if actor == "system" and reason not in CLOSE_REASONS_SYSTEM:
        raise CommitmentError("close_reason_not_system_allowed", http_status=403)

    ensure_commercial_decision_commitment_schema(db)
    row = (
        db.session.query(CommercialDecisionCommitment)
        .filter(
            CommercialDecisionCommitment.id == cid,
            CommercialDecisionCommitment.store_slug == slug,
        )
        .first()
    )
    if row is None:
        raise CommitmentError("commitment_not_found", http_status=404)

    if row.closed_at is not None:
        return {"ok": True, "idempotent": True, "commitment": _row_public(row)}

    now = _utcnow()
    row.closed_at = now
    row.close_reason = reason
    row.close_note = (close_note or "")[:200] or None
    row.active_opportunity_key = None
    if superseded_by_id:
        row.superseded_by_id = str(superseded_by_id)[:36]
    row.updated_at = now
    db.session.commit()
    return {"ok": True, "idempotent": False, "commitment": _row_public(row)}


__all__ = [
    "CommitmentError",
    "accept_commitment",
    "close_commitment",
    "derive_commitment_state",
    "get_active_commitment",
    "list_open_commitments",
    "start_measurement",
    "_row_public",
]
