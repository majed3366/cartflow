# -*- coding: utf-8 -*-
"""Cart Workspace feature flag — merchant surface default OFF."""
from __future__ import annotations

import os


FLAG_CART_WORKSPACE_V1 = "CARTFLOW_CART_WORKSPACE_V1"


def cart_workspace_v1_enabled() -> bool:
    """Merchant Workspace execution gate. Default False (Sprint 1: shadow only)."""
    raw = (os.environ.get(FLAG_CART_WORKSPACE_V1) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def cart_workspace_v1_flag_state() -> dict:
    return {
        "flag": FLAG_CART_WORKSPACE_V1,
        "enabled": cart_workspace_v1_enabled(),
        "default": False,
        "merchant_surface": "disabled" if not cart_workspace_v1_enabled() else "enabled",
        "shadow_pipeline": "available_dev_only",
    }
