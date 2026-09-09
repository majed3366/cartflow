# -*- coding: utf-8 -*-
"""Product Exposure V1 — ingest, persist, rebuild, retention (platform-neutral core)."""
from __future__ import annotations

from services.product_exposure_v1.constants_v1 import (
    PAGE_CONTEXT_PDP,
    SOURCE_STOREFRONT_WIDGET_V1,
    TRUTH_VERSION_EXPOSURE_V1,
)
from services.product_exposure_v1.ingest_v1 import ingest_product_viewed
from services.product_exposure_v1.metrics_v1 import exposure_metrics_snapshot
from services.product_exposure_v1.rebuild_v1 import rebuild_daily_facts
from services.product_exposure_v1.retention_v1 import (
    exposure_retention_enabled,
    run_exposure_retention_tick,
)

__all__ = [
    "PAGE_CONTEXT_PDP",
    "SOURCE_STOREFRONT_WIDGET_V1",
    "TRUTH_VERSION_EXPOSURE_V1",
    "exposure_metrics_snapshot",
    "exposure_retention_enabled",
    "ingest_product_viewed",
    "rebuild_daily_facts",
    "run_exposure_retention_tick",
]
