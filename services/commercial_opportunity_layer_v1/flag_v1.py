# -*- coding: utf-8 -*-
"""Commercial Opportunity Layer V1 — feature flag (default OFF)."""
from __future__ import annotations

import os
from typing import Mapping

ENV_COMMERCIAL_OPPORTUNITY_LAYER_V1 = "CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def commercial_opportunity_layer_v1_enabled(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Fail-closed: unset / empty / false → OFF."""
    src = environ if environ is not None else os.environ
    raw = str(src.get(ENV_COMMERCIAL_OPPORTUNITY_LAYER_V1) or "").strip().lower()
    return raw in _TRUTHY


__all__ = [
    "ENV_COMMERCIAL_OPPORTUNITY_LAYER_V1",
    "commercial_opportunity_layer_v1_enabled",
]
