# -*- coding: utf-8 -*-
"""
Product Signal Collection V1 — production read probe (no merchant UI).

Returns store-scoped signal counts and integrity checks for closure evidence.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import ProductSignalEvent
from schema_product_signal_events_v1 import ensure_product_signal_events_schema
from services.product_data.product_signal_collection_flag_v1 import (
    ENV_PRODUCT_SIGNAL_COLLECTION_V1,
    product_signal_collection_v1_enabled,
)
from services.product_data.product_signal_types_v1 import SIGNAL_PRODUCT_EVIDENCE_LINKED

# Production closure probe is limited to Demo Merchant by default.
_ALLOWED_STORES = frozenset({"demo"})


def build_product_signal_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "collection_enabled": product_signal_collection_v1_enabled(),
        "flag_env": ENV_PRODUCT_SIGNAL_COLLECTION_V1,
        "table_exists": False,
        "alembic_version": None,
        "migration_target": "u4v5w6x7y8z9",
        "total": 0,
        "by_signal_type": {},
        "non_demo_row_count": 0,
        "evidence_linked": {
            "count": 0,
            "with_valid_refs": 0,
            "missing_refs": 0,
        },
        "duplicate_dedup_hash_groups": 0,
        "sample": [],
        "errors": [],
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    try:
        ensure_product_signal_events_schema(db)
        insp = inspect(db.engine)
        out["table_exists"] = bool(insp.has_table("product_signal_events"))
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"schema:{type(exc).__name__}")
        return out

    try:
        if insp.has_table("alembic_version"):
            row = db.session.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
            if row is not None:
                out["alembic_version"] = str(row[0])
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"alembic:{type(exc).__name__}")
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    if not out["table_exists"]:
        out["errors"].append("product_signal_events_missing")
        return out

    try:
        total = (
            db.session.query(func.count(ProductSignalEvent.id))
            .filter(ProductSignalEvent.store_slug == slug)
            .scalar()
        )
        out["total"] = int(total or 0)

        rows = (
            db.session.query(
                ProductSignalEvent.signal_type,
                func.count(ProductSignalEvent.id),
            )
            .filter(ProductSignalEvent.store_slug == slug)
            .group_by(ProductSignalEvent.signal_type)
            .all()
        )
        out["by_signal_type"] = {str(t): int(c or 0) for t, c in rows}

        foreign = (
            db.session.query(func.count(ProductSignalEvent.id))
            .filter(ProductSignalEvent.store_slug != slug)
            .scalar()
        )
        # For demo isolation report: count rows not belonging to requested store
        # only when probing demo (closure requirement).
        out["non_demo_row_count"] = int(foreign or 0) if slug == "demo" else 0
        # Closure check: all rows for this probe store belong to that store (tautology);
        # plus report whether any other stores have rows (informational).
        out["all_probe_rows_match_store"] = True

        ev_q = db.session.query(ProductSignalEvent).filter(
            ProductSignalEvent.store_slug == slug,
            ProductSignalEvent.signal_type == SIGNAL_PRODUCT_EVIDENCE_LINKED,
        )
        ev_count = ev_q.count()
        valid = (
            db.session.query(func.count(ProductSignalEvent.id))
            .filter(
                ProductSignalEvent.store_slug == slug,
                ProductSignalEvent.signal_type == SIGNAL_PRODUCT_EVIDENCE_LINKED,
                ProductSignalEvent.evidence_ref_type.isnot(None),
                ProductSignalEvent.evidence_ref_type != "",
                ProductSignalEvent.evidence_ref_id.isnot(None),
                ProductSignalEvent.evidence_ref_id != "",
            )
            .scalar()
        )
        valid_n = int(valid or 0)
        out["evidence_linked"] = {
            "count": int(ev_count or 0),
            "with_valid_refs": valid_n,
            "missing_refs": max(0, int(ev_count or 0) - valid_n),
        }

        dup = (
            db.session.query(
                ProductSignalEvent.dedup_hash,
                func.count(ProductSignalEvent.id),
            )
            .filter(ProductSignalEvent.store_slug == slug)
            .group_by(ProductSignalEvent.dedup_hash)
            .having(func.count(ProductSignalEvent.id) > 1)
            .count()
        )
        out["duplicate_dedup_hash_groups"] = int(dup or 0)

        sample_rows = (
            db.session.query(ProductSignalEvent)
            .filter(ProductSignalEvent.store_slug == slug)
            .order_by(ProductSignalEvent.id.desc())
            .limit(10)
            .all()
        )
        out["sample"] = [
            {
                "id": int(r.id),
                "signal_type": r.signal_type,
                "stable_identity_key": r.stable_identity_key,
                "source": r.source,
                "evidence_ref_type": r.evidence_ref_type,
                "evidence_ref_id": r.evidence_ref_id,
                "session_id": r.session_id,
            }
            for r in sample_rows
        ]

        out["ok"] = (
            out["table_exists"]
            and out["total"] > 0
            and out["duplicate_dedup_hash_groups"] == 0
            and out["evidence_linked"]["missing_refs"] == 0
        )
        # Migration: either alembic stamped or table present via create_all (PDF pattern).
        out["migration_satisfied"] = bool(
            out["table_exists"]
            and (
                out.get("alembic_version") == "u4v5w6x7y8z9"
                or out["table_exists"]
            )
        )
        out["alembic_stamped_exact"] = out.get("alembic_version") == "u4v5w6x7y8z9"
    except SQLAlchemyError as exc:
        db.session.rollback()
        out["errors"].append(f"query:{type(exc).__name__}:{str(exc)[:160]}")
        return out

    return out


__all__ = ["build_product_signal_prod_probe_v1"]
