# -*- coding: utf-8 -*-
"""Commerce Situation Engine V1 — feature flag (default ON)."""
from __future__ import annotations

import os
from typing import Mapping

ENV_COMMERCE_SITUATIONS_V1 = "CARTFLOW_COMMERCE_SITUATIONS_V1"


def commerce_situations_v1_enabled(*, environ: Mapping[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    raw = str(env.get(ENV_COMMERCE_SITUATIONS_V1, "1") or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


__all__ = ["ENV_COMMERCE_SITUATIONS_V1", "commerce_situations_v1_enabled"]
