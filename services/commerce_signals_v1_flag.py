# -*- coding: utf-8 -*-
"""
Commerce Signals V1 — feature flag.

Default off. Set CARTFLOW_COMMERCE_SIGNALS_V1=1 to enable
read-only signal projection (debug/test only).
"""
from __future__ import annotations

import os

ENV_COMMERCE_SIGNALS_V1 = "CARTFLOW_COMMERCE_SIGNALS_V1"


def commerce_signals_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_COMMERCE_SIGNALS_V1) or "0").strip().lower()
    if not raw:
        return False
    return raw in ("1", "true", "yes", "on")


__all__ = ["ENV_COMMERCE_SIGNALS_V1", "commerce_signals_v1_enabled"]
