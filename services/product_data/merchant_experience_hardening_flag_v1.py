# -*- coding: utf-8 -*-
"""MEH V1 — Merchant Experience Hardening feature flag."""
from __future__ import annotations

import os

ENV_MERCHANT_EXPERIENCE_HARDENING_V1 = "CARTFLOW_MERCHANT_EXPERIENCE_HARDENING_V1"


def merchant_experience_hardening_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_MERCHANT_EXPERIENCE_HARDENING_V1) or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


__all__ = [
    "ENV_MERCHANT_EXPERIENCE_HARDENING_V1",
    "merchant_experience_hardening_v1_enabled",
]
