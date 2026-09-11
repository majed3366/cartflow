# -*- coding: utf-8 -*-
"""Stamp-only Alembic metadata helpers. Never runs upgrade()."""
from __future__ import annotations

import os
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from services.migration_lineage_integrity_v1.graph import inspect_lineage

CANONICAL_HEAD = "f10altparity01"
EXPECTED_PRODUCTION_ANCESTORS: frozenset[str] = frozenset(
    {"k1l2m3n4o5p6q7", "k2l3m4n5o6p7"}
)


def _config(ini_path: str | None = None) -> Config:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = ini_path or os.path.join(root, "alembic.ini")
    return Config(path)


def _normalize_url(url: str) -> str:
    u = (url or "").strip()
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://") :]
    return u


def _read_versions(url: str) -> list[str]:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
        return sorted(r[0] for r in rows)
    except Exception:  # noqa: BLE001
        return []
    finally:
        engine.dispose()


def ancestor_paths_to_head(
    *,
    ancestors: frozenset[str] = EXPECTED_PRODUCTION_ANCESTORS,
    head: str = CANONICAL_HEAD,
    ini_path: str | None = None,
) -> dict[str, Any]:
    """Prove each ancestor is on a walkable path to the canonical head."""
    lineage = inspect_lineage(ini_path)
    out: dict[str, Any] = {
        "ok": False,
        "walkable": bool(lineage.get("walkable")),
        "heads": list(lineage.get("heads") or []),
        "missing_parents": list(lineage.get("missing_parents") or []),
        "canonical_head": head,
        "ancestors": sorted(ancestors),
        "paths": {},
        "reason": None,
    }
    if not lineage.get("walkable"):
        out["reason"] = lineage.get("error") or "lineage_not_walkable"
        return out
    if lineage.get("heads") != [head]:
        out["reason"] = "unexpected_heads:" + ",".join(lineage.get("heads") or [])
        return out
    script = ScriptDirectory.from_config(_config(ini_path))
    known = {s.revision for s in script.walk_revisions()}
    missing = sorted(a for a in ancestors if a not in known)
    if missing:
        out["reason"] = "ancestor_not_in_map:" + ",".join(missing)
        return out
    if head not in known:
        out["reason"] = "head_not_in_map"
        return out

    def _parents(rev: str) -> tuple[str, ...]:
        down = script.get_revision(rev).down_revision
        if down is None:
            return ()
        if isinstance(down, str):
            return (down,)
        return tuple(down)

    reached: dict[str, list[str]] = {a: [] for a in ancestors}
    stack: list[tuple[str, list[str]]] = [(head, [head])]
    seen: set[str] = set()
    while stack:
        rev, path = stack.pop()
        if rev in seen:
            continue
        seen.add(rev)
        if rev in reached and not reached[rev]:
            reached[rev] = list(reversed(path))
        for parent in _parents(rev):
            stack.append((parent, path + [parent]))
    out["paths"] = reached
    if all(reached[a] for a in ancestors):
        out["ok"] = True
        out["reason"] = "ancestors_reach_head"
    else:
        missing_paths = [a for a in ancestors if not reached[a]]
        out["reason"] = "ancestor_not_on_path:" + ",".join(missing_paths)
    return out


def plan_or_stamp_heads(
    *,
    database_url: str,
    execute: bool = False,
    ini_path: str | None = None,
) -> dict[str, Any]:
    """Create `alembic_version` and stamp heads. Default is plan-only."""
    lineage = inspect_lineage(ini_path)
    report: dict[str, Any] = {
        "execute": bool(execute),
        "lineage": lineage,
        "ok": False,
        "action": "refused",
        "stamped": [],
        "alembic_version_before": [],
        "alembic_version_after": [],
        "reason": None,
    }
    if not lineage.get("walkable"):
        report["reason"] = "lineage_not_walkable"
        return report
    heads = list(lineage.get("heads") or [])
    if not heads:
        report["reason"] = "no_heads"
        return report

    url = _normalize_url(database_url)
    if not url:
        report["reason"] = "database_url_missing"
        return report

    before = _read_versions(url)
    report["alembic_version_before"] = before
    extra = sorted(set(before) - set(heads))
    if extra:
        report["reason"] = "unexpected_alembic_version:" + ",".join(extra)
        return report

    report["action"] = "stamp_heads"
    report["stamped"] = heads
    if not execute:
        report["ok"] = True
        report["reason"] = "plan_only"
        return report

    cfg = _config(ini_path)
    cfg.set_main_option("sqlalchemy.url", url)
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        command.stamp(cfg, "heads")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous

    after = _read_versions(url)
    report["alembic_version_after"] = after
    report["ok"] = set(after) == set(heads)
    report["reason"] = "stamped" if report["ok"] else "stamp_mismatch"
    return report


def stamp_canonical_from_ancestors(
    *,
    database_url: str,
    execute: bool = False,
    expected_before: frozenset[str] = EXPECTED_PRODUCTION_ANCESTORS,
    target: str = CANONICAL_HEAD,
    ini_path: str | None = None,
) -> dict[str, Any]:
    """Stamp metadata from known production ancestors to the canonical head.

    Never calls upgrade() or downgrade(). Mutates only alembic_version.
    """
    graph = ancestor_paths_to_head(
        ancestors=expected_before, head=target, ini_path=ini_path
    )
    report: dict[str, Any] = {
        "execute": bool(execute),
        "ok": False,
        "action": "refused",
        "target": target,
        "expected_before": sorted(expected_before),
        "alembic_version_before": [],
        "alembic_version_after": [],
        "graph": graph,
        "reason": None,
        "command": f"alembic stamp {target}",
    }
    if not graph.get("ok"):
        report["reason"] = graph.get("reason") or "graph_invalid"
        return report

    url = _normalize_url(database_url)
    if not url:
        report["reason"] = "database_url_missing"
        return report
    before = _read_versions(url)
    report["alembic_version_before"] = before
    if set(before) != set(expected_before):
        report["reason"] = "unexpected_alembic_version:" + ",".join(before or ["<empty>"])
        return report

    report["action"] = "stamp_canonical"
    if not execute:
        report["ok"] = True
        report["reason"] = "plan_only"
        return report

    cfg = _config(ini_path)
    cfg.set_main_option("sqlalchemy.url", url)
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        command.stamp(cfg, target)
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous

    after = _read_versions(url)
    report["alembic_version_after"] = after
    report["ok"] = after == [target]
    report["reason"] = "stamped" if report["ok"] else "stamp_mismatch"
    return report
