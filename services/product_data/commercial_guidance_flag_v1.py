# -*- coding: utf-8 -*-
"""Commercial Guidance Foundation V1 — kill switch (default on)."""
from __future__ import annotations

import os

ENV_COMMERCIAL_GUIDANCE_V1 = "CARTFLOW_COMMERCIAL_GUIDANCE_FOUNDATION_V1"


def commercial_guidance_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_COMMERCIAL_GUIDANCE_V1) or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


__all__ = [
    "ENV_COMMERCIAL_GUIDANCE_V1",
    "commercial_guidance_v1_enabled",
]
