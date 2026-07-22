# -*- coding: utf-8 -*-
"""Merchant Experience Integration Foundation V1 — kill switch (default on)."""
from __future__ import annotations

import os

ENV_MERCHANT_EXPERIENCE_INTEGRATION_V1 = "CARTFLOW_MERCHANT_EXPERIENCE_INTEGRATION_V1"


def merchant_experience_integration_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_MERCHANT_EXPERIENCE_INTEGRATION_V1) or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


__all__ = [
    "ENV_MERCHANT_EXPERIENCE_INTEGRATION_V1",
    "merchant_experience_integration_v1_enabled",
]
