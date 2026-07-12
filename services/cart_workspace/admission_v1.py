# -*- coding: utf-8 -*-
"""P2 Compiled Admission — R01–R20 binary Admit / Do Not Admit; no UI."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from services.cart_workspace.contracts_v1 import AdmissionResult, OwnershipState, _utc_now_iso
from services.cart_workspace.decision_identity_v1 import allocate_admission_id, build_evidence_fingerprint

ADMISSION_COMPILER_VERSION = "v1"


@dataclass
class AdmissionCandidate:
    """Compiled input predicates — no free-form constitutional reasoning."""

    store_slug: str
    recovery_key: str
    signal_class: str
    proof_class: str
    evidence_ids: list[str] = field(default_factory=list)
    proof_sufficient: bool = False
    automation_capable: bool = True
    human_gain_exceeds_cost: bool = False
    override_eligible: bool = False
    is_status_only: bool = False
    is_knowledge_only: bool = False
    is_refresh_same_fingerprint: bool = False
    is_duplicate_vip_while_active: bool = False
    journey_completed: bool = False
    journey_archived: bool = False
    decision_already_open: bool = False
    open_decision_same_fingerprint: bool = False
    fingerprint_seen_closed: bool = False
    expected_action: Optional[str] = None
    evidence_fingerprint: Optional[str] = None
    matrix_path_hint: str = "normal"

    def resolved_fingerprint(self) -> str:
        if self.evidence_fingerprint:
            return self.evidence_fingerprint
        path = "override" if self.override_eligible else (self.matrix_path_hint or "normal")
        return build_evidence_fingerprint(
            store_slug=self.store_slug,
            recovery_key=self.recovery_key,
            proof_class=self.proof_class or self.signal_class,
            evidence_ids=self.evidence_ids,
            matrix_path=path,
        )


def _reject(
    *,
    row: str,
    reason: str,
    fingerprint: str,
    ownership: OwnershipState,
    rejection_code: str,
    failed_gate: str,
) -> AdmissionResult:
    return AdmissionResult(
        outcome="do_not_admit",
        matrix_row_id=row,
        governing_reason=reason,
        evidence_fingerprint=fingerprint,
        admission_id=allocate_admission_id(),
        evaluated_at=_utc_now_iso(),
        override_path=False,
        ownership_posture={
            "execution_owner": ownership.execution_owner,
            "decision_owner": ownership.decision_owner,
            "override_mode": ownership.override_mode,
            "journey_phase": ownership.journey_phase,
        },
        failed_gate=failed_gate,
        rejection_code=rejection_code,
    )


def _admit(
    *,
    row: str,
    reason: str,
    fingerprint: str,
    ownership: OwnershipState,
    action: str,
    override_path: bool,
    admitting_gate: str,
    justification: str,
) -> AdmissionResult:
    return AdmissionResult(
        outcome="admit",
        matrix_row_id=row,
        governing_reason=reason,
        evidence_fingerprint=fingerprint,
        admission_id=allocate_admission_id(),
        evaluated_at=_utc_now_iso(),
        override_path=override_path,
        ownership_posture={
            "execution_owner": ownership.execution_owner,
            "decision_owner": ownership.decision_owner,
            "override_mode": ownership.override_mode,
            "journey_phase": ownership.journey_phase,
        },
        admitting_gate=admitting_gate,
        expected_merchant_action=action,
        human_gain_justification=justification,
    )


def evaluate_admission(candidate: AdmissionCandidate, ownership: OwnershipState) -> AdmissionResult:
    """
    Deterministic compiled evaluation aligned to Admission Matrix compile shape.
    Binary only. Fail closed.
    """
    fp = candidate.resolved_fingerprint()
    sig = (candidate.signal_class or "").strip().lower()

    # Illegal ownership posture (Customer/CS never owners — posture must be CF|M)
    if ownership.execution_owner not in {"cartflow", "merchant"}:
        return _reject(
            row="RJ-OWNERSHIP",
            reason="Illegal ownership posture",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-OWNERSHIP",
            failed_gate="B",
        )
    if ownership.decision_owner not in {"cartflow", "merchant"}:
        return _reject(
            row="RJ-OWNERSHIP",
            reason="Illegal ownership posture",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-OWNERSHIP",
            failed_gate="B",
        )

    # Terminal / history
    if candidate.journey_completed or ownership.journey_phase == "completed" or sig == "purchase_completed":
        return _reject(
            row="R11",
            reason="Already completed",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-COMPLETED",
            failed_gate="terminal",
        )
    if candidate.journey_archived or ownership.journey_phase == "archived" or sig == "archived":
        return _reject(
            row="R19",
            reason="History / archive surface — outside L2",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-HISTORY",
            failed_gate="AI-8",
        )

    # Duplicate / open Decision / same fingerprint refresh
    if candidate.decision_already_open or ownership.decision_owner == "merchant":
        if candidate.open_decision_same_fingerprint or candidate.is_refresh_same_fingerprint or sig == "merchant_inactive":
            return _reject(
                row="R14",
                reason="Duplicate admission; Decision already open",
                fingerprint=fp,
                ownership=ownership,
                rejection_code="RJ-DUPLICATE",
                failed_gate="stability",
            )

    if candidate.open_decision_same_fingerprint or candidate.is_refresh_same_fingerprint or sig == "refresh":
        return _reject(
            row="R17",
            reason="Duplicate admission / stability",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-DUPLICATE",
            failed_gate="stability",
        )

    if candidate.fingerprint_seen_closed and not candidate.proof_sufficient:
        # Same fingerprint after close without new evidence material — still reject
        return _reject(
            row="R17",
            reason="Duplicate admission / stability",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-DUPLICATE",
            failed_gate="AS-4",
        )

    # Override path
    if candidate.is_duplicate_vip_while_active or (
        ownership.override_mode == "active"
        and candidate.override_eligible
        and (candidate.decision_already_open or ownership.decision_owner == "merchant")
    ):
        return _reject(
            row="R08",
            reason="Duplicate / Override non-oscillation",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-OVERRIDE-DUP",
            failed_gate="F",
        )

    if candidate.override_eligible or ownership.override_mode == "active" and sig in {
        "vip_detect",
        "vip",
        "override",
    }:
        # Override Admission still requires eligibility proof
        if not candidate.proof_sufficient and not candidate.override_eligible:
            return _reject(
                row="R01",
                reason="Automation still owns; insufficient Proof",
                fingerprint=fp,
                ownership=ownership,
                rejection_code="RJ-EVIDENCE",
                failed_gate="A",
            )
        if candidate.override_eligible and candidate.proof_sufficient:
            action = candidate.expected_action or "override_decision_action"
            return _admit(
                row="R07",
                reason="Override Admission",
                fingerprint=fp,
                ownership=ownership,
                action=action,
                override_path=True,
                admitting_gate="F",
                justification="Override policy requires immediate Decision eligibility",
            )

    # Knowledge
    if candidate.is_knowledge_only or sig == "knowledge_claim":
        return _reject(
            row="R18",
            reason="Knowledge ≠ Escalation",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-KNOWLEDGE",
            failed_gate="pipeline",
        )

    # Status-only / noise classes
    if candidate.is_status_only or sig in {"message_sent", "status"}:
        return _reject(
            row="R16",
            reason="Operational noise",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-STATUS",
            failed_gate="AI-7",
        )

    if sig == "customer_inactive" or (sig == "silence" and not candidate.proof_sufficient):
        return _reject(
            row="R15",
            reason="Operational noise / Wait strategy",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-NOISE",
            failed_gate="C",
        )

    if not candidate.proof_sufficient:
        # Map weak hesitation / phone status
        if sig in {"hesitation", "idle_cart"}:
            return _reject(
                row="R01",
                reason="Automation still owns; insufficient Proof",
                fingerprint=fp,
                ownership=ownership,
                rejection_code="RJ-EVIDENCE",
                failed_gate="A",
            )
        if sig == "phone_missing":
            return _reject(
                row="R09",
                reason="Status ≠ Decision; automation owns",
                fingerprint=fp,
                ownership=ownership,
                rejection_code="RJ-STATUS",
                failed_gate="AI-7",
            )
        return _reject(
            row="RJ-UNCLASSIFIED",
            reason="No matrix row — fail closed",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-UNCLASSIFIED",
            failed_gate="AI-15",
        )

    # Automation still capable → reject (normal path)
    if candidate.automation_capable:
        if sig == "customer_reply":
            return _reject(
                row="R04",
                reason="Automation still capable",
                fingerprint=fp,
                ownership=ownership,
                rejection_code="RJ-AUTOMATION",
                failed_gate="C",
            )
        if sig == "provider_failure":
            return _reject(
                row="R12",
                reason="Operational noise / retry",
                fingerprint=fp,
                ownership=ownership,
                rejection_code="RJ-NOISE",
                failed_gate="C",
            )
        if sig in {"hesitation", "idle_cart"}:
            return _reject(
                row="R02",
                reason="Automation still capable",
                fingerprint=fp,
                ownership=ownership,
                rejection_code="RJ-AUTOMATION",
                failed_gate="C",
            )
        if sig == "phone_missing":
            return _reject(
                row="R09",
                reason="Status ≠ Decision; automation owns",
                fingerprint=fp,
                ownership=ownership,
                rejection_code="RJ-STATUS",
                failed_gate="C",
            )
        return _reject(
            row="R02",
            reason="Automation still capable",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-AUTOMATION",
            failed_gate="C",
        )

    # Automation not capable — need human gain > cost
    if not candidate.human_gain_exceeds_cost:
        return _reject(
            row="RJ-VALUE",
            reason="Low business value (Human Gain ≤ Attention Cost)",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-VALUE",
            failed_gate="D/E",
        )

    # Admit rows by signal class
    if sig in {"hesitation", "idle_cart"}:
        return _admit(
            row="R03",
            reason="Normal Admission",
            fingerprint=fp,
            ownership=ownership,
            action=candidate.expected_action or "approve_next_step",
            override_path=False,
            admitting_gate="D/E",
            justification="Human Gain exceeds Attention Cost; automation exhausted",
        )
    if sig in {"customer_question", "business_exception"}:
        return _admit(
            row="R05",
            reason="Human Gain justifies",
            fingerprint=fp,
            ownership=ownership,
            action=candidate.expected_action or "judgment_action",
            override_path=False,
            admitting_gate="D/E",
            justification="Business exception needs merchant judgment",
        )
    if sig in {"discount_request", "exception_request"}:
        return _admit(
            row="R06",
            reason="Business exception",
            fingerprint=fp,
            ownership=ownership,
            action=candidate.expected_action or "approve_or_deny_discount",
            override_path=False,
            admitting_gate="D/E",
            justification="Approve/deny required",
        )
    if sig == "phone_missing":
        return _admit(
            row="R10",
            reason="Human Gain (provide phone)",
            fingerprint=fp,
            ownership=ownership,
            action=candidate.expected_action or "provide_confirm_phone",
            override_path=False,
            admitting_gate="D/E",
            justification="Merchant must supply contact; automation blocked",
        )
    if sig == "provider_failure":
        return _admit(
            row="R13",
            reason="Automation exhausted",
            fingerprint=fp,
            ownership=ownership,
            action=candidate.expected_action or "recovery_action",
            override_path=False,
            admitting_gate="D/E",
            justification="Policy requires merchant decision after exhausted retries",
        )
    if sig == "reopen":
        # R20: reopen ≠ auto-Admit — fall through unclassified unless predicates already classified
        return _reject(
            row="R20",
            reason="Reopen ≠ auto-Admit; full pipeline required",
            fingerprint=fp,
            ownership=ownership,
            rejection_code="RJ-UNCLASSIFIED",
            failed_gate="AI-15",
        )

    return _reject(
        row="RJ-UNCLASSIFIED",
        reason="No matrix row — fail closed",
        fingerprint=fp,
        ownership=ownership,
        rejection_code="RJ-UNCLASSIFIED",
        failed_gate="AI-15",
    )


def candidate_from_dict(data: dict[str, Any]) -> AdmissionCandidate:
    return AdmissionCandidate(
        store_slug=str(data.get("store_slug") or ""),
        recovery_key=str(data.get("recovery_key") or ""),
        signal_class=str(data.get("signal_class") or ""),
        proof_class=str(data.get("proof_class") or data.get("signal_class") or ""),
        evidence_ids=list(data.get("evidence_ids") or []),
        proof_sufficient=bool(data.get("proof_sufficient", False)),
        automation_capable=bool(data.get("automation_capable", True)),
        human_gain_exceeds_cost=bool(data.get("human_gain_exceeds_cost", False)),
        override_eligible=bool(data.get("override_eligible", False)),
        is_status_only=bool(data.get("is_status_only", False)),
        is_knowledge_only=bool(data.get("is_knowledge_only", False)),
        is_refresh_same_fingerprint=bool(data.get("is_refresh_same_fingerprint", False)),
        is_duplicate_vip_while_active=bool(data.get("is_duplicate_vip_while_active", False)),
        journey_completed=bool(data.get("journey_completed", False)),
        journey_archived=bool(data.get("journey_archived", False)),
        decision_already_open=bool(data.get("decision_already_open", False)),
        open_decision_same_fingerprint=bool(data.get("open_decision_same_fingerprint", False)),
        fingerprint_seen_closed=bool(data.get("fingerprint_seen_closed", False)),
        expected_action=data.get("expected_action"),
        evidence_fingerprint=data.get("evidence_fingerprint"),
        matrix_path_hint=str(data.get("matrix_path_hint") or "normal"),
    )
