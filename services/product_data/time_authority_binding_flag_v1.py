# -*- coding: utf-8 -*-
"""TABF V1 — Time Authority Binding feature flag."""
from __future__ import annotations

import os

ENV_TIME_AUTHORITY_BINDING_V1 = "CARTFLOW_TIME_AUTHORITY_BINDING_V1"


def time_authority_binding_v1_enabled() -> bool:
    raw = (os.environ.get(ENV_TIME_AUTHORITY_BINDING_V1) or "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


__all__ = ["ENV_TIME_AUTHORITY_BINDING_V1", "time_authority_binding_v1_enabled"]
