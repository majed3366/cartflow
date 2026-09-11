# -*- coding: utf-8 -*-
"""Future additive schema change must have a real existing parent revision."""
from __future__ import annotations

from typing import Any

from services.migration_lineage_integrity_v1.graph import inspect_lineage


def future_revision_parent_rule(down_revision: str | None) -> dict[str, Any]:
    """Prove a proposed parent exists in the walkable map. No file write."""
    lineage = inspect_lineage()
    known = set(lineage.get("heads") or []) | set(lineage.get("bases") or [])
    # Walkable map is the authority; any missing parent already fails inspect_lineage.
    out: dict[str, Any] = {
        "ok": False,
        "walkable": bool(lineage.get("walkable")),
        "parent": down_revision,
        "reason": None,
    }
    if not lineage.get("walkable"):
        out["reason"] = lineage.get("error") or "lineage_not_walkable"
        return out
    if not down_revision:
        out["reason"] = "parent_required"
        return out
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    import os

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = ScriptDirectory.from_config(Config(os.path.join(root, "alembic.ini")))
    revs = {s.revision for s in script.walk_revisions()}
    if down_revision not in revs:
        out["reason"] = "parent_not_in_map"
        return out
    out["ok"] = True
    out["reason"] = "parent_exists"
    out["known_revision_count"] = len(revs)
    return out
