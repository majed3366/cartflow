# PRODUCTS_READ_MODEL_QUERY_FANOUT_V1 — pre-deploy query-plan proof

**Date (UTC):** 2026-09-09  
**DEPLOY at this file's writing:** pending exact-SHA (plan proof only)  
**New indexes created:** NO  

## Verdict

**QUERY PLAN SAFETY: PASS**  
**CARTESIAN JOIN: NO**  
**UNBOUNDED PER-PRODUCT CORRELATED TABLE QUERY: NO**  
**IMPORTANT MISSING INDEX: NO** (do not create indexes to force PASS)

The 40-row output cap is applied **after** store-scoped index searches and independent aggregates. It does not hide a cartesian explosion.

## Existing indexes used (already on the models — not added by this debt)

| Source | Tenant predicate | Index observed in EXPLAIN / model |
|--------|------------------|-----------------------------------|
| `product_catalog_entries` | `store_slug = :slug` | `ix_product_catalog_entries_store_slug` **SEARCH** |
| `cart_line_snapshots` | `store_slug = :slug` | `ix_cart_line_snapshots_store_slug` **SEARCH** |
| `abandoned_carts` | join `zid_cart_id` + optional `store_id` | `ix_abandoned_carts_zid_cart_id` UNIQUE **SEARCH LEFT-JOIN** |
| `product_purchase_mappings` | `store_slug = :slug` | `ix_product_purchase_mappings_store_slug` **SEARCH** |
| `product_hesitation_mappings` | `store_slug = :slug` | `ix_product_hesitation_mappings_store_slug` **SEARCH** |
| `product_signal_events` (lab SQL only) | `store_slug` + lab source + `product_viewed` | `store_slug` / `source` / `signal_type` indexes exist. SQLite R17 plan picked `ix_product_signal_events_signal_type` then filtered. Postgres may choose `store_slug`. Same predicates as the previous isolated lab query. |

`TRIM(product_id)` is a residual filter **after** the `store_slug` equality. It is not a missing index.

`ORDER BY last_synced_at LIMIT 40` on catalog is the same shape as the prior ORM query. No new composite was required for this closure.

## Aggregation before cross-source joins

CTEs `cart_pairs` → `carts`, `purchases`, `hes_counts` → `hesitation`, `visits` (lab) each reduce to **one row per product_id**. Final `LEFT JOIN` is on those pre-aggregates only.

## Correlated subquery (bounded)

`NOT EXISTS (SELECT 1 FROM catalog cat …)` is a correlated scalar against the **materialized catalog CTE (≤40 rows)**, not against `product_catalog_entries` per product. EXPLAIN: `CORRELATED SCALAR SUBQUERY` → `SCAN cat`.

Universe membership uses `IN (SELECT product_id FROM universe)` + bloom filter, not an N+1 loop.

## SQLite R17 EXPLAIN QUERY PLAN (local)

Captured with `docs/architecture/products_read_model_query_fanout_v1/_explain_plan.py` on scenario R17.

- Catalog / cart lines / purchases / hesitation: **SEARCH** on `store_slug` indexes  
- Abandoned carts: **SEARCH** unique `zid_cart_id`  
- Final joins: automatic covering indexes on CTE `product_id`  
- No `CROSS JOIN`  
- No scan of a fact table without a store/identity index  

Production is PostgreSQL. This proof is the SQLite plan plus the SQL shape (same predicates, same existing indexes). No production `EXPLAIN` was required to reject a cartesian; none was observed.

## Normal merchant

Separate SQL body: **zero** references to `product_signal_events`. Four `store_slug = :slug` predicates (catalog, cart lines, purchases, hesitation).
