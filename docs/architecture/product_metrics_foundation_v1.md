# CartFlow Product Metrics Foundation V1

**Status:** Governed platform layer (architecture + runtime)  
**Date (UTC):** 2026-07-20  
**Authority:** Subordinate to [`product_performance_domain_model_v1.md`](product_performance_domain_model_v1.md) and [`product_signal_collection_v1.md`](product_signal_collection_v1.md). Compatible with Commerce Evidence, Product Identity Foundation, Merchant Trust, Time Authority, Executive Knowledge (as a **consumer**, never a writer of guidance).  
**Audience:** Product, engineering, architecture  
**Explicitly out of scope:** Product Trends, Product Health, Product Ranking, Product Opportunity, Performance Score, Decision Engine, Executive summaries, merchant guidance, AI interpretation, dashboard / Home presentation, new merchant UI

> **Law:** Signals answer *what happened*. Metrics answer *how much happened*.  
> Do not infer meaning. Do not explain why. Do not generate merchant advice.  
> Every future Product Performance capability must consume metrics from this layer — not recompute counts from raw events or UI state.

---

## 0. Purpose

Product Metrics Foundation transforms **canonical Product Signals** into **governed Product Metrics** — measurable business facts with one canonical definition each.

| This layer does | This layer must never |
|-----------------|------------------------|
| Count / aggregate signal facts into named metrics | Infer trends, health, opportunity, or rank |
| Own metric definitions + calculation | Read UI state or dashboard projections |
| Persist deterministic materializations | Emit decisions, recommendations, or copy |
| Support windows, recomputation, future rollups | Duplicate metric formulas elsewhere |

**Relationship to Product Signal Collection:** Signals are the only input. Metrics never re-parse widget payloads, cart UI, or dashboard snapshots.

**Relationship to Product Performance Domain:** Metrics are the quantitative substrate that later Activity / Interest / Purchase / Snapshot facets and Executive Knowledge may cite. Domain interpretation (why / meaning) is **not** this layer.

---

## 1. Placement

```text
Product Signal Collection   (atomic facts — product_signal_events)
        ↓
Product Metrics Foundation  ← THIS LAYER (how much — product_metric_values)
        ↓
Product Performance Domain facets / Trends / Health / Ranking / Decision / Surfaces
        (future consumers only)
```

---

## 2. Canonical metric catalog

### 2.1 Families

| Family | Code | Meaning |
|--------|------|---------|
| Interest Metrics | `interest_metrics` | How many interest signals occurred |
| Cart Metrics | `cart_metrics` | How many cart-activity signals occurred |
| Checkout Metrics | `checkout_metrics` | How many checkout-activity signals occurred |
| Purchase Metrics | `purchase_metrics` | How many purchase signals occurred |
| Recovery Metrics | `recovery_metrics` | How many recovery-interaction signals occurred |
| Return Metrics | `return_metrics` | How many customer-return signals occurred |
| Evidence Metrics | `evidence_metrics` | How many evidence-link signals occurred |

### 2.2 Metric keys (V1 — counts only)

| `metric_key` | Family | Source `signal_type`(s) | Definition |
|--------------|--------|-------------------------|------------|
| `interest_hesitation_count` | interest_metrics | `product_interest_hesitation` | Count of interest-hesitation signals |
| `cart_added_count` | cart_metrics | `product_cart_added` | Count of cart-added signals |
| `cart_removed_count` | cart_metrics | `product_cart_removed` | Count of cart-removed signals |
| `cart_synced_count` | cart_metrics | `product_cart_synced` | Count of cart-synced signals |
| `cart_abandoned_count` | cart_metrics | `product_cart_abandoned` | Count of cart-abandoned signals |
| `checkout_touched_count` | checkout_metrics | `product_checkout_touched` | Count of checkout-touched signals |
| `purchase_count` | purchase_metrics | `product_purchased` | Count of purchase signals |
| `recovery_started_count` | recovery_metrics | `product_recovery_started` | Count of recovery-started signals |
| `recovery_progressed_count` | recovery_metrics | `product_recovery_progressed` | Count of recovery-progressed signals |
| `customer_return_count` | return_metrics | `product_customer_returned` | Count of customer-return signals |
| `evidence_linked_count` | evidence_metrics | `product_evidence_linked` | Count of evidence-linked signals |

**V1 forbids:** rates, ratios, conversion %, ranks, scores, deltas labeled “trend”, or any derived “health” field.

Exposure / View signal types remain deferred in Signal Collection; corresponding metrics are catalogued only when those signals wire.

### 2.3 Grain

| Grain | `stable_identity_key` | Meaning |
|-------|----------------------|---------|
| Product | non-empty identity key | Metric for one Product Identity in one store |
| Store | empty string `""` | Store-scoped total across all identities for that metric |

---

## 3. Metric definitions (contract)

Every metric row / computation result must expose:

| Field | Meaning |
|-------|---------|
| `metric_key` | Canonical key from §2.2 |
| `metric_family` | Family code from §2.1 |
| `store_slug` | Merchant scope (required) |
| `stable_identity_key` | Product grain or `""` for store grain |
| `window_code` | `all` \| `day` \| `week` \| `month` |
| `window_start` / `window_end` | Naive UTC bounds; null for `all` |
| `value` | Non-negative integer count |
| `source_signal_types` | Declared source types (catalog) |
| `computation_version` | Formula version string (`pmf_v1_count`) |
| `content_hash` | Deterministic hash of inputs + definition |

