# -*- coding: utf-8 -*-
"""Diagnostic Reasoning V1 flags — default OFF (opt-in)."""
from __future__ import annotations

import os
from typing import Mapping

FLAG_DIAGNOSTIC_REASONING_V1 = "CARTFLOW_DIAGNOSTIC_REASONING_V1"
FLAG_DIAGNOSTIC_REASONING_EXECUTE = "CARTFLOW_DIAGNOSTIC_REASONING_EXECUTE"

_TRUE = frozenset({"1", "true", "yes", "on"})


def _enabled(name: str, *, environ: Mapping[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    return str(env.get(name, "") or "").strip().lower() in _TRUE


def diagnostic_reasoning_v1_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    return _enabled(FLAG_DIAGNOSTIC_REASONING_V1, environ=environ)


def diagnostic_reasoning_execute_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    return _enabled(FLAG_DIAGNOSTIC_REASONING_EXECUTE, environ=environ)


__all__ = [
    "FLAG_DIAGNOSTIC_REASONING_EXECUTE",
    "FLAG_DIAGNOSTIC_REASONING_V1",
    "diagnostic_reasoning_execute_enabled",
    "diagnostic_reasoning_v1_enabled",
]
