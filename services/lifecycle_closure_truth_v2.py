# -*- coding: utf-8 -*-
"""Backward-compatible re-exports — see lifecycle_closure_records_v1."""
from __future__ import annotations

from services.lifecycle_closure_records_v1 import (
    CANONICAL_CLOSURE_STATUSES,
    CLOSURE_CANCELLED,
    CLOSURE_CUSTOMER_REPLIED,
    CLOSURE_FAILED,
    CLOSURE_PURCHASE_COMPLETED,
    CLOSURE_REPLIED,
    CLOSURE_RETURNED_TO_SITE,
    get_durable_closure,
    record_durable_lifecycle_closure,
    record_lifecycle_closure,
    reset_lifecycle_closure_records_for_tests as reset_lifecycle_closure_truth_for_tests,
)

__all__ = [
    "CANONICAL_CLOSURE_STATUSES",
    "CLOSURE_CANCELLED",
    "CLOSURE_FAILED",
    "CLOSURE_PURCHASE_COMPLETED",
    "CLOSURE_REPLIED",
    "CLOSURE_RETURNED_TO_SITE",
    "CLOSURE_CUSTOMER_REPLIED",
    "get_durable_closure",
    "record_durable_lifecycle_closure",
    "record_lifecycle_closure",
    "reset_lifecycle_closure_truth_for_tests",
]
