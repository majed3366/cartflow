# -*- coding: utf-8 -*-
"""
Product Evidence Assembly Foundation V1 — production probe (no merchant UI).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import ProductEvidenceBundle, ProductEvidenceItem
from schema_product_evidence_assembly_v1 import ensure_product_evidence_assembly_schema
from services.product_data.product_evidence_assembly_flag_v1 import (
    ENV_PRODUCT_EVIDENCE_ASSEMBLY_V1,
    product_evidence_assembly_v1_enabled,
)
from services.product_data.product_evidence_assembly_v1 import (
    assemble_product_evidence_v1,
    materialize_product_evidence_v1,
    verify_evidence_assembly_determinism_v1,
)
from services.product_data.product_trends_types_v1 import TREND_WINDOW_D7

_ALLOWED_STORES = frozenset({"demo"})


def build_product_evidence_assembly_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
    materialize: bool = True,
    assembly_window: str = TREND_WINDOW_D7,
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (assembly_window or TREND_WINDOW_D7).strip().lower() or TREND_WINDOW_D7
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "foundation_enabled": product_evidence_assembly_v1_enabled(),
        "flag_env": ENV_PRODUCT_EVIDENCE_ASSEMBLY_V1,
        "table_exists": False,
        "items_table_exists": False,
        "alembic_version": None,
        "migration_target": "x7y8z9a0b1c2",
        "assembly_window": window,
        "as_of": None,
        "deterministic": False,
        "canonical_fingerprint": "",
        "bundle_count": 0,
        "item_count": 0,
        "materialized_bundle_count": 0,
        "materialized_item_count": 0,
        "upserted_bundles": 0,
        "upserted_items": 0,
        "sample_store_bundle": None,
        "errors": [],
        "migration_satisfied": False,
        "alembic_stamped_exact": False,
        "inputs_metrics_and_trends_only": True,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    try:
        ensure_product_evidence_assembly_schema(db)
        insp = inspect(db.engine)
        out["table_exists"] = bool(insp.has_table("product_evidence_bundles"))
        out["items_table_exists"] = bool(insp.has_table("product_evidence_items"))
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"schema:{type(exc).__name__}")
        return out

    try:
        if insp.has_table("alembic_version"):
            row = db.session.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            ).first()
            if row is not None:
                out["alembic_version"] = str(row[0])
                out["alembic_stamped_exact"] = str(row[0]) == "x7y8z9a0b1c2"
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"alembic:{type(exc).__name__}")
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    out["migration_satisfied"] = bool(
        out["table_exists"] and out["items_table_exists"]
    )

    det = verify_evidence_assembly_determinism_v1(slug, assembly_window=window)
    out["deterministic"] = bool(det.get("deterministic"))
    out["canonical_fingerprint"] = str(det.get("fingerprint_a") or "")
    out["as_of"] = det.get("as_of")
    out["bundle_count"] = int(det.get("bundle_count") or 0)
    out["item_count"] = int(det.get("item_count") or 0)
    out["errors"].extend(list(det.get("errors") or []))

    frozen = None
    if det.get("as_of"):
        try:
            frozen = datetime.fromisoformat(str(det["as_of"]))
        except ValueError:
            frozen = None
    assembled = assemble_product_evidence_v1(
        slug, assembly_window=window, as_of=frozen
    )
    store_bundles = [
        b
        for b in (assembled.get("bundles") or [])
        if b.get("subject_type") == "store"
    ]
    if store_bundles:
        b0 = store_bundles[0]
        out["sample_store_bundle"] = {
            "evidence_bundle_id": b0.get("evidence_bundle_id"),
            "fingerprint": b0.get("fingerprint"),
            "source_count": b0.get("source_count"),
            "items": [
                {
                    "metric_key": i.get("metric_key"),
                    "metric_value": i.get("metric_value"),
                    "trend_direction": i.get("trend_direction"),
                    "trend_window": i.get("trend_window"),
                    "source_layer": i.get("source_layer"),
                }
                for i in (b0.get("items") or [])[:12]
            ],
        }

    if materialize and product_evidence_assembly_v1_enabled():
        mat = materialize_product_evidence_v1(
            slug, assembly_window=window, as_of=frozen
        )
        out["upserted_bundles"] = int(mat.get("upserted_bundles") or 0)
        out["upserted_items"] = int(mat.get("upserted_items") or 0)
        if not mat.get("ok"):
            out["errors"].extend(list(mat.get("errors") or []))

    if out["table_exists"]:
        try:
            out["materialized_bundle_count"] = int(
                db.session.query(func.count(ProductEvidenceBundle.id))
                .filter(ProductEvidenceBundle.store_slug == slug)
                .scalar()
                or 0
            )
            out["materialized_item_count"] = int(
                db.session.query(func.count(ProductEvidenceItem.id))
                .filter(ProductEvidenceItem.store_slug == slug)
                .scalar()
                or 0
            )
        except SQLAlchemyError as exc:
            out["errors"].append(f"count:{type(exc).__name__}")
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass

    out["ok"] = bool(
        out["migration_satisfied"]
        and out["deterministic"]
        and "store_not_allowlisted" not in out["errors"]
    )
    return out


__all__ = ["build_product_evidence_assembly_prod_probe_v1"]
