# -*- coding: utf-8 -*-
"""
Evidence Truth feature-flag skeleton (Blueprint WP-ET-00 / Stage 0–1).

All flags default OFF. No production consumer reads these flags yet.
WP-ET-00 does not change runtime behaviour when flags are toggled —
later packages wire consumers behind these names.
"""
from __future__ import annotations

import os
from typing import Mapping

# Flag names (stable).
# WP-ET-03 wires OBSERVATION_DUAL_WRITE (default OFF).
# WP-ET-05…08 wire EVIDENCE_DUAL_WRITE for Stage-3/4/5 family publishers (default OFF).
# WP-ET-09 wires BUNDLE_COMPOSER_SHADOW (default OFF). CONSUME remains unwired.
# WP-ET-10 wires KNOWLEDGE_COMPOSER_SHADOW (default OFF). INPUT/Findings remain unwired.
# FLAG_VISITOR_BUNDLE_FIELDS remains OFF (visitor Bundle fields unauthorized).
FLAG_OBSERVATION_DUAL_WRITE = "CARTFLOW_EVIDENCE_OBSERVATION_DUAL_WRITE"
FLAG_EVIDENCE_DUAL_WRITE = "CARTFLOW_EVIDENCE_DUAL_WRITE"
FLAG_BUNDLE_COMPOSER_SHADOW = "CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW"
FLAG_BUNDLE_COMPOSER_CONSUME = "CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_CONSUME"
FLAG_KNOWLEDGE_COMPOSER_SHADOW = "CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_SHADOW"
FLAG_KNOWLEDGE_COMPOSER_INPUT = "CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_INPUT"
FLAG_FINDINGS_COMPOSER_INPUT = "CARTFLOW_EVIDENCE_FINDINGS_COMPOSER_INPUT"
FLAG_VISITOR_BUNDLE_FIELDS = "CARTFLOW_EVIDENCE_VISITOR_BUNDLE_FIELDS"

EVIDENCE_TRUTH_FLAGS_V1: tuple[str, ...] = (
    FLAG_OBSERVATION_DUAL_WRITE,
    FLAG_EVIDENCE_DUAL_WRITE,
    FLAG_BUNDLE_COMPOSER_SHADOW,
    FLAG_BUNDLE_COMPOSER_CONSUME,
    FLAG_KNOWLEDGE_COMPOSER_SHADOW,
    FLAG_KNOWLEDGE_COMPOSER_INPUT,
    FLAG_FINDINGS_COMPOSER_INPUT,
    FLAG_VISITOR_BUNDLE_FIELDS,
)

_TRUE = frozenset({"1", "true", "yes", "on"})


def evidence_truth_flag_enabled(flag_name: str, *, environ: Mapping[str, str] | None = None) -> bool:
    """
    Return whether a declared Evidence Truth flag is enabled.

    Unknown flag names return False (fail closed). Default is always False
    when unset — production behaviour unchanged.
    """
    name = (flag_name or "").strip()
    if name not in EVIDENCE_TRUTH_FLAGS_V1:
        return False
    env = environ if environ is not None else os.environ
    raw = str(env.get(name, "") or "").strip().lower()
    return raw in _TRUE


def evidence_truth_flags_snapshot(*, environ: Mapping[str, str] | None = None) -> dict[str, bool]:
    """Read-only snapshot of all Evidence Truth flags (defaults False)."""
    return {name: evidence_truth_flag_enabled(name, environ=environ) for name in EVIDENCE_TRUTH_FLAGS_V1}
