# -*- coding: utf-8 -*-
"""P1 Ownership — sole writer of dual-axis ownership + Override mode + journey phase."""
from __future__ import annotations

import uuid
from typing import Any, Optional

from services.cart_workspace.contracts_v1 import (
    OwnershipState,
    OwnershipTransitionAudit,
    _utc_now_iso,
)

# Product-deferred transition codes (OQ-1 / OQ-2 / OQ-4) — hooks only.
DEFERRED_TRANSITIONS = frozenset({"T4", "T6", "T7", "T12"})

LEGAL_TRANSITIONS: dict[str, dict[str, Any]] = {
    "T1": {
        "axis": "decision",
        "gate": "decision_admission_normal",
        "to": {"decision_owner": "merchant"},
        "product_deferred": False,
    },
    "T2": {
        "axis": "decision",
        "gate": "decision_admission_override",
        "to": {"decision_owner": "merchant", "override_mode": "active"},
        "product_deferred": False,
    },
    "T3": {
        "axis": "decision",
        "gate": "decision_resolved_action",
        "to": {"decision_owner": "cartflow"},
        "product_deferred": False,
    },
    "T4": {
        "axis": "decision",
        "gate": "expiry_return_supersede",
        "to": {"decision_owner": "cartflow"},
        "product_deferred": True,
    },
    "T5": {
        "axis": "decision",
        "gate": "leave_l2",
        "to": {"decision_owner": "cartflow"},
        "product_deferred": False,
    },
    "T6": {
        "axis": "execution",
        "gate": "scoped_manual_handoff",
        "to": {"execution_owner": "merchant"},
        "product_deferred": True,
    },
    "T7": {
        "axis": "execution",
        "gate": "manual_scope_closed",
        "to": {"execution_owner": "cartflow"},
        "product_deferred": True,
    },
    "T8": {
        "axis": "override_mode",
        "gate": "priority_override_detect",
        "to": {"override_mode": "active"},
        "product_deferred": False,
    },
    "T9": {
        "axis": "override_mode",
        "gate": "priority_override_clear",
        "to": {"override_mode": "inactive"},
        "product_deferred": False,
    },
    "T10": {
        "axis": "journey_phase",
        "gate": "completion",
        "to": {"journey_phase": "completed", "decision_owner": "cartflow"},
        "product_deferred": False,
    },
    "T11": {
        "axis": "journey_phase",
        "gate": "archive",
        "to": {"journey_phase": "archived", "decision_owner": "cartflow"},
        "product_deferred": False,
    },
    "T12": {
        "axis": "journey_phase",
        "gate": "governed_reopen",
        "to": {
            "journey_phase": "active",
            "execution_owner": "cartflow",
            "decision_owner": "cartflow",
        },
        "product_deferred": True,
    },
}


class OwnershipError(ValueError):
    pass


def default_ownership(store_slug: str, recovery_key: str) -> OwnershipState:
    return OwnershipState(store_slug=store_slug, recovery_key=recovery_key)


