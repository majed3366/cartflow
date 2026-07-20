# -*- coding: utf-8 -*-
"""
Product Trends Foundation V1 — production probe (no merchant UI).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import ProductTrendValue
from schema_product_trend_values_v1 import ensure_product_trend_values_schema
from services.product_data.product_trends_flag_v1 import (
    ENV_PRODUCT_TRENDS_FOUNDATION_V1,
    product_trends_foundation_v1_enabled,
)
from services.product_data.product_trends_foundation_v1 import (
    compute_product_trends_v1,
    materialize_product_trends_v1,
    verify_trends_determinism_v1,
)
from services.product_data.product_trends_types_v1 import TREND_WINDOW_D7

_ALLOWED_STORES = frozenset({"demo"})


def build_product_trends_prod_probe_v1(
    store_slug: str,
    *,
    allow_any_store: bool = False,
    materialize: bool = True,
    trend_window: str = TREND_WINDOW_D7,
) -> dict[str, Any]:
    slug = (store_slug or "").strip()[:255]
    window = (trend_window or TREND_WINDOW_D7).strip().lower() or TREND_WINDOW_D7
    out: dict[str, Any] = {
        "ok": False,
        "store_slug": slug,
        "foundation_enabled": product_trends_foundation_v1_enabled(),
        "flag_env": ENV_PRODUCT_TRENDS_FOUNDATION_V1,
        "table_exists": False,
        "alembic_version": None,
        "migration_target": "w6x7y8z9a0b1",
        "trend_window": window,
        "as_of": None,
        "deterministic": False,
        "canonical_fingerprint": "",
        "by_direction": {},
        "store_trend_count": 0,
        "product_trend_count": 0,
        "materialized_row_count": 0,
        "upserted": 0,
        "sample_store_trends": [],
        "errors": [],
        "migration_satisfied": False,
        "alembic_stamped_exact": False,
        "consumes_metrics_only": True,
    }
    if not slug:
        out["errors"].append("store_slug_required")
        return out
    if not allow_any_store and slug not in _ALLOWED_STORES:
        out["errors"].append("store_not_allowlisted")
        return out

    try:
        ensure_product_trend_values_schema(db)
        insp = inspect(db.engine)
        out["table_exists"] = bool(insp.has_table("product_trend_values"))
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
                out["alembic_stamped_exact"] = str(row[0]) == "w6x7y8z9a0b1"
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"alembic:{type(exc).__name__}")
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    out["migration_satisfied"] = bool(out["table_exists"])

    det = verify_trends_determinism_v1(slug, trend_window=window)
    out["deterministic"] = bool(det.get("deterministic"))
    out["canonical_fingerprint"] = str(det.get("fingerprint_a") or "")
    out["as_of"] = det.get("as_of")
    out["by_direction"] = dict(det.get("by_direction") or {})
    out["store_trend_count"] = int(det.get("store_trend_count") or 0)
    out["product_trend_count"] = int(det.get("product_trend_count") or 0)
    out["errors"].extend(list(det.get("errors") or []))

    compute = compute_product_trends_v1(slug, trend_window=window)
    # Recompute with frozen as_of from determinism check for stable sample
    if det.get("as_of"):
        from datetime import datetime

        try:
            frozen = datetime.fromisoformat(str(det["as_of"]))
            compute = compute_product_trends_v1(
                slug, trend_window=window, as_of=frozen
            )
        except ValueError:
            pass
    out["sample_store_trends"] = [
        {
            "metric_key": t.get("metric_key"),
            "current_value": t.get("current_value"),
            "previous_value": t.get("previous_value"),
            "delta_abs": t.get("delta_abs"),
            "trend_direction": t.get("trend_direction"),
        }
        for t in (compute.get("store_trends") or [])[:20]
    ]

    if materialize and product_trends_foundation_v1_enabled():
        mat_as_of = None
        if det.get("as_of"):
            from datetime import datetime

            try:
                mat_as_of = datetime.fromisoformat(str(det["as_of"]))
            except ValueError:
                mat_as_of = None
        mat = materialize_product_trends_v1(
            slug, trend_window=window, as_of=mat_as_of
        )
        out["upserted"] = int(mat.get("upserted") or 0)
        if not mat.get("ok"):
            out["errors"].extend(list(mat.get("errors") or []))

    if out["table_exists"]:
        try:
            n = (
                db.session.query(func.count(ProductTrendValue.id))
                .filter(ProductTrendValue.store_slug == slug)
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
        and "store_not_allowlisted" not in out["errors"]
    )
    return out


__all__ = ["build_product_trends_prod_probe_v1"]
