# -*- coding: utf-8 -*-
"""CIS → Knowledge Integration V1 — kill switch (default on)."""
from __future__ import annotations

import os

ENV_CIKNOW_V1 = "CARTFLOW_COMMERCE_INTELLIGENCE_KNOWLEDGE_INTEGRATION_V1"


def commerce_intelligence_knowledge_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_CIKNOW_V1) or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


__all__ = ["ENV_CIKNOW_V1", "commerce_intelligence_knowledge_v1_enabled"]
