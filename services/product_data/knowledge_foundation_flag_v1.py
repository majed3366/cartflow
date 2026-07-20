# -*- coding: utf-8 -*-
"""Knowledge Foundation V1 — kill switch (default on)."""
from __future__ import annotations

import os

ENV_KNOWLEDGE_FOUNDATION_V1 = "CARTFLOW_KNOWLEDGE_FOUNDATION_V1"


def knowledge_foundation_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_KNOWLEDGE_FOUNDATION_V1) or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


__all__ = [
    "ENV_KNOWLEDGE_FOUNDATION_V1",
    "knowledge_foundation_v1_enabled",
]
