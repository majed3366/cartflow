# -*- coding: utf-8 -*-
"""Guidance Eligibility Foundation V1 — kill switch (default on)."""
from __future__ import annotations

import os

ENV_GUIDANCE_ELIGIBILITY_V1 = "CARTFLOW_GUIDANCE_ELIGIBILITY_V1"


def guidance_eligibility_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_GUIDANCE_ELIGIBILITY_V1) or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


__all__ = [
    "ENV_GUIDANCE_ELIGIBILITY_V1",
    "guidance_eligibility_v1_enabled",
]
