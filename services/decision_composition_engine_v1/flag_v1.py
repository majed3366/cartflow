# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from typing import Mapping

ENV_DECISION_COMPOSITION_ENGINE_V1 = "CARTFLOW_DECISION_COMPOSITION_ENGINE_V1"


def decision_composition_engine_v1_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    """Default ON. Set 0/false/off to fall back to Gate 2A enrich path."""
    env = environ if environ is not None else os.environ
    raw = str(env.get(ENV_DECISION_COMPOSITION_ENGINE_V1, "1") or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}
