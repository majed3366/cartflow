# -*- coding: utf-8 -*-
"""
WP-ET-10.6 materialization execution flags (default OFF).

CARTFLOW_EXECUTIVE_KNOWLEDGE_PREVIEW remains a read/display gate only.
"""
from __future__ import annotations

import os
from typing import Mapping

FLAG_KNOWLEDGE_MATERIALIZATION_V1 = "CARTFLOW_EVIDENCE_KNOWLEDGE_MATERIALIZATION_V1"
FLAG_KNOWLEDGE_MATERIALIZATION_EXECUTE = (
    "CARTFLOW_EVIDENCE_KNOWLEDGE_MATERIALIZATION_EXECUTE"
)

_TRUE = frozenset({"1", "true", "yes", "on"})


def _enabled(name: str, *, environ: Mapping[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    raw = str(env.get(name, "") or "").strip().lower()
    return raw in _TRUE


def knowledge_materialization_v1_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    """Master gate — dry-run and execute both require this ON (or force in tests)."""
    return _enabled(FLAG_KNOWLEDGE_MATERIALIZATION_V1, environ=environ)


def knowledge_materialization_execute_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    """Mutation gate — EXECUTE mode additionally requires this ON."""
    return _enabled(FLAG_KNOWLEDGE_MATERIALIZATION_EXECUTE, environ=environ)


__all__ = [
    "FLAG_KNOWLEDGE_MATERIALIZATION_EXECUTE",
    "FLAG_KNOWLEDGE_MATERIALIZATION_V1",
    "knowledge_materialization_execute_enabled",
    "knowledge_materialization_v1_enabled",
]
