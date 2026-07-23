# -*- coding: utf-8 -*-
"""Feature flag: Knowledge → Commercial Guidance integration (cguide_v1)."""
from __future__ import annotations

import os

# Distinct from CARTFLOW_COMMERCIAL_GUIDANCE_FOUNDATION_V1 (eligibility → cgf_v1).
ENV_COMMERCIAL_GUIDANCE_KNOWLEDGE_V1 = "CARTFLOW_COMMERCIAL_GUIDANCE_V1"


def commercial_guidance_knowledge_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_COMMERCIAL_GUIDANCE_KNOWLEDGE_V1) or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


__all__ = [
    "ENV_COMMERCIAL_GUIDANCE_KNOWLEDGE_V1",
    "commercial_guidance_knowledge_v1_enabled",
]
