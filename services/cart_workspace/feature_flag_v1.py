# -*- coding: utf-8 -*-
"""Cart Workspace feature flag — merchant surface gated by env."""
from __future__ import annotations

import os


FLAG_CART_WORKSPACE_V1 = "CARTFLOW_CART_WORKSPACE_V1"


def cart_workspace_v1_enabled() -> bool:
    """
    Merchant Workspace execution gate.

    - Explicit true/1/yes/on → ON
    - Explicit false/0/no/off → OFF (rollback)
    - Unset on Railway deploy → ON (pre-launch production publish)
    - Unset elsewhere → OFF (local/dev safety)
    """
    raw = (os.environ.get(FLAG_CART_WORKSPACE_V1) or "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    # Pre-launch: Railway process without explicit flag → enabled.
    # Rollback remains: set CARTFLOW_CART_WORKSPACE_V1=false and restart/redeploy.
    if (os.environ.get("RAILWAY_GIT_COMMIT_SHA") or "").strip():
        return True
    return False


def cart_workspace_primary_dashboard_path() -> str:
    """
    Primary merchant entry when Workspace is enabled.
    #carts remains available as rollback/reference; flag OFF restores #carts.
    """
    if cart_workspace_v1_enabled():
        return "/dashboard#workspace"
    return "/dashboard#carts"


def cart_workspace_v1_flag_state() -> dict:
    raw = (os.environ.get(FLAG_CART_WORKSPACE_V1) or "").strip()
    return {
        "flag": FLAG_CART_WORKSPACE_V1,
        "enabled": cart_workspace_v1_enabled(),
        "default": False,
        "env_raw": raw or None,
        "railway_deploy_default_on": True,
        "merchant_surface": "disabled" if not cart_workspace_v1_enabled() else "enabled",
        "shadow_pipeline": "available_dev_only",
        "primary_path": cart_workspace_primary_dashboard_path(),
    }
