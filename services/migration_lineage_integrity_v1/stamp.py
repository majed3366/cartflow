# -*- coding: utf-8 -*-
"""Stamp current Alembic heads only. Never runs upgrade()."""
from __future__ import annotations

import os
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from services.migration_lineage_integrity_v1.graph import inspect_lineage


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
        return [r[0] for r in rows]
    except Exception:  # noqa: BLE001
        return []
    finally:
        engine.dispose()


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
