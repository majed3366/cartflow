# -*- coding: utf-8 -*-
"""Surface Composition Foundation V1 — kill switch (default on)."""
from __future__ import annotations

import os

ENV_SURFACE_COMPOSITION_V1 = "CARTFLOW_SURFACE_COMPOSITION_V1"


def surface_composition_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_SURFACE_COMPOSITION_V1) or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


__all__ = [
    "ENV_SURFACE_COMPOSITION_V1",
    "surface_composition_v1_enabled",
]
