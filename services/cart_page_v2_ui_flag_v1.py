# -*- coding: utf-8 -*-
"""
Cart Page V2 Phase 2 — Attention Verdict (presentation flag).

When enabled, the Carts page shows one merchant attention verdict and hides
competing hero / MPL / queue-sub summaries. No truth or API changes.
"""
from __future__ import annotations

import os

ENV_CARTS_V2_UI = "CARTFLOW_CARTS_V2_UI"


def carts_v2_ui_enabled() -> bool:
    """Default on after Phase 1 — set CARTFLOW_CARTS_V2_UI=0 to restore legacy summaries."""
    raw = (os.environ.get(ENV_CARTS_V2_UI) or "1").strip().lower()
    if not raw:
        return True
    return raw in ("1", "true", "yes", "on")


__all__ = ["ENV_CARTS_V2_UI", "carts_v2_ui_enabled"]
