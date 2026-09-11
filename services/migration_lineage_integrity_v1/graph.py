# -*- coding: utf-8 -*-
"""Alembic revision-map integrity. No database writes."""
from __future__ import annotations

import os
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory


def _config(ini_path: str | None = None) -> Config:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = ini_path or os.path.join(root, "alembic.ini")
    return Config(path)


def inspect_lineage(ini_path: str | None = None) -> dict[str, Any]:
    """Load the revision map or report why it cannot walk."""
    out: dict[str, Any] = {
        "walkable": False,
        "heads": [],
        "bases": [],
        "revision_count": 0,
        "missing_parents": [],
        "error": None,
    }
    try:
        script = ScriptDirectory.from_config(_config(ini_path))
        # Force map build — this is what KeyError'd on m1n2 / p2q3.
        _ = script.revision_map
        heads = list(script.get_heads())
        bases = list(script.get_bases())
        revs = list(script.walk_revisions())
        out["walkable"] = True
        out["heads"] = sorted(heads)
        out["bases"] = sorted(bases)
        out["revision_count"] = len(revs)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}:{exc}"
        msg = str(exc)
        if "m1n2o3p4q5r6" in msg:
            out["missing_parents"].append("m1n2o3p4q5r6")
        if "p2q3r4s5t6u7" in msg:
            out["missing_parents"].append("p2q3r4s5t6u7")
    return out
