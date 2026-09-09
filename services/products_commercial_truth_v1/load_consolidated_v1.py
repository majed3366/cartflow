# -*- coding: utf-8 -*-
"""
Products commercial truth — one bounded store-scoped SQL read.

Closes PRODUCTS_READ_MODEL_QUERY_FANOUT_V1.

Carts, purchases, hesitation, and (lab-only) visits are pre-aggregated in
independent CTEs, then left-joined onto a catalog/cart universe. One output
row per product. No N+1. No cartesian multiplication across fact tables.

Normal merchants never touch product_signal_events (separate SQL body).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from services.live_reality_lab_v1.contract_v1 import LAB_SYNTHETIC_VISIT_SOURCE
from services.product_data.product_signal_types_v1 import SIGNAL_PRODUCT_VIEWED
from services.products_commercial_truth_v1.contract_v1 import (
    MAX_CART_LINK_ROWS,
    MAX_PRODUCTS,
    QUERY_COUNT_LAB,
    QUERY_COUNT_NORMAL,
)

_RS = "CHAR(30)"
_US = "CHAR(31)"
_RS_PG = "CHR(30)"
_US_PG = "CHR(31)"


def products_read_sql_v1(*, lab_tenant: bool, dialect: str = "sqlite") -> str:
    """Return the single store-scoped SQL body. Tests inspect this string."""
    pg = str(dialect or "").lower() == "postgresql"
    rs = _RS_PG if pg else _RS
    us = _US_PG if pg else _US
    n_cast = "n::text" if pg else "CAST(n AS TEXT)"
    agg = "string_agg" if pg else "GROUP_CONCAT"
    visits_cte = ""
    visits_select = "NULL AS visit_count"
    visits_join = ""
    if lab_tenant:
        visits_cte = """
,
visits AS (
  SELECT product_id AS product_id,
         COUNT(*) AS visit_count
  FROM product_signal_events
  WHERE store_slug = :slug
    AND source = :lab_source
    AND signal_type = :lab_signal
    AND product_id IS NOT NULL
    AND TRIM(product_id) != ''
    AND product_id IN (SELECT product_id FROM universe)
  GROUP BY product_id
)
"""
        visits_select = "v.visit_count AS visit_count"
        visits_join = "LEFT JOIN visits v ON v.product_id = u.product_id"
    return f"""
WITH catalog AS (
  SELECT
    COALESCE(NULLIF(TRIM(product_id), ''), TRIM(stable_identity_key)) AS product_id,
    TRIM(name) AS name,
    price AS price,
    COALESCE(NULLIF(TRIM(currency), ''), 'SAR') AS currency,
    TRIM(sku) AS sku,
    last_synced_at AS last_synced_at
  FROM product_catalog_entries
  WHERE store_slug = :slug
    AND COALESCE(NULLIF(TRIM(product_id), ''), TRIM(stable_identity_key)) IS NOT NULL
    AND COALESCE(NULLIF(TRIM(product_id), ''), TRIM(stable_identity_key)) != ''
  ORDER BY last_synced_at DESC
  LIMIT :max_products
),
cart_pairs AS (
  SELECT product_id AS product_id,
         cart_id AS cart_id
  FROM cart_line_snapshots
  WHERE store_slug = :slug
    AND product_id IS NOT NULL
    AND TRIM(product_id) != ''
    AND cart_id IS NOT NULL
    AND TRIM(cart_id) != ''
  GROUP BY product_id, cart_id
  LIMIT :max_cart_pairs
),
carts AS (
  SELECT cp.product_id AS product_id,
         COUNT(*) AS cart_count,
         COALESCE(SUM(ac.cart_value), 0) AS cart_value
  FROM cart_pairs cp
  LEFT JOIN abandoned_carts ac
    ON ac.zid_cart_id = cp.cart_id
   AND (:store_id = 0 OR ac.store_id = :store_id)
  GROUP BY cp.product_id
),
universe AS (
  SELECT product_id FROM catalog
  UNION
  SELECT product_id FROM cart_pairs
),
purchases AS (
  SELECT product_id AS product_id,
         COUNT(*) AS purchase_count,
         COALESCE(
           SUM(COALESCE(unit_price, 0) * COALESCE(quantity, 1)),
           0
         ) AS revenue
  FROM product_purchase_mappings
  WHERE store_slug = :slug
    AND product_id IS NOT NULL
    AND TRIM(product_id) != ''
    AND product_id IN (SELECT product_id FROM universe)
  GROUP BY product_id
),
hes_counts AS (
  SELECT product_id AS product_id,
         LOWER(TRIM(reason)) AS reason,
         COUNT(*) AS n
  FROM product_hesitation_mappings
  WHERE store_slug = :slug
    AND product_id IS NOT NULL
    AND TRIM(product_id) != ''
    AND product_id IN (SELECT product_id FROM universe)
  GROUP BY product_id, LOWER(TRIM(reason))
),
hesitation AS (
  SELECT product_id AS product_id,
         {agg}(reason || {us} || {n_cast}, {rs}) AS reasons_blob
  FROM hes_counts
  GROUP BY product_id
)
{visits_cte}
,
joined AS (
  SELECT
    cat.product_id AS product_id,
    cat.name AS name,
    cat.price AS price,
    cat.currency AS currency,
    cat.sku AS sku,
    cat.last_synced_at AS last_synced_at,
    0 AS cart_only
  FROM catalog cat
  UNION ALL
  SELECT
    c.product_id AS product_id,
    '' AS name,
    NULL AS price,
    'SAR' AS currency,
    '' AS sku,
    NULL AS last_synced_at,
    1 AS cart_only
  FROM carts c
  WHERE NOT EXISTS (
    SELECT 1 FROM catalog cat WHERE cat.product_id = c.product_id
  )
)
SELECT
  u.product_id AS product_id,
  u.name AS name,
  u.price AS price,
  u.currency AS currency,
  u.sku AS sku,
  u.cart_only AS cart_only,
  COALESCE(c.cart_count, 0) AS cart_count,
  COALESCE(c.cart_value, 0) AS cart_value,
  COALESCE(p.purchase_count, 0) AS purchase_count,
  COALESCE(p.revenue, 0) AS revenue,
  h.reasons_blob AS reasons_blob,
  {visits_select}
