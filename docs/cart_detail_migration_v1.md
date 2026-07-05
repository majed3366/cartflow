# CartFlow Cart Detail Migration V1

**Status:** Implemented — Sprint 2 of Merchant Experience Migration Program  
**Date (UTC):** 2026-07-05  
**Scope:** Phase 2 — migrate Cart Detail from surface-owned eligibility/explanation branching to governed routing consumer  
**Authority:** [`merchant_experience_migration_program_v1.md`](merchant_experience_migration_program_v1.md) Phase 2  
**Audience:** Engineering, architecture review  

---

## Executive summary

Cart Detail is no longer a knowledge owner. It is a **certified routing consumer** — third surface after Daily Brief and Knowledge Layer to complete the full Infrastructure → Routing → Explanation → Projection → UI pipeline for a single cart row.

Selection, suggested-action visibility, and explanation composition moved from `static/merchant_dashboard_lazy.js` to platform layers:

```
Merchant Knowledge Infrastructure (Truth / Proof / Decision / Explanation)
        ↓
Knowledge Routing (`route_cart_detail_knowledge_v1`)
        ↓
Merchant Explanation (`merchant_explanation_v1`)
        ↓
Cart Detail Projection (`cart_detail_projection_v1`)
        ↓
Cart Detail UI (`merchant_dashboard_lazy.js` — presentation only)
```

---

## Removed surface ownership (JS)

| Removed | Former responsibility | New owner |
|---------|----------------------|-----------|
| `merchantDecisionExecutable()` | Local executability gate for suggested action | `cart_detail_projection_v1.suggested_action` (routed decision + `_brief_action_ar`) |
| `MERCHANT_DECISION_LABEL_AR` | Surface-owned decision label map | `_brief_action_ar` in projection (Decision Layer copy path) |
| `NORMAL_CART_MERCHANT_EXECUTABLE_DECISION_KEYS` | Surface-owned decision key allowlist | Routing eligibility + published decision payload |
| JS branching on `merchant_decision_key` for display | Surface action visibility | `suggested_action.visible` from projection |
| Direct lifecycle copy assembly when projection present | Parallel explanation path | `cart_detail_projection_v1.explanation` from `merchant_explanation_v1` |

### JS decisions audit

| Decision | Classification |
|----------|----------------|
| Read `cart_detail_projection_v1` when present | **KEEP** — routed feed consumer |
| Render explanation fields from `proj.explanation` | **KEEP** — presentation |
| Render suggested action from `proj.suggested_action` | **KEEP** — presentation |
| Render contact button from `proj.contact_action` | **KEEP** — presentation |
| Render archive/reopen from `proj.lifecycle_ui` | **KEEP** — presentation |
| `esc()` HTML escaping | **KEEP** — presentation safety |
| Legacy fallbacks when projection absent (old snapshots) | **KEEP** — backward compatibility only |
| `merchantDecisionExecutable` | **REMOVE** — retired |
| `MERCHANT_DECISION_LABEL_AR` | **REMOVE** — retired |
| Local decision key allowlist | **REMOVE** — retired |

---

## Ownership audit

| Responsibility | Owner | Cart Detail role |
|----------------|-------|------------------|
| Purchase / Lifecycle Truth | Platform Truth layers | **Consume** — unchanged |
| Evidence / Proof | `merchant_proof_surface_v1` | **Consume** — unchanged |
| Merchant Decision | `merchant_decision_layer_v1` | **Consume** via routing payload |
| Merchant Explanation | `merchant_explanation_v1` | **Consume** — projected to `explanation` block |
| Routing priority / eligibility | `knowledge_routing_v1` | **Consume** — `route_cart_detail_knowledge_v1` |
| Suggested action label | Decision + `_brief_action_ar` | **Project** — never minted in JS |
| Contact href visibility | Row semantics (`merchant_intervention_*`) | **Project** — operational interaction wiring |
| Archive / reopen buttons | Row lifecycle action field | **Project** — interaction affordance |
| Layout / expand / HTML structure | `merchant_dashboard_lazy.js` | **Surface-owned** |
| Timeline / movement line display | Dashboard row fields | **Surface-owned** presentation |

No responsibility remains ambiguous: business knowledge is platform-owned; Cart Detail UI owns layout and interaction only.

---

## Implementation

### Routing (`services/knowledge_routing_v1.py`)

- Added `route_cart_detail_knowledge_v1()` — routes explanation + decision bundle for `surface=cart_detail`
- Uses existing `route_knowledge_for_surface_v1` (no routing algorithm changes)
- `max_attention_items=1` — single primary attention item for cart detail

### Projection (`services/cart_detail_projection_v1.py`)

- `build_cart_detail_projection_v1()` / `attach_cart_detail_projection_v1()`
- Modes: `explanation`, `archived`, `legacy`, `unavailable`
- `explanation` — projected copy from `merchant_explanation_v1` (CDM-1)
- `suggested_action` — primary routed decision via `_brief_action_ar` (CDM-2, CDM-3)
- `contact_action` — operational WhatsApp affordance from row semantics
- `lifecycle_ui` — archive/reopen visibility from `customer_lifecycle_dashboard_action`
- Embeds `knowledge_routing_v1` per row for observability

