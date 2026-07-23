# -*- coding: utf-8 -*-
"""
Evidence Truth acceptance gates A–G — declarations only (Blueprint §9).

WP-ET-00 does not execute gates, BFSV, or Reality Validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EvidenceTruthGate:
    gate_id: str
    name: str
    proves: str
    required_before: str
    execution_authorized: bool = False


EVIDENCE_TRUTH_GATES_V1: dict[str, EvidenceTruthGate] = {
    "A": EvidenceTruthGate(
        gate_id="A",
        name="Evidence accounting",
        proves="Raw→Observation→Evidence counts reconcile; rejects audited; no silent loss",
        required_before="Any consumer flag on",
    ),
    "B": EvidenceTruthGate(
        gate_id="B",
        name="Visitor Truth",
        proves="Visitor Authority sole owner; carts never proxy; Unavailable honest when no channel",
        required_before="Visitor Bundle fields enabled",
    ),
    "C": EvidenceTruthGate(
        gate_id="C",
        name="EvidenceBundle parity",
        proves="Composer ≡ legacy where legacy was honest; never more certain without Ready",
        required_before="Findings/KL switch",
    ),
    "D": EvidenceTruthGate(
        gate_id="D",
        name="Knowledge parity",
        proves="Same claims/confidence class under Composer input; BK-2 holds",
        required_before="Declaring Knowledge migration done",
    ),
    "E": EvidenceTruthGate(
        gate_id="E",
        name="Business Finding parity",
        proves="Deterministic findings match fixtures + KF-3; Review Lab stable",
        required_before="Declaring Findings migration done",
    ),
    "F": EvidenceTruthGate(
        gate_id="F",
        name="BFSV Experiment 1 replay",
        proves="Persisted signals produce governed Evidence and Bundle slices without composition gap",
        required_before="Full pipeline acceptance",
        execution_authorized=False,
    ),
    "G": EvidenceTruthGate(
        gate_id="G",
        name="Reality Validation",
        proves="Sim/production-class walkthrough under MQIC+QTC+Evidence",
        required_before='Production "Evidence Truth complete" claim',
        execution_authorized=False,
    ),
}


def get_evidence_truth_gate(gate_id: str) -> Optional[EvidenceTruthGate]:
    return EVIDENCE_TRUTH_GATES_V1.get((gate_id or "").strip().upper())


def list_evidence_truth_gates() -> list[EvidenceTruthGate]:
    return [EVIDENCE_TRUTH_GATES_V1[k] for k in sorted(EVIDENCE_TRUTH_GATES_V1)]
