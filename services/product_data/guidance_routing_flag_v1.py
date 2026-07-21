# -*- coding: utf-8 -*-
"""Guidance Routing Foundation V1 — kill switch (default on)."""
from __future__ import annotations

import os

ENV_GUIDANCE_ROUTING_V1 = "CARTFLOW_GUIDANCE_ROUTING_FOUNDATION_V1"


def guidance_routing_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_GUIDANCE_ROUTING_V1) or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


__all__ = [
    "ENV_GUIDANCE_ROUTING_V1",
    "guidance_routing_v1_enabled",
]
