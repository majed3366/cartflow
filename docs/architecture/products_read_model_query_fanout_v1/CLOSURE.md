# PRODUCTS_READ_MODEL_QUERY_FANOUT_V1 — closure proof

**Date (UTC):** 2026-09-09  
**PERFORMANCE DEBT STATUS:** CLOSED IN PRODUCTION  
**RUNTIME CANDIDATE SHA:** `57fa657093d55ea481240d8f56128911642ff0f6`  
**DEPLOYMENT ID:** `00c00a30-279a-4164-9c78-c093fab004dd`  
**POST-DEPLOY LIVE SHA:** `57fa657093d55ea481240d8f56128911642ff0f6`  
**GENERAL RELEASE:** NO  
**DEPLOY:** YES (API exact-SHA only; Scheduler untouched)

See [`PRODUCTION_PROOF.json`](PRODUCTION_PROOF.json) and [`QUERY_PLAN_PROOF.md`](QUERY_PLAN_PROOF.md).

## Invariants preserved

- `product_read_model_contract_v1` remains authoritative owner
- Product order = existing readability sort (not a ranker)
- Identity / price / cart count / cart value / purchase / revenue / hesitation unchanged
- Lab exposure LAB-ONLY; normal merchants `NOT_STORED`
- Unique visitor claims = 0; product-scoped causal claims = 0
- Missing-name degraded identity safe
- Tenant isolation on every source
- COL / OGL / Mission Catalog / CDC / Portfolio / Home / Workspace / Carts / Scheduler / UI: **NO**

## Consolidation

Independent CTEs (catalog, unique cart pairs, carts, purchases, hesitation, optional lab visits) then one `LEFT JOIN` to one row per product. Normal SQL body never names `product_signal_events`.

Loader: `services/products_commercial_truth_v1/load_consolidated_v1.py`  
Compose still owns presentation: `compose_v1.py`

## Gates

`tests/test_products_read_model_query_fanout_closure_v1.py`  
plus existing Products V1 / V1.1 / V1.2 truth tests (query-count ceilings updated to ≤ +1 / ≤ +2).

See [`README.md`](README.md) and [`MEASUREMENTS.md`](MEASUREMENTS.md).
