# -*- coding: utf-8 -*-
"""Commerce Intelligence Foundation V1 — Home consumes; Home never computes."""

from services.commerce_intelligence.contract_v1 import (
    FOUNDATION_VERSION,
    canonical_record_v1,
)
from services.commerce_intelligence.engine_v1 import (
    run_commerce_intelligence_foundation_v1,
)

__all__ = [
    "FOUNDATION_VERSION",
    "canonical_record_v1",
    "run_commerce_intelligence_foundation_v1",
]
