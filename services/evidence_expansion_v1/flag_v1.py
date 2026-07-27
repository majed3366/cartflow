# -*- coding: utf-8 -*-
"""Evidence Expansion V1 flags — default OFF (opt-in persist)."""
from __future__ import annotations

import os
from typing import Mapping

FLAG_EVIDENCE_EXPANSION_V1 = "CARTFLOW_EVIDENCE_EXPANSION_V1"
FLAG_EVIDENCE_EXPANSION_EXECUTE = "CARTFLOW_EVIDENCE_EXPANSION_EXECUTE"

_TRUE = frozenset({"1", "true", "yes", "on"})


def _enabled(name: str, *, environ: Mapping[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    return str(env.get(name, "") or "").strip().lower() in _TRUE


def evidence_expansion_v1_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    return _enabled(FLAG_EVIDENCE_EXPANSION_V1, environ=environ)


def evidence_expansion_execute_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    return _enabled(FLAG_EVIDENCE_EXPANSION_EXECUTE, environ=environ)


__all__ = [
    "FLAG_EVIDENCE_EXPANSION_EXECUTE",
    "FLAG_EVIDENCE_EXPANSION_V1",
    "evidence_expansion_execute_enabled",
    "evidence_expansion_v1_enabled",
]
