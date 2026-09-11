# -*- coding: utf-8 -*-
"""Disposable PostgreSQL Alembic replay. Never pointed at production."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

from services.migration_lineage_integrity_v1.inventory import snapshot_schema
from services.migration_lineage_integrity_v1.replay import upgrade_heads_from_empty

CANONICAL_HEAD = "f10altparity01"
B_CLASS_TABLES: tuple[str, ...] = (
    "abandonment_reason_logs",
    "cart_recovery_reasons",
    "merchant_followup_actions",
    "recovery_schedules",
    "merchant_users",
    "merchant_password_reset_tokens",
    "whatsapp_delivery_truth",
    "purchase_truth_records",
    "lifecycle_closure_records",
    "recovery_truth_timeline_events",
    "merchant_cart_lifecycle_archives",
    "store_identity_aliases",
    "operational_control_snapshots",
    "db_ready_operational_snapshots",
    "merchant_subscription_audit_logs",
    "movement_snapshots",
    "provider_retry_ledger",
    "diagnostic_snapshots",
    "evidence_gaps",
    "landing_page_events_v1",
    "product_exposure_events",
    "product_exposure_daily_facts",
)


def _pgdata_root() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"))
    root = base / "cartflow_mhr_v21_pg"
    root.mkdir(parents=True, exist_ok=True)
    return root


def start_disposable_postgres() -> Any:
    """Start a local embedded PostgreSQL. Caller must cleanup()."""
    from pgembed import get_server

    stamp = f"replay_{os.getpid()}_{int(time.time())}"
    pgdata = _pgdata_root() / stamp
    if not pgdata.exists():
        pgdata.mkdir(parents=False, exist_ok=False)
    return get_server(pgdata, cleanup_mode="delete")


def _admin_engine(server: Any):
    uri = server.get_uri(database="postgres")
    if uri.startswith("postgresql://") and "+psycopg" not in uri:
        uri = uri.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(uri, isolation_level="AUTOCOMMIT")


def _db_uri(server: Any, name: str) -> str:
    uri = server.get_uri(database=name)
    if uri.startswith("postgresql://") and "+psycopg" not in uri:
        uri = uri.replace("postgresql://", "postgresql+psycopg://", 1)
    return uri


def create_empty_database(server: Any, name: str) -> str:
    engine = _admin_engine(server)
    try:
        with engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {name}"))
            conn.execute(text(f"CREATE DATABASE {name}"))
    finally:
        engine.dispose()
    return _db_uri(server, name)


def drop_database(server: Any, name: str) -> None:
    engine = _admin_engine(server)
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    f"WHERE datname = '{name}' AND pid <> pg_backend_pid()"
                )
            )
            conn.execute(text(f"DROP DATABASE IF EXISTS {name}"))
    finally:
        engine.dispose()


def postgres_version(url: str) -> str:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return str(conn.execute(text("SELECT version()")).scalar() or "")
    finally:
        engine.dispose()


def replay_once(url: str) -> dict[str, Any]:
    out = upgrade_heads_from_empty(database_url=url)
    out["postgres_version"] = postgres_version(url) if out.get("ok") else None
    if out.get("ok"):
        engine = create_engine(url)
        try:
            out["schema"] = snapshot_schema(engine)
        finally:
            engine.dispose()
    return out


def replay_twice_independently() -> dict[str, Any]:
    """Create two empty DBs, upgrade each from zero. Destroy the first before the second."""
    report: dict[str, Any] = {
        "ok": False,
        "replay_1": None,
        "replay_2": None,
        "deterministic": False,
        "postgres_version": None,
        "error": None,
    }
    server = None
    try:
        server = start_disposable_postgres()
        url1 = create_empty_database(server, "cartflow_replay_1")
        r1 = replay_once(url1)
        report["replay_1"] = {
            "ok": r1.get("ok"),
            "failing_message": r1.get("failing_message"),
            "alembic_version": r1.get("alembic_version"),
            "table_count": len(r1.get("tables") or []),
            "tables": r1.get("tables"),
            "postgres_version": r1.get("postgres_version"),
            "starting_schema": "EMPTY",
        }
        report["postgres_version"] = r1.get("postgres_version")
        drop_database(server, "cartflow_replay_1")

        url2 = create_empty_database(server, "cartflow_replay_2")
        r2 = replay_once(url2)
        report["replay_2"] = {
            "ok": r2.get("ok"),
            "failing_message": r2.get("failing_message"),
            "alembic_version": r2.get("alembic_version"),
            "table_count": len(r2.get("tables") or []),
            "tables": r2.get("tables"),
            "postgres_version": r2.get("postgres_version"),
            "starting_schema": "EMPTY",
        }
        report["schema_2"] = r2.get("schema")
        report["deterministic"] = bool(
            r1.get("ok")
            and r2.get("ok")
            and r1.get("alembic_version") == r2.get("alembic_version")
            and set(r1.get("tables") or []) == set(r2.get("tables") or [])
        )
        report["ok"] = bool(
            report["deterministic"]
            and r1.get("alembic_version") == [CANONICAL_HEAD]
            and "commercial_decision_commitments" not in (r1.get("tables") or [])
            and all(t in (r1.get("tables") or []) for t in B_CLASS_TABLES)
        )
        report["final_url"] = url2
        report["server"] = server
        return report
    except Exception as exc:  # noqa: BLE001
        report["error"] = f"{type(exc).__name__}: {exc}"
        if server is not None:
            try:
                server.cleanup()
            except Exception:  # noqa: BLE001
                pass
        return report
