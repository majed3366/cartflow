# -*- coding: utf-8 -*-
"""Commerce Intelligence Synthesis Foundation V1 — kill switch (default on)."""
from __future__ import annotations

import os

ENV_COMMERCE_INTELLIGENCE_SYNTHESIS_V1 = "CARTFLOW_COMMERCE_INTELLIGENCE_SYNTHESIS_V1"


def commerce_intelligence_synthesis_v1_enabled() -> bool:
    raw = (
        os.environ.get(ENV_COMMERCE_INTELLIGENCE_SYNTHESIS_V1) or "1"
    ).strip().lower()
    return raw not in {"0", "false", "no", "off"}


__all__ = [
    "ENV_COMMERCE_INTELLIGENCE_SYNTHESIS_V1",
    "commerce_intelligence_synthesis_v1_enabled",
]
