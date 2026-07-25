# -*- coding: utf-8 -*-
"""Business Theme Engine V1 — feature flag (default ON)."""
from __future__ import annotations

import os
from typing import Mapping

ENV_BUSINESS_THEMES_V1 = "CARTFLOW_BUSINESS_THEMES_V1"


def business_themes_v1_enabled(*, environ: Mapping[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    raw = str(env.get(ENV_BUSINESS_THEMES_V1, "1") or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


__all__ = ["ENV_BUSINESS_THEMES_V1", "business_themes_v1_enabled"]