def apply_transition(
    state: OwnershipState,
    *,
    transition_code: str,
    evidence_refs: Optional[list[str]] = None,
    correlation_id: Optional[str] = None,
    force: bool = False,
) -> tuple[OwnershipState, OwnershipTransitionAudit, bool]:
    """
    Apply a legal T* transition.

    Returns (new_state, audit, changed).
    Idempotent no-ops return changed=False.
    Deferred transitions raise unless force=True (tests only — never invent product policy).
    """
    code = (transition_code or "").strip().upper()
    spec = LEGAL_TRANSITIONS.get(code)
    if spec is None:
        raise OwnershipError(f"unknown_transition:{code}")

    if spec.get("product_deferred") and not force:
        raise OwnershipError(f"product_deferred_transition:{code}")

    evidence_refs = list(evidence_refs or [])
    correlation_id = correlation_id or str(uuid.uuid4())
    from_values = {
        "execution_owner": state.execution_owner,
        "decision_owner": state.decision_owner,
        "override_mode": state.override_mode,
        "journey_phase": state.journey_phase,
    }

    # Anti-oscillation / idempotency
    if code == "T8" and state.override_mode == "active":
        audit = _audit(state, code, spec, from_values, from_values, evidence_refs, correlation_id, changed=False)
        return state, audit, False

    if code == "T9" and state.override_mode == "inactive":
        audit = _audit(state, code, spec, from_values, from_values, evidence_refs, correlation_id, changed=False)
        return state, audit, False

    if code == "T1" and state.decision_owner == "merchant" and state.override_mode != "active":
        # Already merchant decision owner on normal path — no second transfer without close
        audit = _audit(state, code, spec, from_values, from_values, evidence_refs, correlation_id, changed=False)
        return state, audit, False

    if code == "T2" and state.decision_owner == "merchant" and state.override_mode == "active":
        audit = _audit(state, code, spec, from_values, from_values, evidence_refs, correlation_id, changed=False)
        return state, audit, False

    if code in {"T3", "T5"} and state.decision_owner == "cartflow":
        audit = _audit(state, code, spec, from_values, from_values, evidence_refs, correlation_id, changed=False)
        return state, audit, False

    new_state = OwnershipState(
        store_slug=state.store_slug,
        recovery_key=state.recovery_key,
        execution_owner=state.execution_owner,
        decision_owner=state.decision_owner,
        override_mode=state.override_mode,
        journey_phase=state.journey_phase,
        updated_at=_utc_now_iso(),
        last_transition_id=None,
        source_refs=list(state.source_refs),
    )
    for k, v in (spec.get("to") or {}).items():
        setattr(new_state, k, v)

    # T2 ensures override active (Override Admission)
    if code == "T2":
        new_state.override_mode = "active"
        new_state.decision_owner = "merchant"

    # T10/T11 close decision ownership to cartflow
    if code in {"T10", "T11"}:
        new_state.decision_owner = "cartflow"

    to_values = {
        "execution_owner": new_state.execution_owner,
        "decision_owner": new_state.decision_owner,
        "override_mode": new_state.override_mode,
        "journey_phase": new_state.journey_phase,
    }
    if to_values == from_values:
        audit = _audit(state, code, spec, from_values, to_values, evidence_refs, correlation_id, changed=False)
        return state, audit, False

    tid = str(uuid.uuid4())
    new_state.last_transition_id = tid
    new_state.source_refs = list(dict.fromkeys([*new_state.source_refs, *evidence_refs]))
    audit = OwnershipTransitionAudit(
        transition_id=tid,
        transition_code=code,
        store_slug=new_state.store_slug,
        recovery_key=new_state.recovery_key,
        axis=str(spec["axis"]),
        from_values=from_values,
        to_values=to_values,
        gate=str(spec["gate"]),
        evidence_refs=evidence_refs,
        at=new_state.updated_at,
        correlation_id=correlation_id,
        product_deferred=bool(spec.get("product_deferred")),
    )
    return new_state, audit, True


def _audit(
    state: OwnershipState,
    code: str,
    spec: dict[str, Any],
    from_values: dict[str, str],
    to_values: dict[str, str],
    evidence_refs: list[str],
    correlation_id: str,
    *,
    changed: bool,
) -> OwnershipTransitionAudit:
    return OwnershipTransitionAudit(
        transition_id=str(uuid.uuid4()) if not changed else (state.last_transition_id or str(uuid.uuid4())),
        transition_code=code,
        store_slug=state.store_slug,
        recovery_key=state.recovery_key,
        axis=str(spec["axis"]),
        from_values=from_values,
        to_values=to_values,
        gate=str(spec["gate"]) + ("" if changed else ":noop"),
        evidence_refs=evidence_refs,
        at=_utc_now_iso(),
        correlation_id=correlation_id,
        product_deferred=bool(spec.get("product_deferred")),
    )
