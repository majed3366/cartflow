# CartFlow Product Trends Foundation V1

**Status:** Governed platform layer (architecture + runtime)  
**Date (UTC):** 2026-07-20  
**Authority:** Subordinate to [`product_metrics_foundation_v1.md`](product_metrics_foundation_v1.md) and [`product_performance_domain_model_v1.md`](product_performance_domain_model_v1.md).  
**Audience:** Product, engineering, architecture  
**Explicitly out of scope:** Recommendations, ranking, product health, scoring, confidence, AI, knowledge generation, root-cause analysis, dashboard redesign, Home integration, merchant guidance, Decision Engine

> **Law:** Trends answer only *how metrics are changing over time*.  
> They do not explain why. They do not advise. They do not rank.  
> Inputs are canonical Product Metrics only — never raw commerce events, never provider schemas.

---

## 0. Purpose

Product Trends Foundation detects **governed temporal change** between two equal-length metric windows (current vs previous).

| This layer does | This layer must never |
|-----------------|------------------------|
| Compare metric values across adjacent windows | Infer cause or opportunity |
| Emit direction labels (increase/decrease/…) | Rank products or score health |
| Persist deterministic trend records | Read UI / dashboard / provider payloads |
| Support refresh / recompute | Bypass Metrics to re-aggregate signals |

---

## 1. Placement

```text
Product Signal Collection
        ↓
Product Metrics Foundation   (how much)
        ↓
Product Trends Foundation    ← THIS LAYER (how changing)
        ↓
Evidence Assembly → Confidence → Knowledge → Guidance   (future)
```

**No layer may bypass another.** Trends call the Metrics compute API only.

---

## 2. Trend directions (canonical)

| `trend_direction` | Rule (integer metric values) |
|-------------------|------------------------------|
| `newly_appeared` | previous = 0 and current > 0 |
| `disappeared` | previous > 0 and current = 0 |
| `stable` | current = previous |
| `increasing` | current > previous (and previous > 0) |
| `decreasing` | current < previous (and current > 0) |

Priority is evaluated in that order so appearance/disappearance are not collapsed into increase/decrease.

**Never emit:** “improving”, “at risk”, “opportunity”, ranks, scores, or prose explanations.

---

## 3. Trend windows

| `trend_window` | Current metric window | Previous metric window | Metrics `window_code` |
|----------------|----------------------|------------------------|------------------------|
| `today` | [as_of−1d, as_of) | [as_of−2d, as_of−1d) | `day` |
| `d7` | [as_of−7d, as_of) | [as_of−14d, as_of−7d) | `week` |
| `d30` | [as_of−30d, as_of) | [as_of−60d, as_of−30d) | `month` |
| `d90` | [as_of−90d, as_of) | [as_of−180d, as_of−90d) | `d90` |

`as_of` is naive UTC, fixed once per compute for determinism.

---

## 4. Metric coverage

Trends are computed for **every** Product Metrics Foundation V1 `metric_key` (store grain and product grain), including:

- `cart_added_count`
- `cart_abandoned_count` (canonical abandonment count — not a separate `abandonment_count` key)
- `purchase_count`
- `evidence_linked_count`
- …and the full PMF catalog

---

## 5. Trend record contract

| Field | Meaning |
|-------|---------|
| `store_slug` | Merchant scope |
| `stable_identity_key` | Product grain or `""` store grain |
| `metric_key` | Canonical PMF metric |
| `trend_window` | `today` \| `d7` \| `d30` \| `d90` |
| `as_of` | Comparison anchor (naive UTC) |
| `current_value` / `previous_value` | Integer metric values |
| `delta_abs` | `current_value - previous_value` |
| `trend_direction` | One of §2 |
| `computation_version` | `ptf_v1_delta` |
| `content_hash` | Deterministic hash of factual fields |

---

## 6. Ownership

| Concern | Owner |
|---------|-------|
| Trend catalog + direction rules | Product Trends Foundation (`product_trends_*`) |
| Metric values | Product Metrics Foundation only |
| Signal facts | Product Signal Collection (upstream of Metrics) |
| Why / guidance / ranking | Future layers |

---

## 7. Aggregation / refresh / recompute

1. Fix `as_of`.
2. Call `compute_product_metrics_v1` for current window (`as_of`).
3. Call `compute_product_metrics_v1` for previous window (`as_of` shifted back by window length).
4. Diff store-grain and product-grain metric maps → trend records.
5. Optional `materialize_product_trends_v1` upserts `product_trend_values`.

Kill switch: `CARTFLOW_PRODUCT_TRENDS_FOUNDATION_V1=0` skips materialize.

---

## 8. Determinism

Same store + same `as_of` + same metrics inputs → identical `canonical_fingerprint` and `content_hash` values. Probe verifies two computes with the same frozen `as_of`.

---

## 9. Runtime modules

- `product_trends_types_v1.py`
- `product_metrics` extension: `WINDOW_D90` / `d90` for 90-day metric windows
- `product_trends_flag_v1.py`
- `product_trends_foundation_v1.py`
- `product_trends_prod_probe_v1.py`
- `schema_product_trend_values_v1.py`
- Model `ProductTrendValue` → `product_trend_values`
- Alembic `w6x7y8z9a0b1`
- Probe `GET /dev/product-trends-foundation`

---

## 10. Acceptance

| Criterion | Requirement |
|-----------|-------------|
| Deterministic | Fingerprint equality |
| Canonical ownership | Trends own directions; Metrics own counts |
| Refresh/recompute | On-demand compute + materialize |
| Provider-independent | Metrics API only |
| Documented | This file |
| Production probe + evidence | Deploy verification + closure doc |
