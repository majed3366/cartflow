# -*- coding: utf-8 -*-
"""
Merchant Pulse V1 — feature flag.

Default off. Set CARTFLOW_MERCHANT_PULSE_V1=1 to attach MerchantPulseV1
on dashboard summary. Rollback = set flag to 0.
"""
from __future__ import annotations

import os

ENV_MERCHANT_PULSE_V1 = "CARTFLOW_MERCHANT_PULSE_V1"


def merchant_pulse_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_MERCHANT_PULSE_V1) or "0").strip().lower()
    if not raw:
        return False
    return raw in ("1", "true", "yes", "on")


__all__ = ["ENV_MERCHANT_PULSE_V1", "merchant_pulse_v1_enabled"]
