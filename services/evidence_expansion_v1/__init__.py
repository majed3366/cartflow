# -*- coding: utf-8 -*-
"""Evidence Expansion Framework V1 — internal Evidence Gap registry."""
from __future__ import annotations

from services.evidence_expansion_v1.flag_v1 import (
    FLAG_EVIDENCE_EXPANSION_EXECUTE,
    FLAG_EVIDENCE_EXPANSION_V1,
    evidence_expansion_execute_enabled,
    evidence_expansion_v1_enabled,
)
from services.evidence_expansion_v1.orchestrator_v1 import (
    register_evidence_gaps_from_diagnostics_v1,
)

__all__ = [
    "FLAG_EVIDENCE_EXPANSION_EXECUTE",
    "FLAG_EVIDENCE_EXPANSION_V1",
    "evidence_expansion_execute_enabled",
    "evidence_expansion_v1_enabled",
    "register_evidence_gaps_from_diagnostics_v1",
]