FROM joined u
LEFT JOIN carts c ON c.product_id = u.product_id
LEFT JOIN purchases p ON p.product_id = u.product_id
LEFT JOIN hesitation h ON h.product_id = u.product_id
{visits_join}
ORDER BY u.cart_only ASC, u.last_synced_at DESC, u.product_id ASC
LIMIT :max_products
"""


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _parse_reasons(raw: Any) -> dict[str, int]:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        blob = raw
        out: dict[str, int] = {}
        for key, val in blob.items():
            n = _as_int(val)
            if n > 0:
                out[str(key).strip().lower()[:64]] = n
        return out
    text = str(raw)
    out = {}
    for part in text.split("\x1e"):
        if "\x1f" not in part:
            continue
        key, val = part.split("\x1f", 1)
        n = _as_int(val)
        if n > 0:
            out[str(key).strip().lower()[:64]] = n
    return out


def _dialect_name() -> str:
    from extensions import db

    name = getattr(getattr(db, "engine", None), "dialect", None)
    return str(getattr(name, "name", "") or "sqlite").lower()


def load_products_read_model_v1(
    store_slug: str,
    store: Any,
    *,
    lab_tenant: bool,
) -> dict[str, Any]:
    """One SQL statement. Normal merchants never touch product_signal_events."""
    from extensions import db

    slug = str(store_slug or "").strip()[:191]
    store_id = int(getattr(store, "id", 0) or 0) if store is not None else 0
    dialect = _dialect_name()
    sql_text = products_read_sql_v1(lab_tenant=bool(lab_tenant), dialect=dialect)
    if not lab_tenant and "product_signal_events" in sql_text.lower():
        raise RuntimeError("normal_merchant_paid_lab_exposure_read")
    params = {
        "slug": slug,
        "store_id": store_id,
        "max_products": int(MAX_PRODUCTS),
        "max_cart_pairs": int(MAX_CART_LINK_ROWS),
        "lab_source": LAB_SYNTHETIC_VISIT_SOURCE,
        "lab_signal": SIGNAL_PRODUCT_VIEWED,
    }
    catalog: list[dict[str, Any]] = []
    carts: dict[str, dict[str, Any]] = {}
    purchases: dict[str, dict[str, Any]] = {}
    hesitation: dict[str, dict[str, int]] = {}
    visits: dict[str, int] | None = {} if lab_tenant else None
    try:
        rows = db.session.execute(text(sql_text), params).fetchall()
        seen: set[str] = set()
        for row in rows:
            mapping = row._mapping
            pid = str(mapping.get("product_id") or "").strip()
            if not pid or pid in seen:
                continue
            seen.add(pid)
            catalog.append(
                {
                    "product_id": pid,
                    "name": str(mapping.get("name") or "").strip(),
                    "price": mapping.get("price"),
                    "currency": str(mapping.get("currency") or "SAR").strip() or "SAR",
                    "sku": str(mapping.get("sku") or "").strip(),
                    "missing_name": not str(mapping.get("name") or "").strip(),
                }
            )
            cart_count = _as_int(mapping.get("cart_count"))
            if cart_count > 0:
                carts[pid] = {
                    "cart_count": cart_count,
                    "cart_value": _as_float(mapping.get("cart_value")),
                }
            purch_n = _as_int(mapping.get("purchase_count"))
            if purch_n > 0:
                purchases[pid] = {
                    "purchase_count": purch_n,
                    "revenue": _as_float(mapping.get("revenue")),
                    "known": True,
                }
            reasons = _parse_reasons(mapping.get("reasons_blob"))
            if reasons:
                hesitation[pid] = reasons
            if lab_tenant and visits is not None:
                n_vis = mapping.get("visit_count")
                if n_vis is not None and _as_int(n_vis) > 0:
                    visits[pid] = _as_int(n_vis)
    except SQLAlchemyError:
        db.session.rollback()
        raise
    expected = QUERY_COUNT_LAB if lab_tenant else QUERY_COUNT_NORMAL
    return {
        "catalog": catalog,
        "carts": carts,
        "purchases": purchases,
        "hesitation": hesitation,
        "visits": visits,
        "query_count": expected,
        "result_row_count": len(catalog),
    }


__all__ = ["load_products_read_model_v1", "products_read_sql_v1"]
