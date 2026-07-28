# -*- coding: utf-8 -*-
"""Decision Workspace V2 feature flag — constitutional prototype surface."""
from __future__ import annotations

import os

FLAG_DECISION_WORKSPACE_V2 = "CARTFLOW_DECISION_WORKSPACE_V2"


def decision_workspace_v2_enabled() -> bool:
    """
    Decision Workspace V2 paint + budget gate.

    - Explicit false/0/no/off → OFF (rollback to prior Workspace chrome)
    - Explicit true/1/yes/on → ON
    - Unset on Railway → ON (production prototype)
    - Unset elsewhere → ON (local validates the approved constitutions)
    """
    raw = (os.environ.get(FLAG_DECISION_WORKSPACE_V2) or "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    return True


def decision_workspace_v2_flag_state() -> dict:
    raw = (os.environ.get(FLAG_DECISION_WORKSPACE_V2) or "").strip()
    return {
        "flag": FLAG_DECISION_WORKSPACE_V2,
        "enabled": decision_workspace_v2_enabled(),
        "env_raw": raw or None,
        "default": True,
    }
