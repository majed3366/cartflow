# -*- coding: utf-8 -*-
"""Empty-database Alembic replay. Never pointed at production."""
from __future__ import annotations

import os
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from services.migration_lineage_integrity_v1.graph import inspect_lineage


def _config(ini_path: str | None = None, url: str | None = None) -> Config:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = ini_path or os.path.join(root, "alembic.ini")
    cfg = Config(path)
    if url:
        cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def upgrade_heads_from_empty(
    *,
    database_url: str,
    ini_path: str | None = None,
) -> dict[str, Any]:
    """Run `alembic upgrade heads` on an isolated empty URL. No create_all."""
    lineage = inspect_lineage(ini_path)
    report: dict[str, Any] = {
        "ok": False,
        "lineage": lineage,
        "heads": list(lineage.get("heads") or []),
        "failing_revision": None,
        "failing_message": None,
        "tables": [],
        "alembic_version": [],
    }
    if not lineage.get("walkable"):
        report["failing_message"] = lineage.get("error") or "lineage_not_walkable"
        return report

    url = (database_url or "").strip()
    if not url:
        report["failing_message"] = "database_url_missing"
        return report

    cfg = _config(ini_path, url)
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        command.upgrade(cfg, "heads")
        report["ok"] = True
    except Exception as exc:  # noqa: BLE001
        report["failing_message"] = f"{type(exc).__name__}: {exc}"
        script = ScriptDirectory.from_config(cfg)
        walk = list(reversed([s.revision for s in script.walk_revisions()]))
        # Identify first failing revision on a sibling empty URL if caller used sqlite file.
        report["revision_walk"] = walk
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous

    engine = create_engine(url)
    try:
        insp = inspect(engine)
        report["tables"] = sorted(insp.get_table_names())
        if insp.has_table("alembic_version"):
            with engine.connect() as conn:
                report["alembic_version"] = sorted(
                    r[0] for r in conn.execute(text("SELECT version_num FROM alembic_version"))
                )
    finally:
        engine.dispose()
    return report
