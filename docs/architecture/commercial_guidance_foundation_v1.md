# CartFlow Commercial Guidance Foundation V1

**Status:** Governed platform layer (architecture + runtime)  
**Date (UTC):** 2026-07-21  
**Authority:** Subordinate to [`guidance_eligibility_foundation_v1.md`](guidance_eligibility_foundation_v1.md).  
**Audience:** Product, engineering, architecture  
**Explicitly out of scope:** AI advice, root-cause claims, merchant UI, routing, presentation, automatic actions, WhatsApp/Widget changes, Home/Dashboard integration

> **Law:** Commercial Guidance answers only *what guidance CartFlow is permitted to produce from an eligible knowledge state*.  
> Eligible ≠ unrestricted. Guidance must never exceed supporting knowledge.  
> Input contract: Guidance Eligibility only (`knowledge_context` included).

---

## 0. Purpose

Convert a governed eligibility evaluation into one canonical **commercial guidance record** per subject scope — deterministic, abstention-capable, claim-bounded.

| This layer does | This layer must never |
|-----------------|------------------------|
| Select a registered guidance key | Invent causes or certainty |
| Preserve eligibility + knowledge lineage | Execute merchant actions |
| Separate known / unknown / prohibited | Generate free-form advice |
| Refresh/recompute with supersession | Rank products or score health |
| Abstain with explicit rationale | Render UI or route surfaces |

---

## 1. Placement

```text
Guidance Eligibility  ✅
        ↓
Commercial Guidance  ← THIS LAYER
        ↓
Guidance Routing → Presentation → Decision  (future)
```

---

## 2. Ownership

| Concern | Owner |
|---------|-------|
| Permitted guidance records + registry | Commercial Guidance |
| Eligibility permission + knowledge_context | Guidance Eligibility |
| Merchant wording / placement | Presentation (future) |
| Execution | Merchant Decision / Action (future) |

---

## 3. Input contract

Only `evaluate_guidance_eligibility_v1` / its evaluation records:

- `eligibility_id`, `eligibility_status`, `eligibility_reason`
- `blocking_conditions`, `knowledge_ids`
- `knowledge_context[]` — type, statement, facets (`metric_key`, `trend_direction`, `gap_key`)
- `contract_version`, fingerprints, subject grain, `as_of`

No direct reads of Knowledge / Confidence / Assembly / Metrics / Trends / Signals / providers.

---

## 4. Output contract

| Field group | Fields |
|-------------|--------|
| Identity | `guidance_id`, `store_slug`, `subject_type`, `subject_id`, `guidance_key`, `guidance_version`, `guidance_scope` |
| Lineage | `eligibility_id`, `eligibility_status`, `knowledge_reference_ids`, `source_contract_version`, `rule_version` |
| Meaning | `guidance_status`, `rationale_code`, `rationale_summary`, `known_facts`, `unknown_facts`, `prohibited_claims` |
| Lifecycle | `valid_from`, `valid_until`, `generated_at`, `refreshed_at`, `superseded_at`, `is_current` |
| Determinism | `input_fingerprint`, `guidance_fingerprint`, `generation_version`, `as_of` |

Versions: `cgf_v1` / `cgf_v1_gen` / registry `cgf_reg_v1`.

---

## 5. Registry

Code-owned registry in `commercial_guidance_registry_v1.py`. Each type declares:

- key, definition, permitted eligibility statuses
- required knowledge types / facets
- prohibited blocking conditions
- max claim strength, default validity days, default unknowns
- rule version, active flag

V1 keys: `continue_observing`, `investigate_conversion_path`, `review_product_experience`, `review_cart_progression`, `verify_evidence_gap`, `monitor_new_pattern`, `defer_until_more_evidence`, `no_guidance`.

---

## 6. Rule evaluation (deterministic priority)

First matching active rule wins (eligible path). Non-`eligible` always yields `no_guidance` / `abstained` with rationale = eligibility status (or explicit block).

Eligible priority:

1. purchase gap + cart/checkout intent trends → `investigate_conversion_path`
2. any `newly_appeared` trend → `monitor_new_pattern`
3. cart abandonment / progression metrics → `review_cart_progression`
4. product subject with cart activity → `review_product_experience`
5. any evidence gap → `verify_evidence_gap`
6. quality + trend present → `continue_observing`
7. else → `defer_until_more_evidence`

No AI. Same input → same key, rationale, refs, fingerprints.

---

## 7. Claim boundaries

Every record must include:

- **known_facts** — statements from eligibility `knowledge_context`
- **unknown_facts** — registry defaults (e.g. no proven cause)
- **prohibited_claims** — causal / action claims not justified

---

## 8. Statuses

`active` | `deferred` | `abstained` | `expired` | `superseded`

One `is_current=true` record per `(store_slug, subject_type, subject_id, guidance_scope)`.

---

## 9. Refresh / recompute

- Refresh evaluates current eligibility; identical input → idempotent upsert; material change → supersede prior current.
- Recompute is store-scoped, versioned, never deletes history.
- Kill switch `CARTFLOW_COMMERCIAL_GUIDANCE_FOUNDATION_V1=0` skips writes.

---

## 10. Runtime

- `commercial_guidance_*` modules under `services/product_data/`
- Model `CommercialGuidanceRecord` / table `commercial_guidance_records`
- Alembic `b1c2d3e4f5a6`
- Probe `GET /dev/commercial-guidance?store=demo`

---

## 11. Forbidden / future

Forbidden in V1: AI, UI, routing, actions, ranking, provider logic.  
Future: Guidance Routing and Merchant Presentation consume this contract only after review.
