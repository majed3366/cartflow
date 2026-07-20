# -*- coding: utf-8 -*-
"""Product Metrics Foundation V1 — kill switch (default on)."""
from __future__ import annotations

import os

ENV_PRODUCT_METRICS_FOUNDATION_V1 = "CARTFLOW_PRODUCT_METRICS_FOUNDATION_V1"


def product_metrics_foundation_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_PRODUCT_METRICS_FOUNDATION_V1) or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


__all__ = [
    "ENV_PRODUCT_METRICS_FOUNDATION_V1",
    "product_metrics_foundation_v1_enabled",
]
