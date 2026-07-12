# -*- coding: utf-8 -*-
"""Silent Success Product Validation mode — internal facilitator only."""
from __future__ import annotations

import os

FLAG_SILENT_SUCCESS = "CARTFLOW_CART_WORKSPACE_SILENT_SUCCESS"


def cart_workspace_silent_success_enabled() -> bool:
    """When true (with Workspace flag ON): merchant-clean UI, auto-seed, no facilitator chrome."""
    raw = (os.environ.get(FLAG_SILENT_SUCCESS) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}
