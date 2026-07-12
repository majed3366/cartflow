# -*- coding: utf-8 -*-
"""Cart Workspace contracts v1 — shared shapes only; no business rules."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

CONTRACT_VERSION = "v1"

Owner = Literal["cartflow", "merchant"]
OverrideMode = Literal["inactive", "active"]
JourneyPhase = Literal["active", "completed", "archived"]
DecisionClass = Literal["normal", "override"]
DecisionStatus = Literal["open", "resolving", "closed"]
AdmitOutcome = Literal["admit", "do_not_admit"]
Freshness = Literal["final", "revalidating", "uncertain", "degraded"]


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class OwnershipState:
    store_slug: str
    recovery_key: str
    execution_owner: Owner = "cartflow"
    decision_owner: Owner = "cartflow"
    override_mode: OverrideMode = "inactive"
    journey_phase: JourneyPhase = "active"
    updated_at: str = field(default_factory=_utc_now_iso)
    last_transition_id: Optional[str] = None
    source_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdmissionResult:
    outcome: AdmitOutcome
    matrix_row_id: str
    governing_reason: str
    evidence_fingerprint: str
    admission_id: str
    evaluated_at: str
    override_path: bool
    ownership_posture: dict[str, str]
    failed_gate: Optional[str] = None
    admitting_gate: Optional[str] = None
    rejection_code: Optional[str] = None
    human_gain_justification: Optional[str] = None
    expected_merchant_action: Optional[str] = None
    contract_version: str = CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionExplanation:
    why_here: str
    cartflow_did: str
    why_stopped: str
    expected_after: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionRecord:
    decision_id: str
    recovery_key: str
    store_slug: str
    admission_id: str
    admission_rule_id: str
    governing_reason: str
    execution_owner: Owner
    decision_owner: Owner
    override_mode: OverrideMode
    decision_class: DecisionClass
    required_action: str
    explanation: DecisionExplanation
    evidence_refs: list[str]
    evidence_fingerprint: str
    admitted_at: str
    status: DecisionStatus = "open"
    resolved_at: Optional[str] = None
    projection_version: Optional[int] = None
    order_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class ZoneSummary:
    visible: bool
    kind: str = "reassurance"
    summary: str = ""
    active_recovery_indicator: Optional[bool] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CompletedOutcomeRollup:
    window: str
    completed_count: int
    recent_items: list[dict[str, Any]]
    rollup_version: int
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OperationalHealthException:
    exception_id: str
    merchant_actionable: bool
    summary: str
    severity: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkspaceProjection:
    store_slug: str
    projection_id: str
    projection_version: int
    projection_fingerprint: str
    built_at: str
    freshness: Freshness
    workspace_phase: str
    zone_a: list[dict[str, Any]]
    zone_b: list[dict[str, Any]]
    zone_c: dict[str, Any]
    zone_d: dict[str, Any]
    zone_e: Optional[dict[str, Any]]
    quiet: bool
    attention_focus_decision_id: Optional[str] = None
    last_good_retained: bool = False
    contract_version: str = CONTRACT_VERSION
    zone_labels: Optional[dict[str, str]] = None
    mission_question: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OwnershipTransitionAudit:
    transition_id: str
    transition_code: str
    store_slug: str
    recovery_key: str
    axis: str
    from_values: dict[str, str]
    to_values: dict[str, str]
    gate: str
    evidence_refs: list[str]
    at: str
    correlation_id: str
    product_deferred: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
