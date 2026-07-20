# CartFlow Product Evidence Assembly Foundation V1

**Status:** Governed platform layer (architecture + runtime)  
**Date (UTC):** 2026-07-20  
**Authority:** Subordinate to [`product_metrics_foundation_v1.md`](product_metrics_foundation_v1.md), [`product_trends_foundation_v1.md`](product_trends_foundation_v1.md), [`product_performance_domain_model_v1.md`](product_performance_domain_model_v1.md).  
**Audience:** Product, engineering, architecture  
**Explicitly out of scope:** Confidence, evidence weighting, strong/weak evidence, contradiction resolution, product health/ranking/scoring, Decision Engine, root-cause analysis, recommendations, knowledge generation, dashboard/Home UI, AI

> **Law:** Evidence Assembly answers only *what governed evidence exists for this product*.  
> It assembles. It never interprets.  
> Inputs are Product Metrics + Product Trends only — never Signals, never provider tables.

---

## 0. Purpose

Assemble deterministic **evidence bundles** that list factual metric and trend evidence for a subject (product identity or store), with full source lineage.

| This layer does | This layer must never |
|-----------------|------------------------|
| Join Metrics + Trends into bundles | Explain why / score / recommend |
| Preserve lineage to source layers | Read Signals / Zid / Salla / WhatsApp |
| Fingerprint bundles for equality | Weight or contradict-resolve evidence |
| Refresh/recompute idempotently | Mutate historical `as_of` rows |

---

## 1. Placement

```text
Product Signals → Product Metrics → Product Trends
                                           ↓
                         Product Evidence Assembly  ← THIS LAYER
                                           ↓
                         Confidence → Knowledge → Guidance  (future)
```

No lower layer may consume Evidence. Evidence consumes Metrics + Trends APIs only.

---

## 2. Ownership

| Concern | Owner |
|---------|-------|
| Bundle shape + assembly rules | Evidence Assembly (`product_evidence_assembly_*`) |
| Metric values | Product Metrics Foundation |
| Trend directions | Product Trends Foundation |
| Confidence / Knowledge / Guidance | Future layers |

---

## 3. Bundle specification

### 3.1 Bundle header

| Field | Meaning |
|-------|---------|
| `evidence_bundle_id` | Deterministic id (hash of grain + `as_of` + version) |
| `store_slug` | Merchant scope |
| `subject_type` | `product` \| `store` |
| `subject_id` | `stable_identity_key` or store slug |
| `bundle_version` | `pea_v1` |
| `assembled_at` | Assembly clock (naive UTC) |
| `assembly_window` | Trend window used for pairing (`today`\|`d7`\|`d30`\|`d90`) |
| `as_of` | Frozen comparison/assembly anchor |
| `source_count` | Number of evidence items |
| `fingerprint` | SHA-256 of canonical item set |

### 3.2 Evidence item

| Field | Meaning |
|-------|---------|
| `evidence_item_id` | Deterministic id |
| `metric_key` | Canonical PMF metric key |
| `metric_value` | Current metric integer (nullable if trend-only edge case) |
| `trend_direction` | PTF direction when present |
| `trend_window` | Assembly window |
| `source_layer` | `metrics` \| `trends` \| `metrics+trends` |
| `source_record_id` | Source `content_hash` (metrics and/or trends) |
| `observed_from` / `observed_to` | Window bounds (ISO naive UTC) |
| `lineage` | Structured origin refs (layer, window, timestamp, hashes) |

Items are emitted for metric keys with non-zero current metric value and/or non-stable-zero trend presence (same omit rules as Trends for empty zeros).

---

## 4. Lineage specification

Every item must retain:

| Lineage field | Source |
|---------------|--------|
| `originating_layer` | `metrics` / `trends` / both |
| `metrics_content_hash` | From Metrics row when present |
| `trends_content_hash` | From Trends row when present |
| `originating_window` | `assembly_window` / metric window code |
| `originating_as_of` | Frozen `as_of` |
| `metrics_computation_version` | e.g. `pmf_v1_count` |
| `trends_computation_version` | e.g. `ptf_v1_delta` |

No evidence item may be persisted without `source_layer` + at least one source hash.

---

## 5. Assembly algorithm

1. Fix `as_of` (floor to second).
2. `compute_product_trends_v1(store, trend_window, as_of)`.
3. `compute_product_metrics_v1(store, window_code=mapped, as_of)` for current metric window.
4. For each product identity and for store grain: merge metric + trend maps by `metric_key`.
5. Sort items by `metric_key`; build deterministic ids + bundle fingerprint.
6. Optional materialize: upsert bundle+items for `(store, subject, window, as_of_key, bundle_version)`.

---

## 6. Refresh / recompute semantics

| Mode | Behavior |
|------|----------|
| Refresh (same `as_of`) | Upsert same grain — idempotent; no duplicate rows |
| Recompute (new `as_of`) | Insert/upsert new grain — prior `as_of` rows untouched |
| Kill switch | `CARTFLOW_PRODUCT_EVIDENCE_ASSEMBLY_V1=0` skips materialize |

Historical facts for prior `as_of_key` values are never mutated by a later refresh with a different anchor.

---

## 7. Runtime

- `product_evidence_assembly_types_v1.py`
- `product_evidence_assembly_flag_v1.py`
- `product_evidence_assembly_v1.py`
- `product_evidence_assembly_prod_probe_v1.py`
- `schema_product_evidence_assembly_v1.py`
- Models: `ProductEvidenceBundle`, `ProductEvidenceItem`
- Alembic `x7y8z9a0b1c2`
- Probe: `GET /dev/product-evidence-assembly?store=demo`

---

## 8. Acceptance

Deterministic assembly · Metrics+Trends inputs only · lineage preserved · stable fingerprint · refresh-safe · recompute supported · production probe + evidence · STOP before Confidence/Knowledge/Guidance.
