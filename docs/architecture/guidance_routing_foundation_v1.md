# CartFlow Guidance Routing Foundation V1

**Status:** Governed platform layer (architecture + runtime)  
**Date (UTC):** 2026-07-21  
**Authority:** Subordinate to [`commercial_guidance_foundation_v1.md`](commercial_guidance_foundation_v1.md).  
**Audience:** Product, engineering, architecture  
**Explicitly out of scope:** Merchant Presentation, Home/Carts/Communication/Settings UI, copy, layout, visual priority, notifications, automatic actions, AI

> **Law:** Guidance Routing answers only *on which surfaces governed commercial guidance is eligible to appear*.  
> Home is the first validation surface — not the architectural owner.  
> Input: Commercial Guidance only (`routing_context` included).

---

## 0. Purpose

For each current Commercial Guidance record, emit one canonical **route** per merchant surface — eligible, ineligible, deferred, blocked, expired, or failed with reason. No silent route loss.

| This layer does | This layer must never |
|-----------------|------------------------|
| Assign surface eligibility | Rewrite guidance meaning |
| Set route_scope / route_role | Create merchant wording |
| Preserve guidance lineage | Design cards or layout |
| Account every guidance×surface pair | Score priority or rank |
| Refresh/recompute deterministically | Execute actions |

---

## 1. Placement

```text
Commercial Guidance ✅
        ↓
Guidance Routing  ← THIS LAYER
        ↓
Merchant Presentation → Surface Composition → Home validation (future)
```

Primary surfaces: `home`, `decision_workspace`, `carts`, `communication`, `settings`.

---

## 2. Page responsibilities (preserved)

| Surface | Merchant question |
|---------|-------------------|
| Home | What should the merchant know now? |
| Decision Workspace | What decision requires reasoning/review? |
| Carts | What cart operational attention is required? |
| Communication | What communication follow-up is needed? |
| Settings | How does the merchant control configuration? |

Routing must not dump every guidance onto every surface.

---

## 3. Input contract

Only `generate_commercial_guidance_v1` records:

- identity + `guidance_key` / `guidance_status`
- `routing_context` (`cart_related`, subject, scope)
- validity, fingerprints, lineage ids

No lower-layer reads.

---

## 4. Output contract

Per guidance×surface:

`route_id`, `guidance_id`, `store_slug`, `subject_*`, `surface_key`, `route_scope`, `route_role`, `route_status`, `routing_rationale_code`, `routing_context_digest`, validity, `is_current`, versions, fingerprints, lifecycle timestamps.

Reusable fields only — never `show_on_home`, `home_card_title`, `home_priority`.

---

## 5. Registries

- **Surface registry** (`guidance_surface_registry_v1.py`) — responsibilities, accepted/prohibited scopes & subjects, statuses
- **Routing registry** (`guidance_routing_registry_v1.py`) — per guidance key: eligible surfaces, scopes, roles, priorities

Versions: `gsurf_v1`, `grule_v1`, evaluator `grf_v1_eval`.

---

## 6. Scopes / roles / statuses

Scopes: `summary`, `full_context`, `operational`, `follow_up`, `control`, `internal_only`  
Roles: `awareness`, `investigation`, `decision_support`, `operational_attention`, `communication_followup`, `configuration_context`, `suppressed`  
Statuses: `eligible`, `ineligible`, `deferred`, `blocked`, `expired`, `superseded`

---

## 7. Accounting guarantee

```text
expected_route_pairs = guidance_count × active_surfaces
= eligible + ineligible + blocked + deferred + expired + failed(explicit)
```

Surface isolation: one route materialize failure must not block other surfaces.

---

## 8. Runtime

- Modules under `services/product_data/guidance_routing_*` / `guidance_surface_*`
- Table `guidance_routes` / Alembic `c2d3e4f5a6b7`
- Flag `CARTFLOW_GUIDANCE_ROUTING_FOUNDATION_V1`
- Probe `GET /dev/guidance-routing?store=demo`

---

## 9. Forbidden / future

Forbidden: UI, copy, presentation, notifications, actions, AI, page-local routing.  
Future: Merchant Presentation consumes routes only after review.
