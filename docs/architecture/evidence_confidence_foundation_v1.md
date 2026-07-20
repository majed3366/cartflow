# CartFlow Evidence Confidence Foundation V1

**Status:** Governed platform layer (architecture + runtime)  
**Date (UTC):** 2026-07-20  
**Authority:** Subordinate to [`product_evidence_assembly_v1.md`](product_evidence_assembly_v1.md) and [`product_performance_domain_model_v1.md`](product_performance_domain_model_v1.md).  
**Audience:** Product, engineering, architecture  
**Explicitly out of scope:** Merchant recommendations, root-cause analysis, product ranking/health/scoring, knowledge generation, AI reasoning, Decision Engine, dashboard/Home UI

> **Law:** Confidence answers only *how confident CartFlow is in this assembled evidence*.  
> It evaluates evidence quality — not business meaning, not guidance.  
> Inputs are Evidence Assembly bundles only.

---

## 0. Purpose

Produce a versioned, deterministic confidence evaluation for each evidence bundle.

| This layer does | This layer must never |
|-----------------|------------------------|
| Score evidence completeness / freshness / consistency / diversity / sample size | Explain why evidence exists |
| Flag missing sources and conflicts (flag only) | Recommend actions or rank products |
| Persist evaluations keyed to `evidence_bundle_id` | Read Signals / Metrics / Trends / providers |
| Support refresh/recompute | Invent knowledge or UI |

---

## 1. Placement

```text
Evidence Assembly
        ↓
Evidence Confidence  ← THIS LAYER
        ↓
Knowledge → Commercial Guidance  (future)
```

---

## 2. Ownership

| Concern | Owner |
|---------|-------|
| Confidence formulas + levels | Evidence Confidence (`evidence_confidence_*`) |
| Evidence bundles / items | Evidence Assembly |
| Knowledge / Guidance | Future layers |

---

## 3. Evaluation factors (V1)

All factors are derived **only** from a single assembled bundle (+ its items). Scores are integers 0–100.

| Factor | Rule (deterministic) |
|--------|----------------------|
| `completeness` | % of core evidence keys present in the bundle (core catalog owned here) |
| `source_diversity` | 50 if only one originating layer; 100 if both metrics and trends lineage present |
| `consistency` | 100 if all items share bundle `trend_window` / `as_of`; else reduced; conflicts lower further |
| `sample_size` | From sum of positive `metric_value`: 0→0, 1→40, 2–4→60, 5–9→80, ≥10→100 |
| `freshness` | 100 when `observed_to`/`as_of` equals evaluation `as_of`; 70 if any item missing observed bounds; 40 if mismatched |
| `missing_sources` | Core keys absent from bundle (list) |
| `conflicting_signals` | Boolean: any item with `metric_value>0` and `trend_direction=disappeared` (or inverse edge) |

**Composite `confidence_score`:** round average of completeness, source_diversity, consistency, sample_size, freshness (equal weights).

**`confidence_level`:**

| Score | Level |
|------:|-------|
| 0–39 | `low` |
| 40–59 | `medium` |
| 60–79 | `high` |
| 80–100 | `very_high` |

**Core evidence keys (evaluation catalog):**  
`cart_added_count`, `cart_abandoned_count`, `purchase_count`, `evidence_linked_count`

---

## 4. Output contract

| Field | Meaning |
|-------|---------|
| `confidence_id` | Deterministic id (hash of bundle id + versions + as_of) |
| `evidence_bundle_id` | Source bundle |
| `store_slug` / `subject_type` / `subject_id` | Copied from bundle |
| `confidence_level` | Enum above |
| `confidence_score` | 0–100 |
| `confidence_version` | `ecf_v1` |
| `evaluator_version` | `ecf_v1_eval` |
| `evaluated_at` / `as_of` | Naive UTC |
| `factors` | completeness, freshness, consistency, source_diversity, sample_size |
| `missing_sources` | list |
| `conflicting_signals` | bool |
| `confidence_notes` | factual machine notes (not advice) |
| `content_hash` | Fingerprint of evaluation payload |

---

## 5. Refresh / recompute

| Mode | Behavior |
|------|----------|
| Same `as_of` + same bundle id | Upsert — idempotent |
| New `as_of` (new assembly) | New `confidence_id` / rows; prior evaluations untouched |
| Kill switch | `CARTFLOW_EVIDENCE_CONFIDENCE_V1=0` skips materialize |

---

## 6. Runtime

- `evidence_confidence_types_v1.py`
- `evidence_confidence_flag_v1.py`
- `evidence_confidence_foundation_v1.py`
- `evidence_confidence_prod_probe_v1.py`
- `schema_evidence_confidence_v1.py`
- Model `EvidenceConfidenceEvaluation`
- Alembic `y8z9a0b1c2d3`
- Probe: `GET /dev/evidence-confidence?store=demo`

---

## 7. Acceptance

Deterministic · Evidence-Assembly-only inputs · stable ids · versioned · refresh/recompute · production probe + evidence · STOP before Knowledge/Guidance.
