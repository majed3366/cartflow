# -*- coding: utf-8 -*-
"""Business Facts Extraction V1 — feature flag (default ON)."""
from __future__ import annotations

import os
from typing import Mapping

ENV_BUSINESS_FACTS_V1 = "CARTFLOW_BUSINESS_FACTS_V1"


def business_facts_v1_enabled(*, environ: Mapping[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    raw = str(env.get(ENV_BUSINESS_FACTS_V1, "1") or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


__all__ = ["ENV_BUSINESS_FACTS_V1", "business_facts_v1_enabled"]
