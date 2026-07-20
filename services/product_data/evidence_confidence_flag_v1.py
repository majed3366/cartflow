# -*- coding: utf-8 -*-
"""Evidence Confidence Foundation V1 — kill switch (default on)."""
from __future__ import annotations

import os

ENV_EVIDENCE_CONFIDENCE_V1 = "CARTFLOW_EVIDENCE_CONFIDENCE_V1"


def evidence_confidence_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_EVIDENCE_CONFIDENCE_V1) or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


__all__ = [
    "ENV_EVIDENCE_CONFIDENCE_V1",
    "evidence_confidence_v1_enabled",
]
