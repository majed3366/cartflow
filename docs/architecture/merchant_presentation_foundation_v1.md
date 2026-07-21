# CartFlow Merchant Presentation Foundation V1

**Status:** Governed platform layer (architecture + runtime)  
**Date (UTC):** 2026-07-21  
**Authority:** Subordinate to [`guidance_routing_foundation_v1.md`](guidance_routing_foundation_v1.md).  
**Audience:** Product, engineering, architecture  
**Explicitly out of scope:** Home redesign, page layout, Design System cards, notifications, automatic actions, AI wording, Surface Composition, merchant action execution

> **Law:** Merchant Presentation answers only *how a routed guidance item may be represented to the merchant*.  
> Routing decides where; Presentation decides representation; Composition later decides page placement.  
> Home validates the reusable contract — Home does not own it.  
> Input: Guidance Routing only (`presentation_context` included).

---

## 0. Purpose

Convert each eligible (and governed blocked/deferred) Guidance Route into one canonical **presentation contract** — deterministic templates, claim-bounded, cross-surface reusable.

| This layer does | This layer must never |
|-----------------|------------------------|
| Select presentation type + slots | Rewrite guidance meaning |
| Render code-owned templates | Infer root cause / revenue |
| Preserve known/unknown/prohibited | Execute actions |
| Classify action affordances | Own page layout |
| Account every expected presentation | Use AI / free-form text |

---

## 1. Placement

```text
Guidance Routing ✅
        ↓
Merchant Presentation  ← THIS LAYER
        ↓
Reusable Surface Composition → Home validation (future)
```

---

## 2. Input / output

**Input:** `generate_guidance_routes_v1` routes with `presentation_context`  
(known_facts, unknown_facts, prohibited_claims, evidence_state).

**Output:** `merchant_presentations` rows / dicts with route lineage, presentation_type, content slots, affordance, fingerprints, lifecycle.

Versions: `mpf_v1` / `mpf_v1_gen` / registries `mpres_v1` / `mtpl_v1`.

---

## 3. Registries

- **Presentation Registry** — maps surface × scope × role × guidance_key × route_status → type, slots, affordance
- **Template Registry** — keyed templates with required/optional variables, versions, max lengths

No page-controller presentation logic.

---

## 4. Types / states / affordances

Types: `executive_summary`, `decision_prompt`, `operational_notice`, `monitoring_state`, `evidence_gap_state`, `follow_up_context`, `configuration_context`, `abstention_state`

States: `ready`, `monitoring`, `insufficient_evidence`, `deferred`, `blocked`, `expired`, `superseded`, `failed`

Affordances: `none`, `navigate`, `review`, `inspect`, `configure`, `acknowledge` — never execute.

---

## 5. Accounting

```text
expected presentations
= ready + monitoring + insufficient_evidence + deferred + blocked + expired + failed
```

Eligible routes always accounted. Blocked/deferred may yield calm state presentations on permitted surfaces. Ineligible routes produce no normal presentation.

---

## 6. Runtime

- `merchant_presentation_*` under `services/product_data/`
- Table `merchant_presentations` / Alembic `d3e4f5a6b7c8`
- Flag `CARTFLOW_MERCHANT_PRESENTATION_FOUNDATION_V1`
- Probe `GET /dev/merchant-presentation?store=demo`

---

## 7. Forbidden / future

Forbidden: UI rollout, composition, actions, AI, ranking.  
Future: Surface Composition binds contracts into pages after review.
