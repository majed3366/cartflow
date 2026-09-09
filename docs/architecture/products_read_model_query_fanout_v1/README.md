# PRODUCTS_READ_MODEL_QUERY_FANOUT_V1

**Status:** CLOSED  
**Date (UTC):** 2026-09-09  
**DEPLOY:** NO  
**Exact-SHA deploy:** NO  
**UI / COL / OGL / Mission Catalog / CDC / Portfolio / Home / Workspace / Carts / Scheduler:** unchanged

| Field | Value |
|-------|--------|
| DEBT ID | `PRODUCTS_READ_MODEL_QUERY_FANOUT_V1` |
| CURRENT BASELINE (closed) | normal = **+1** · lab = **+1** |
| OWNER | Products server read-model (`products_commercial_truth_v1` → `load_consolidated_v1`) |
| N+1 | 0 |
| AI / external / Scheduler / new table | 0 / 0 / 0 / NO |

Phase 0 (V1.1/V1.2, still the historical before) is recorded in [`PHASE0_BASELINE.md`](PHASE0_BASELINE.md): normal **+4** · lab **+5**.

## Root cause

`_load_from_db` issued four (lab: five) independent ORM queries for one Products page:

1. `ProductCatalogEntry` — identity
2. `CartLineSnapshot` ⟕ `AbandonedCart` — carts / cart value
3. `ProductPurchaseMapping` grouped — purchases / revenue
4. `ProductHesitationMapping` grouped — product-scoped hesitation
5. Lab only: `ProductSignalEvent` `product_viewed` + `live_reality_lab_v2_synthetic_visit`

Each query was store-scoped and bounded (not N+1). The fanout was still four/five round-trips aggregating the same tenant universe.

## New read path

One store-scoped SQL (`services/products_commercial_truth_v1/load_consolidated_v1.py`):

- CTE `catalog` — `LIMIT 40` by `last_synced_at`
- CTE `cart_pairs` — unique `(product_id, cart_id)` then `LIMIT 400`
- CTE `carts` — `COUNT` + `SUM(cart_value)` after the pair aggregate
- CTE `universe` — catalog ∪ cart product ids
- CTE `purchases` / `hes_counts` / `hesitation` — independent aggregates over `universe`
- Lab SQL only: CTE `visits` on `product_signal_events`
- Final `LEFT JOIN` of pre-aggregates — one output row per product (`LIMIT 40`)
- `UNION ALL` cart-only products missing from catalog

Normal merchants execute a **different SQL body** that does not mention `product_signal_events`.

Compose / `_card_from_facts` / readability order / Products V1.2 paint are unchanged.

## Query ownership

| Concern | Owner |
|---------|--------|
| Identity / price | catalog CTE |
| Cart count / value | cart_pairs → carts CTE |
| Purchases / revenue | purchases CTE |
| Hesitation by reason | hes_counts → hesitation CTE |
| Lab visits | visits CTE (lab SQL only) |
| Presentation | `product_read_model_contract_v1` via `compose_v1` |

## SQL safety

Cart × purchase × hesitation rows cannot multiply: each fact family is aggregated to one row per product **before** join. Duplicate cart-lines collapse in `cart_pairs` (`GROUP BY product_id, cart_id`) so `COUNT(carts)` is unique carts, not snapshot rows.

## Before / after (local SQLite, R17 lab + empty normal slug)

| | Before | After |
|--|--------|--------|
| Normal query Δ | +4 | **+1** |
| Lab query Δ | +5 | **+1** |
| N+1 | 0 | 0 |
| Lab wall (compose) | 45.179 ms | 27.618 ms |
| Normal empty wall | 14.588 ms | 8.222 ms |
| Lab result rows | 11 products / 10 named | identical |
| Total SQL statements / request (Products compose) | 4 / 5 | **1** |
| Max SQL statements / request | 5 | **1** |

Wall time did not regress. Query-count reduction is not claimed as the only proof.

## Failure tests

Gate: `tests/test_products_read_model_query_fanout_closure_v1.py`

No catalog · catalog without carts · carts without purchases · purchases without hesitation · hesitation without purchase · multiple hesitation reasons · duplicate cart-line · duplicate purchase mapping · missing identity · empty store · lab vs normal exposure · cross-tenant same `product_id` · 11/100/500/1000 catalog rows · measured statement count · N+1 = 0.

## Closure proof

- NORMAL QUERY DELTA ≤ +1
- LAB QUERY DELTA ≤ +2 (achieved +1)
- N+1 = 0
- R17 truth identical (عود ملكي مركز 5/945/0/price 5/visits 5; عنبر ليلي 4/596/0/shipping 4/visits 4; طقم العناية الفاخر 4/996/0/no visit truth; missing-name degraded)
- Normal merchant: no `ProductSignalEvent` SQL; exposure `NOT_STORED`; zero visits not invented
- Tenant filter on every source (`store_slug = :slug`; abandoned carts also `store_id` when present)

**PERFORMANCE DEBT STATUS: CLOSED**  
**READY FOR CLEAN CANDIDATE: YES** (code+tests+docs; not a product release)  
**READY FOR EXACT-SHA DEPLOY: NO**  
**DEPLOY: NO**
