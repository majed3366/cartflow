# -*- coding: utf-8 -*-
"""OTIF V1 — Operational Truth Integration feature flag."""
from __future__ import annotations

import os

ENV_OPERATIONAL_TRUTH_V1 = "CARTFLOW_OPERATIONAL_TRUTH_V1"


def operational_truth_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_OPERATIONAL_TRUTH_V1) or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


__all__ = ["ENV_OPERATIONAL_TRUTH_V1", "operational_truth_v1_enabled"]
