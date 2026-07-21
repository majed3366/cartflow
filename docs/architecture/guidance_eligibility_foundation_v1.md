# CartFlow Guidance Eligibility Foundation V1

**Status:** Governed platform layer (architecture + runtime)  
**Date (UTC):** 2026-07-21  
**Authority:** Subordinate to [`knowledge_foundation_v1.md`](knowledge_foundation_v1.md) and [`product_performance_domain_model_v1.md`](product_performance_domain_model_v1.md).  
**Audience:** Product, engineering, architecture  
**Explicitly out of scope:** Merchant recommendations, Decision Engine, root-cause analysis, opportunity ranking, product health, AI reasoning, dashboard/Home UI, Commercial Guidance generation

> **Law:** Eligibility answers only *whether CartFlow is allowed to generate commercial guidance*.  
> It governs permission — not content.  
> Inputs are Knowledge Foundation statements only.

---

## 0. Purpose

Produce one canonical **eligibility evaluation** per subject from current knowledge, deciding if Commercial Guidance may run later.

| This layer does | This layer must never |
|-----------------|------------------------|
| Emit `eligible` / blocking statuses | Generate guidance or actions |
| List blocking conditions factually | Read Confidence/Assembly/Metrics/… |
| Version + fingerprint evaluations | Rank products or score health |
| Refresh/recompute idempotently | Render UI |

---

## 1. Placement

```text
Knowledge Foundation
        ↓
Guidance Eligibility  ← THIS LAYER
        ↓
Commercial Guidance  (future — only if eligible)
```

---

## 2. Ownership

| Concern | Owner |
|---------|-------|
| Eligibility rules + statuses | Guidance Eligibility (`guidance_eligibility_*`) |
| Knowledge statements | Knowledge Foundation |
| Guidance content | Commercial Guidance (future) |

---

## 3. Eligibility contract

| Field | Meaning |
|-------|---------|
| `eligibility_id` | Deterministic id |
| `store_slug` | Merchant scope |
| `subject_type` / `subject_id` | Subject grain |
| `eligibility_status` | One of §4 |
| `eligibility_reason` | Factual machine reason string |
| `knowledge_count` | Statements considered for subject |
| `required_knowledge_count` | Minimum required (V1 = 2) |
| `blocking_conditions` | Ordered list of block codes |
| `knowledge_ids` | Trace refs to knowledge statements |
| `evaluated_at` / `as_of` | Naive UTC |
| `eligibility_version` | `gef_v1` |
| `fingerprint` | Content hash |

---

## 4. Status lifecycle (single active status)

Priority order (first match wins):

| Priority | Status | Condition |
|---------:|--------|-----------|
| 1 | `pending_observation` | No knowledge statements for subject |
| 2 | `expired_knowledge` | Any statement `valid_until` < evaluation `as_of` |
| 3 | `conflicting_knowledge` | Any `evidence_conflict_flag` statement |
| 4 | `insufficient_confidence` | Quality statement `confidence_level` ∉ {high, very_high} |
| 5 | `insufficient_knowledge` | Missing `evidence_quality` and/or `metric_trend_observation`, or count < required |
| 6 | `eligible` | All checks pass |

Only one status is active per subject at evaluation time.

---

## 5. Blocking condition codes

| Code | Meaning |
|------|---------|
| `no_knowledge` | Zero statements |
| `expired_knowledge` | Validity window ended |
| `conflict_flag_present` | Conflict knowledge present |
| `confidence_below_high` | Quality confidence not high/very_high |
| `missing_evidence_quality` | No quality knowledge |
| `missing_trend_observation` | No metric trend observation |
| `below_required_count` | knowledge_count < required |

---

## 6. Required knowledge (V1)

`required_knowledge_count = 2`:

1. At least one `evidence_quality` statement  
2. At least one `metric_trend_observation` statement  

Both must be non-expired at `as_of`.

---

## 7. Refresh / versioning

| Mode | Behavior |
|------|----------|
| Same `as_of` + same `eligibility_id` | Upsert — idempotent |
| New `as_of` | New evaluation grain; prior rows untouched |
| Kill switch | `CARTFLOW_GUIDANCE_ELIGIBILITY_V1=0` skips materialize |

`eligibility_version = gef_v1`. Rule changes require a new version.

---

## 8. Runtime

- `guidance_eligibility_types_v1.py`
- `guidance_eligibility_flag_v1.py`
- `guidance_eligibility_foundation_v1.py`
- `guidance_eligibility_prod_probe_v1.py`
- `schema_guidance_eligibility_v1.py`
- Model `GuidanceEligibilityEvaluation`
- Alembic `a0b1c2d3e4f5`
- Probe: `GET /dev/guidance-eligibility?store=demo`
