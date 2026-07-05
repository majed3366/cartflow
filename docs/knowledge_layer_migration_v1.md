# CartFlow Knowledge Layer Migration V1

**Status:** Implemented — Sprint 1 of Merchant Experience Migration Program  
**Date (UTC):** 2026-07-05  
**Scope:** Phase 1 — migrate Knowledge Layer from surface-owned knowledge to governed routing consumer  
**Authority:** [`merchant_experience_migration_program_v1.md`](merchant_experience_migration_program_v1.md) Phase 1  
**Audience:** Engineering, architecture review  

---

## Executive summary

Knowledge Layer is no longer a knowledge owner. It is a **certified routing consumer** — second surface after Daily Brief to complete the full Infrastructure → Routing → Projection → UI pipeline.

Selection, ranking, aggregation, and OIA copy generation moved from `static/merchant_knowledge_layer.js` to platform layers:

```
Merchant Knowledge Infrastructure (producers + metadata)
        ↓
Knowledge Routing (`route_knowledge_layer_knowledge_v1`)
        ↓
Knowledge Layer Projection (`knowledge_layer_projection_v1`)
        ↓
Knowledge Layer UI (`merchant_knowledge_layer.js` — presentation only)
```

---

## Removed surface ownership (JS)

| Removed | Former responsibility | New owner |
|---------|----------------------|-----------|
| `INSIGHT_PRIORITY` | Static insight priority map | `routing_priority` in `knowledge_routing_v1` |
| `insightScore()` | Composite score for ranking | `compute_routing_priority_v1` |
| `pickTopInsights()` | Filter, sort, slice 3–5 cards | `flatten_kl_routed_display_items_v1` |
| `SEVERITY_RANK` / `CONF_RANK` (scoring) | Score inputs for selection | Retired with `insightScore` |
| `OIA_BUILDERS` + per-key builders | Surface-owned explanation/OIA generation | `project_kl_oia_v1` (projection layer) |
| `buildKnowledgeCardOIA()` | Orchestrate JS OIA | `project_kl_display_card_v1` |
| Local `insights` iteration for display | Surface selection from raw API | `knowledge_layer_projection_v1.display_cards` |
| `payload.insights` actionable filter | Surface eligibility | Projection empty_reason + routing eligibility |

### JS decisions audit

| Decision | Classification |
|----------|----------------|
| Fetch `/api/knowledge/report` | **KEEP** — API consumer |
| Read `knowledge_layer_projection_v1.display_cards` | **KEEP** — routed feed |
| Render OIA blocks from projected fields | **KEEP** — presentation |
| Evidence registry label lookup | **KEEP** — presentation (registry read) |
| `esc()` HTML escaping | **KEEP** — presentation safety |
| Empty state copy | **KEEP** — presentation |
| `INSIGHT_PRIORITY` | **REMOVE** — retired |
| `pickTopInsights` | **REMOVE** — retired |
| OIA builders | **MOVE TO PROJECTION** — `knowledge_layer_projection_v1.py` |
| Insight selection/sort | **MOVE TO ROUTING** — `route_knowledge_layer_knowledge_v1` |

---

## Implementation

### Routing (`services/knowledge_routing_v1.py`)

- Added `route_knowledge_layer_knowledge_v1()` — routes KL producer insights for `surface=knowledge_layer`
- Uses existing `route_knowledge_for_surface_v1` (no routing algorithm changes)

### Projection (`services/knowledge_layer_projection_v1.py`)

- `enrich_knowledge_report_kl_routing_and_projection_v1()` — attaches to `/api/knowledge/report`
- `build_knowledge_layer_projection_v1()` — builds `display_cards` for UI
- `project_kl_oia_v1()` — OIA copy from producer payload (ported from former JS)
- `flatten_kl_routed_display_items_v1()` — achievements-first order, insufficient filter, max 5

### API (`routes/knowledge.py`)

After producer metadata + decisions enrichment:

```python
enrich_knowledge_report_kl_routing_and_projection_v1(payload)
```

Response adds:

- `knowledge_routing_v1` — routed feed (`surface=knowledge_layer`)
- `knowledge_layer_projection_v1` — `display_cards` for UI

### UI (`static/merchant_knowledge_layer.js`)

- Consumes `knowledge_layer_projection_v1.display_cards` only
- Renders projected `title_ar`, `observation_ar`, `impact_ar`, `action_ar`
- No selection, ranking, aggregation, or OIA generation

---

## Migration rules compliance

| Rule | Status |
|------|--------|
| KLM-1 — consumes routed knowledge only | **Pass** |
| KLM-2 — no selection/ranking/prioritization/aggregation/generation in JS | **Pass** |
| KLM-3 — no recreated merchant explanations in JS | **Pass** |
| KLM-4 — no recreated merchant decisions in JS | **Pass** |
| KLM-5 — projects routed knowledge only | **Pass** |
| KLM-6 — presentation improvements allowed; no business ownership | **Pass** |

---

## Regression safety

| Layer | Changed? |
|-------|----------|
| Truth | **No** |
| Evidence | **No** |
| Proof | **No** |
| Decision Layer | **No** |
| Merchant Explanation | **No** |
| Knowledge Routing algorithms | **No** — surface wiring only |
| Daily Brief | **No** |
| Recovery / Lifecycle / Purchase Truth | **No** |
| `knowledge_insights_v1` producer | **No** |

---

## Tests

| File | Coverage |
|------|----------|
| `tests/test_knowledge_layer_migration_v1.py` | JS grep gate, routing feed, projection, certification |
| `tests/test_knowledge_routing_v1.py` | `route_knowledge_layer_knowledge_v1` surface test |
| `tests/test_merchant_knowledge_dashboard_v1.py` | Updated JS contract tests |

---

## Knowledge Layer Certification Review V1

### Remaining violations

| Item | Status |
|------|--------|
| JS `INSIGHT_PRIORITY` | **None** — removed |
| JS `pickTopInsights` | **None** — removed |
| JS OIA selection/generation | **None** — moved to projection |
| JS local ranking | **None** — removed |
| JS local aggregation | **None** — removed |
| Raw `insights[]` display path | **None** — UI uses projection only |

**Note:** `payload.insights[]` remains on API for backward compatibility and upstream consumers — not used by KL UI for selection.

### Ownership audit

| Responsibility | Owner |
|----------------|-------|
| Insight production | `knowledge_insights_v1` (unchanged) |
| Producer metadata | `knowledge_producer_metadata_v1` |
| Routing priority / eligibility / aggregation | `knowledge_routing_v1` |
| OIA presentation copy | `knowledge_layer_projection_v1` |
| Card layout / HTML / proof meta display | `merchant_knowledge_layer.js` |

### Regression audit

- Daily Brief routing path untouched  
- KL producer and metrics unchanged  
- API shape additive (`knowledge_routing_v1`, `knowledge_layer_projection_v1`)  
- Empty state behavior preserved when no actionable insights  

### Architecture verdict

## **PASS**

Knowledge Layer is certified as a **governed routing consumer** — second certified surface after Daily Brief.

Merchant Experience Migration Program V1 **Phase 1 complete**.

---

## Related documents

| Document | Role |
|----------|------|
| [`merchant_experience_migration_program_v1.md`](merchant_experience_migration_program_v1.md) | Program Phase 1 definition |
| [`knowledge_routing_implementation_v1.md`](knowledge_routing_implementation_v1.md) | Routing V1 reference |
| [`merchant_knowledge_infrastructure_closure_review_v1.md`](merchant_knowledge_infrastructure_closure_review_v1.md) | Era 1 closure |
