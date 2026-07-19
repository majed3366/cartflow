# -*- coding: utf-8 -*-
"""
Product Signal Collection V1 — feature flag.

Default **on**. Set CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1=0 to disable writers.
Collection never affects merchant UI; kill switch is for ops safety only.
"""
from __future__ import annotations

import os

ENV_PRODUCT_SIGNAL_COLLECTION_V1 = "CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1"


def product_signal_collection_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_PRODUCT_SIGNAL_COLLECTION_V1) or "1").strip().lower()
    if not raw:
        return True
    return raw not in ("0", "false", "no", "off")


__all__ = [
    "ENV_PRODUCT_SIGNAL_COLLECTION_V1",
    "product_signal_collection_v1_enabled",
]
