# -*- coding: utf-8 -*-
"""
Product Metrics Foundation V1 — production read/materialize probe (no merchant UI).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import ProductMetricValue
from schema_product_metric_values_v1 import ensure_product_metric_values_schema
from services.product_data.product_metrics_flag_v1 import (
    ENV_PRODUCT_METRICS_FOUNDATION_V1,
    product_metrics_foundation_v1_enabled,
)
from services.product_data.product_metrics_foundation_v1 import (
    compute_product_metrics_v1,
    materialize_product_metrics_v1,
    verify_metrics_determinism_v1,
)
from services.product_data.product_metrics_types_v1 import WINDOW_ALL

_ALLOWED_STORES = frozenset({"demo"})


def build_product_metrics_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
    materialize: bool = True,
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "foundation_enabled": product_metrics_foundation_v1_enabled(),
        "flag_env": ENV_PRODUCT_METRICS_FOUNDATION_V1,
        "table_exists": False,
        "alembic_version": None,
        "migration_target": "v5w6x7y8z9a0",
        "window_code": WINDOW_ALL,
        "signal_row_count": 0,
        "by_metric_key": {},
        "materialized_row_count": 0,
        "upserted": 0,
        "deterministic": False,
        "canonical_fingerprint": "",
        "sample_store_metrics": [],
        "errors": [],
        "migration_satisfied": False,
        "alembic_stamped_exact": False,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    try:
        ensure_product_metric_values_schema(db)
        insp = inspect(db.engine)
        out["table_exists"] = bool(insp.has_table("product_metric_values"))
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
                out["alembic_stamped_exact"] = str(row[0]) == "v5w6x7y8z9a0"
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"alembic:{type(exc).__name__}")
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    out["migration_satisfied"] = bool(out["table_exists"])

    det = verify_metrics_determinism_v1(slug, window_code=WINDOW_ALL)
    out["deterministic"] = bool(det.get("deterministic"))
    out["canonical_fingerprint"] = str(det.get("fingerprint_a") or "")
    out["by_metric_key"] = dict(det.get("by_metric_key") or {})
    out["signal_row_count"] = int(det.get("signal_row_count") or 0)
    out["errors"].extend(list(det.get("errors") or []))

    compute = compute_product_metrics_v1(slug, window_code=WINDOW_ALL)
    out["sample_store_metrics"] = [
        {
            "metric_key": m.get("metric_key"),
            "value": m.get("value"),
            "metric_family": m.get("metric_family"),
            "content_hash": m.get("content_hash"),
        }
        for m in (compute.get("store_metrics") or [])
        if int(m.get("value") or 0) > 0
    ][:20]

    if materialize and product_metrics_foundation_v1_enabled():
        mat = materialize_product_metrics_v1(slug, window_code=WINDOW_ALL)
        out["upserted"] = int(mat.get("upserted") or 0)
        if not mat.get("ok"):
            out["errors"].extend(list(mat.get("errors") or []))

    if out["table_exists"]:
        try:
            n = (
                db.session.query(func.count(ProductMetricValue.id))
                .filter(ProductMetricValue.store_slug == slug)
                .scalar()
            )
            out["materialized_row_count"] = int(n or 0)
        except SQLAlchemyError as exc:
            out["errors"].append(f"count:{type(exc).__name__}")
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass

    out["ok"] = bool(
        out["table_exists"]
        and out["deterministic"]
        and out["signal_row_count"] >= 0
        and "store_not_allowlisted" not in out["errors"]
    )
    return out


__all__ = ["build_product_metrics_prod_probe_v1"]