### API (`main.py`)

After `attach_merchant_decisions_v1(out)`:

```python
attach_cart_detail_projection_v1(out)
```

Each normal-carts row adds `cart_detail_projection_v1`.

### Snapshot allowlist

`services/dashboard_snapshot_normal_carts_slim_v1.py` includes `cart_detail_projection_v1`.

### UI (`static/merchant_dashboard_lazy.js`)

- `cartDetailProjection(mc)` — reads governed projection
- `merchantExplanationProjectionHtml()` — renders projected explanation block
- `merchantDecisionSuggestedActionHtml()` — reads `proj.suggested_action` only
- `merchantInterventionContactBtnHtml()` / `cartLifecycleActionBtnHtml()` — read projection blocks
- Legacy fallbacks when projection absent (cached snapshots) — presentation only, no business gates

---

## Cart Detail principles compliance

| Rule | Status |
|------|--------|
| CDM-1 — every visible explanation from Merchant Explanation | **Pass** |
| CDM-2 — every visible action from Merchant Decision | **Pass** |
| CDM-3 — every visible priority from Knowledge Routing | **Pass** |
| CDM-4 — Cart Detail never invents merchant wording | **Pass** |
| CDM-5 — Cart Detail never determines attention worthiness | **Pass** |
| CDM-6 — Cart Detail never evaluates merchant eligibility | **Pass** |
| CDM-7 — Cart Detail only composes governed knowledge | **Pass** |

---

## Regression safety

| Layer | Changed? |
|-------|----------|
| Purchase Truth | **No** |
| Lifecycle Truth | **No** |
| Recovery execution | **No** |
| Merchant Explanation wording | **No** |
| Decision Layer logic | **No** |
| Knowledge Routing algorithms | **No** — surface wiring only |
| Daily Brief | **No** |
| Knowledge Layer | **No** |
| Knowledge Layer producer | **No** |

---

## Tests

| File | Coverage |
|------|----------|
| `tests/test_cart_detail_migration_v1.py` | JS grep gate, projection attachment, explanation consistency, suggested/contact/lifecycle blocks, archived mode |
| `tests/test_knowledge_routing_v1.py` | `route_cart_detail_knowledge_v1` surface test |
| `tests/test_merchant_decision_execution_v1.py` | Decision attach regression (unchanged contract) |

---

## Cart Detail Certification Review V1

### Remaining violations

| Item | Status |
|------|--------|
| JS `merchantDecisionExecutable` | **None** — removed |
| JS `MERCHANT_DECISION_LABEL_AR` | **None** — removed |
| JS local decision key allowlist | **None** — removed |
| JS local suggested-action eligibility | **None** — projection owns visibility |
| JS local explanation branching (when projection present) | **None** — projection path only |
| Duplicated merchant wording in JS | **None** — labels from projection |

**Note:** Legacy fallbacks remain for rows without `cart_detail_projection_v1` (cached snapshots). They do not reintroduce business ownership on fresh API responses where projection is always attached.

### Projection audit

| Block | Source |
|-------|--------|
| `explanation.*` | `merchant_explanation_v1` |
| `suggested_action.*` | Routed decision + `_brief_action_ar` |
| `contact_action.*` | Row `merchant_intervention_*` semantics |
| `lifecycle_ui.*` | Row `customer_lifecycle_dashboard_action` |
| `knowledge_routing_v1` | `route_cart_detail_knowledge_v1` |

Projection creates no knowledge, explanations, decisions, eligibility, or routing.

### Regression audit

- Daily Brief and Knowledge Layer paths untouched  
- Decision and Explanation attach order unchanged before projection  
- API shape additive (`cart_detail_projection_v1`)  
- Cart detail HTML structure preserved — no UI redesign  

### Merchant explanation consistency

Cart Detail explanation fields match `merchant_explanation_v1` on the same row (verified in tests). Suggested action copy uses the same `_brief_action_ar` path as Daily Brief.

### Routing consumption

Each cart row embeds `knowledge_routing_v1` with `surface=cart_detail`. Primary attention item drives `suggested_action.routing_priority`.

### Architecture verdict

## **PASS**

Cart Detail is certified as a **governed routing consumer** — third certified surface after Daily Brief and Knowledge Layer.

Merchant Experience Migration Program V1 **Phase 2 complete**.

---

## Related documents

| Document | Role |
|----------|------|
| [`merchant_experience_migration_program_v1.md`](merchant_experience_migration_program_v1.md) | Program Phase 2 definition |
| [`knowledge_routing_implementation_v1.md`](knowledge_routing_implementation_v1.md) | Routing V1 reference |
| [`knowledge_layer_migration_v1.md`](knowledge_layer_migration_v1.md) | Phase 1 certified pattern |
| [`merchant_explanation_unification_v1.md`](merchant_explanation_unification_v1.md) | Explanation source |
