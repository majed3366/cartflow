# -*- coding: utf-8 -*-
"""Product Evidence Assembly Foundation V1 — kill switch (default on)."""
from __future__ import annotations

import os

ENV_PRODUCT_EVIDENCE_ASSEMBLY_V1 = "CARTFLOW_PRODUCT_EVIDENCE_ASSEMBLY_V1"


def product_evidence_assembly_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_PRODUCT_EVIDENCE_ASSEMBLY_V1) or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


__all__ = [
    "ENV_PRODUCT_EVIDENCE_ASSEMBLY_V1",
    "product_evidence_assembly_v1_enabled",
]
