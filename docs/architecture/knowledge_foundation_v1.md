# CartFlow Knowledge Foundation V1

**Status:** Governed platform layer (architecture + runtime)  
**Date (UTC):** 2026-07-21  
**Authority:** Subordinate to [`evidence_confidence_foundation_v1.md`](evidence_confidence_foundation_v1.md) and [`product_performance_domain_model_v1.md`](product_performance_domain_model_v1.md).  
**Audience:** Product, engineering, architecture  
**Explicitly out of scope:** Merchant recommendations, decisions, root-cause analysis, product health scoring, opportunity ranking, action / next-best-action generation, dashboard/Home UI, AI reasoning

> **Law:** Knowledge answers only *what CartFlow can truthfully state based on high-confidence evidence*.  
> Knowledge is observation — not advice, not recommendation, not decision.  
> Inputs are Evidence Confidence evaluations only.

---

## 0. Purpose

Transform evaluated evidence into **canonical knowledge statements** that are deterministic, factual, and always linked to a `confidence_id`.

| This layer does | This layer must never |
|-----------------|------------------------|
| Emit factual observation statements | Recommend actions or decide |
| Require confidence linkage on every record | Read Signals/Metrics/Trends/Assembly/providers |
| Version + fingerprint statements | Score product health or rank opportunity |
| Refresh/recompute idempotently | Generate Home/Dashboard UI |

---

## 1. Placement

```text
Evidence Confidence
        ↓
Knowledge Foundation  ← THIS LAYER
        ↓
Commercial Guidance  (future)
```

---

## 2. Ownership

| Concern | Owner |
|---------|-------|
| Statement templates + knowledge types | Knowledge Foundation (`knowledge_foundation_*`) |
| Confidence evaluations (+ `evidence_summary` digest) | Evidence Confidence |
| Guidance / actions | Commercial Guidance (future) |

---

## 3. Statement specification

### 3.1 Knowledge types

| `knowledge_type` | Meaning |
|------------------|---------|
| `evidence_quality` | Statement about confidence level of the evaluation |
| `metric_trend_observation` | Statement about a metric trend from confidence `evidence_summary` |
| `evidence_gap` | Statement about missing core sources noted by confidence |
| `evidence_conflict_flag` | Statement that conflicting signals were flagged (flag only) |

### 3.2 Record fields

| Field | Meaning |
|-------|---------|
| `knowledge_id` | Deterministic id |
| `store_slug` | Merchant scope |
| `subject_type` / `subject_id` | From confidence evaluation |
| `knowledge_type` | Enum above |
| `statement` | Factual English observation string |
| `evidence_confidence_id` | Required FK-style ref to confidence evaluation |
| `confidence_level` | Copied from evaluation |
| `valid_from` / `valid_until` | Validity window (naive UTC) |
| `generated_at` | Generation clock |
| `knowledge_version` | `kf_v1` |
| `fingerprint` | Content hash |
| `assembly_window` | Window from confidence summary |

### 3.3 High-confidence gate

Metric/trend observation statements are emitted only when `confidence_level` ∈ {`high`, `very_high`}.

`evidence_quality` statements are always emitted when an evaluation exists.

---

## 4. Statement templates (deterministic)

Window labels: `today`→"today", `d7`→"the last 7 days", `d30`→"the last 30 days", `d90`→"the last 90 days".

Metric labels (catalog): e.g. `cart_added_count`→"Cart additions", `evidence_linked_count`→"Evidence-linked events".

| Trend | Template |
|-------|----------|
| `newly_appeared` | "{label} have newly appeared during {window}." |
| `increasing` | "{label} are increasing during {window}." |
| `decreasing` | "{label} are decreasing during {window}." |
| `disappeared` | "{label} have disappeared during {window}." |
| `stable` | "{label} are stable during {window}." |

Quality: `"Evidence quality is {confidence_level}."`  
Gap: `"Evidence does not include {metric_key}."`  
Conflict: `"Conflicting signals were flagged in the evidence evaluation."`

---

## 5. Lifecycle / versioning / refresh

| Mode | Behavior |
|------|----------|
| Same `as_of` + same `knowledge_id` | Upsert — idempotent |
| New `as_of` | New knowledge ids; prior rows untouched |
| Kill switch | `CARTFLOW_KNOWLEDGE_FOUNDATION_V1=0` skips materialize |

`knowledge_version = kf_v1`. Template changes require a new version.

---

## 6. Traceability

Every knowledge record **must** include `evidence_confidence_id`.  
Fingerprint covers statement + confidence id + type + subject + window + as_of.

---

## 7. Runtime

- `knowledge_foundation_types_v1.py`
- `knowledge_foundation_flag_v1.py`
- `knowledge_foundation_v1.py`
- `knowledge_foundation_prod_probe_v1.py`
- `schema_knowledge_foundation_v1.py`
- Model `KnowledgeStatement`
- Alembic `z9a0b1c2d3e4`
- Probe: `GET /dev/knowledge-foundation?store=demo`

ECF additive: evaluations include `evidence_summary` (factual item digest) for Knowledge input without PEA reads.
