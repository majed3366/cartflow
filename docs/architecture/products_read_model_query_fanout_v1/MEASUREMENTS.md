# PRODUCTS_READ_MODEL_QUERY_FANOUT_V1 — measurements

Local SQLite. Compose only (`compose_products_commercial_truth_v1`). Not production Postgres, not HTTP.

## Query trace — before (4/5 ORM reads, 2026-09-09)

Captured while `_load_from_db` still issued separate ORM queries.

| Tenant | query_delta | sql_n | wall_ms | products |
|--------|-------------|-------|---------|----------|
| Lab R17 `cf_live_reality_lab` | 5 | 5 | 45.179 | 11 / 10 named |
| Normal empty slug `acme_store` | 4 | 4 | 14.588 | 0 |

SQL owners (lab):

1. `product_catalog_entries`
2. `cart_line_snapshots` ⟕ `abandoned_carts`
3. `product_purchase_mappings` grouped
4. `product_hesitation_mappings` grouped
5. `product_signal_events` grouped (`product_viewed` + lab synthetic source)

Normal omitted (5). N+1 = 0.

## Query trace — after (one CTE read, 2026-09-09)

| Tenant | query_delta | sql_n | wall_ms | products |
|--------|-------------|-------|---------|----------|
| Lab R17 | 1 | 1 | 27.618 | 11 / 10 named |
| Normal empty slug | 1 | 1 | 8.222 | 0 |

One `WITH catalog AS (...)` statement. Lab body includes `product_signal_events`. Normal body does not.

Wall time improved on this SQLite capture. Query-count reduction is not the only claim.

## Scale (synthetic catalog + 20 hot SKUs × 8 carts/purchases/hesitation)

All runs: **1 SQL**, N+1 = 0, result rows capped at `MAX_PRODUCTS` (40).

| Catalog n | wall_ms | result_rows |
|-----------|---------|-------------|
| 11 | 30.962 | 11 |
| 100 | 30.998 | 40 |
| 500 | 18.666 | 40 |
| 1000 | 24.518 | 40 |

No explosive join: output stays ≤ 40. 500/1000 times are the same order as 11 (SQLite cache + LIMIT 40 on catalog). Not a load test.

## R17 truth (after)

| Product | carts | SAR | purchases | hesitation | visits |
|---------|-------|-----|-----------|------------|--------|
| عود ملكي مركز | 5 | 945 | 0 | price 5 | lab 5 |
| عنبر ليلي | 4 | 596 | 0 | shipping 4 | lab 4 |
| طقم العناية الفاخر | 4 | 996 | 0 | — | none recorded |
| nf-missing-name | — | — | — | — | degraded identity |
