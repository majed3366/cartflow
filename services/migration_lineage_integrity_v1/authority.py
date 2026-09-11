# -*- coding: utf-8 -*-
"""Production schema authority: Alembic owns DDL. create_all() may not repair."""
from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy import inspect

log = logging.getLogger("cartflow")

# Tables that production must already have. Missing → visible failure, not create_all.
REQUIRED_PRODUCTION_TABLES: tuple[str, ...] = (
    "alembic_version",
    "stores",
    "purchase_truth_records",
    "order_economic_facts",
    "store_identity_aliases",
)

_REFUSE_LOGGED = False


def schema_mutation_permitted() -> bool:
    """False when runtime must not ADD COLUMN / create_all / manufacture schema."""
    return create_all_permitted()


def create_all_permitted() -> bool:
    """True only for tests, explicit allow, or ephemeral local development."""
    if (os.getenv("CARTFLOW_ALLOW_CREATE_ALL") or "").strip() == "1":
        return True
    if (os.getenv("CARTFLOW_REFUSE_CREATE_ALL") or "").strip() == "1":
        return False
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    env = (os.getenv("ENV") or "").strip().lower()
    if env == "development":
        return True
    if env in ("production", "prod", "staging", "preview"):
        return False
    role = (os.getenv("CARTFLOW_PROCESS_ROLE") or "").strip().lower()
    if role in ("api", "scheduler"):
        return False
    return True


def note_create_all_refused() -> None:
    global _REFUSE_LOGGED
    if not _REFUSE_LOGGED:
        log.warning(
            "schema_authority: create_all refused — Alembic is the production "
            "schema authority"
        )
        _REFUSE_LOGGED = True


def inspect_required_schema(engine: Any) -> dict[str, Any]:
    """Return whether required production tables exist. Never creates them."""
    missing: list[str] = []
    present: list[str] = []
    error = None
    try:
        insp = inspect(engine)
        names = set(insp.get_table_names())
        for table in REQUIRED_PRODUCTION_TABLES:
            if table in names:
                present.append(table)
            else:
                missing.append(table)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}:{exc}"
        missing = list(REQUIRED_PRODUCTION_TABLES)
    ok = not missing and error is None
    return {
        "ok": ok,
        "authority": "alembic",
        "required": list(REQUIRED_PRODUCTION_TABLES),
        "present": present,
        "missing": missing,
        "error": error,
        "reason": "ok" if ok else "schema_missing" if missing else "inspect_failed",
    }


def assert_required_schema(engine: Any) -> dict[str, Any]:
    chk = inspect_required_schema(engine)
    if not chk["ok"]:
        raise RuntimeError(
            "schema_authority_missing:" + ",".join(chk.get("missing") or [])
        )
    return chk
