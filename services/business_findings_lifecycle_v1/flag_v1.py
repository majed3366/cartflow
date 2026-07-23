# -*- coding: utf-8 -*-
"""BFL V1 feature flag — default on."""
from __future__ import annotations

import os

ENV_BUSINESS_FINDINGS_LIFECYCLE_V1 = "CARTFLOW_BUSINESS_FINDINGS_LIFECYCLE_V1"


def business_findings_lifecycle_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_BUSINESS_FINDINGS_LIFECYCLE_V1) or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


__all__ = [
    "ENV_BUSINESS_FINDINGS_LIFECYCLE_V1",
    "business_findings_lifecycle_v1_enabled",
]