---

## 4. Ownership

| Concern | Owner |
|---------|-------|
| Metric catalog + formulas | Product Metrics Foundation (`services/product_data/product_metrics_*`) |
| Signal facts | Product Signal Collection (`product_signal_events`) |
| Product identity keys | Product Identity Foundation / PDF |
| Time window boundaries | Time Authority (naive UTC; window helpers in this layer) |
| Trends / health / ranking / decisions | Future foundations (must not redefine counts) |
| Surfaces | Home / Dashboard / Reports (consumers only) |

**Calculation ownership law:** Only `product_metrics_foundation_v1` (and its catalog module) may define how a `metric_key` is computed. Callers request metrics; they do not re-implement `COUNT(*)`.

---

## 5. Signal → Metric mapping

```text
product_interest_hesitation  → interest_hesitation_count
product_cart_added           → cart_added_count
product_cart_removed         → cart_removed_count
product_cart_synced          → cart_synced_count
product_cart_abandoned       → cart_abandoned_count
product_checkout_touched     → checkout_touched_count
product_purchased            → purchase_count
product_recovery_started     → recovery_started_count
product_recovery_progressed  → recovery_progressed_count
product_customer_returned    → customer_return_count
product_evidence_linked      → evidence_linked_count
```

Mapping is **1 signal_type → 1 metric_key** in V1 (bijective for wired types). Multi-signal metrics are reserved for a future catalog revision with a new `computation_version`.

---

## 6. Aggregation strategy

1. **Filter** `product_signal_events` by `store_slug` and optional `observed_at` window.
2. **Group** by `(stable_identity_key, signal_type)`.
3. **Map** `signal_type` → `metric_key` via catalog.
4. **Emit** product-grain rows (`value = count`).
5. **Roll up** store-grain rows by summing product-grain values per `metric_key` (equivalent to counting signals without identity split).
6. **Omit** zero-value product rows unless explicitly requested; store-grain zeros may be emitted for catalog completeness on probe.

Aggregation is **additive counts only**. No averages, percentiles, or unique-session inventiveness in V1 (unique-session metrics would be a new catalog entry with explicit definition).

---

## 7. Refresh strategy

| Mode | When | Behavior |
|------|------|----------|
| **On-demand compute** | Probe / consumer / verify script | Read signals → compute metrics in memory (always allowed) |
| **Materialize** | Explicit `materialize_product_metrics_v1` | Upsert `product_metric_values` for store×window |
| **Kill switch** | `CARTFLOW_PRODUCT_METRICS_FOUNDATION_V1=0` | Skip materialize; compute may still read for diagnostics when forced |

Hot-path cart-event hooks **do not** write metrics (avoids coupling collection latency). Refresh is batch/on-demand.

---

## 8. Historical recomputation strategy

1. Select signals for `store_slug` and window bounds.
2. Re-run the same `pmf_v1_count` formulas.
3. Upsert materialization rows keyed by `(store_slug, stable_identity_key, metric_key, window_code, window_start, window_end)`.
4. `content_hash` changes only when inputs or `computation_version` change — enabling idempotent verification.

Past materializations for the same key are replaced (upsert), not version-chained in V1. Future archiving may soft-retain superseded rows; V1 does not require archive tables.

---

## 9. Integration with Product Signal Collection

| Rule | Detail |
|------|--------|
| Input table | `product_signal_events` only |
| Schema ensure | Depends on PSC `ensure_product_signal_events_schema` |
| Flag independence | Metrics flag does not disable signal collection |
| Store isolation | All reads/writes filter `store_slug` |
| Evidence | Metrics may cite signal counts; they do not invent evidence refs |

Runtime modules:

- `product_metrics_types_v1.py` — catalog
- `product_metrics_flag_v1.py` — kill switch
- `product_metrics_foundation_v1.py` — compute + materialize
- `product_metrics_prod_probe_v1.py` — Demo diagnostic
- `schema_product_metric_values_v1.py` — ensure table
- Model `ProductMetricValue` → `product_metric_values`
- Alembic `v5w6x7y8z9a0`

---

## 10. Future extension points

| Extension | Constraint |
|-----------|------------|
| Exposure / View metrics | Add only after PSC wires those signal types |
| Unique session / cart metrics | New `metric_key` + `computation_version`; never overload count keys |
| Rollup tables (daily store cubes) | New table; formulas still owned here |
| Archive / cold storage | Export materializations; recompute remains possible from signals |
| Trends / Health / Ranking | Separate foundations consuming these metrics |
| Executive Knowledge | Cite metric keys + windows; never redefine formulas |

---

## 11. Production validation

- Deploy runtime + migration/ensure.
- Demo Merchant: materialize metrics from existing Demo signals.
- Run compute twice; require identical canonical payloads (`deterministic=true`).
- Smoke Home / health — no new merchant UI.

Evidence: `docs/product/PRODUCT_METRICS_FOUNDATION_V1_PROD_CLOSURE_EVIDENCE.md` (when closed).

---

## 12. Acceptance checklist

| Criterion | Status |
|-----------|--------|
| Governed platform layer | Yes — this doc + runtime |
| One canonical definition per metric | Yes — §2.2 / catalog module |
| Consume only Product Signals | Yes — §9 |
| Ownership documented | Yes — §4 |
| Signal → Metric mapping documented | Yes — §5 |
| No trend / decision / presentation | Yes — out of scope |
| Deterministic generation | Yes — `pmf_v1_count` + content hash |
