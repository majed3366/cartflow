# CartFlow Merchant Experience Migration Program V1

**Status:** Complete — all phases certified (2026-07-05)  
**Date (UTC):** 2026-07-05  
**Scope:** Migrate all existing merchant-facing surfaces to pure consumption of Merchant Knowledge Infrastructure — not new feature development  
**Authority:** First operational program of **Merchant Experience Era 2**, subordinate to [`merchant_experience_foundation_v1.md`](merchant_experience_foundation_v1.md), [`merchant_knowledge_infrastructure_closure_review_v1.md`](merchant_knowledge_infrastructure_closure_review_v1.md), and the **Permanent Architectural Rule**  
**Audience:** Product, engineering, architecture review  

**Explicitly out of scope:** Weekly Brief, Monthly Summary, Notifications, Executive Dashboard, AI Assistant, new routing rules, Truth/Decision/Explanation changes, UI redesign for its own sake.

---

## Executive summary

Merchant Knowledge Infrastructure is **complete**. Merchant Experience Foundation V1 defines **how** merchants should experience governed knowledge. This program closes the gap between **architectural intent** and **runtime reality** by migrating three remaining surfaces that still own local knowledge logic.

**This is a migration program — not a feature sprint.**

Every migrated surface becomes an **Infrastructure Consumer** — never an **Infrastructure Owner**.

| Surface | Program phase | Current status |
|---------|---------------|----------------|
| **Daily Brief** | Pre-certified (reference) | ✅ Routing consumer — Composer V2 projection-only |
| **Knowledge Layer** | Phase 1 | ✅ Certified — [`knowledge_layer_migration_v1.md`](knowledge_layer_migration_v1.md) |
| **Cart Detail** | Phase 2 | ✅ Certified — [`cart_detail_migration_v1.md`](cart_detail_migration_v1.md) |
| **Merchant Home** | Phase 3 | ✅ Certified — [`merchant_home_experience_v1.md`](merchant_home_experience_v1.md) |

**Program complete.** All merchant-facing knowledge surfaces listed above are **certified routing consumers**. Consumer migration debt from Closure Review Verdict B is closed for Phases 1–3.

---

## Section 1 — Mission

**Merchant Experience must become consistent across the entire platform.**

Every merchant-facing surface should feel as though it is powered by **one intelligence**.

The merchant should **never** experience:

- Different selection logic on Home vs Brief vs Knowledge Layer  
- Different priority ordering between Cart Detail and Daily Brief  
- Different knowledge ownership between dashboard sections  

One platform. One governed pipeline. One consistent experience.

---

## Section 2 — Program principle

```
Every migrated surface  →  Infrastructure Consumer
Never                   →  Infrastructure Owner
```

| Consumer (required) | Owner (forbidden) |
|---------------------|-------------------|
| Reads routed knowledge | Mints decisions |
| Projects layout and copy | Selects which insights appear |
| Truncates to surface budget | Re-ranks platform priority |
| Renders `merchant_explanation_v1` | Generates parallel explanations |
| Honors `eligible_surfaces` | Overrides routing visibility |

**Daily Brief** is the certified reference pattern: `route_daily_brief_knowledge_v1()` → Composer V2 projection. All three migration phases must converge on this model.

---

## Section 3 — Program phases

### Phase 0 — Reference consumer (complete)

**Daily Brief** — already certified in Merchant Knowledge Infrastructure Closure Review V1.

| Property | State |
|----------|-------|
| Routing | `services/knowledge_routing_v1.py` → `route_daily_brief_knowledge_v1()` |
| Projection | `services/merchant_daily_brief_composer_v2.py` — no select/rank/filter |
| Local selection | **None** |
| Certification | **Pass** — template for Phases 1–3 |

No migration work in this program. Daily Brief is the **pattern all phases must match**.

---

### Phase 1 — Knowledge Layer

**Priority:** First — largest active violation of Surfaces Never Decide.

#### Goals

Remove **all remaining local knowledge ownership** in Knowledge Layer.

Eliminate:

| Violation | Location (today) | Target |
|-----------|------------------|--------|
| `INSIGHT_PRIORITY` | `static/merchant_knowledge_layer.js` | Retired — routing owns priority |
| `pickTopInsights()` | `static/merchant_knowledge_layer.js` | Retired — routing owns selection |
| Surface-owned selection | KL JS filter/slice (3–5 insights) | Consume routed KL slice only |
| Surface-owned ranking | `insightScore`, priority map sort | Use `routing_priority` from routed feed |
| Surface-owned explanation decisions | OIA builders with purchase/return/hesitation branching | Project producer payloads; no local branching |

**Knowledge Layer must consume routed knowledge only.**

#### Current state

| Check | Status |
|-------|--------|
| KL API producer metadata | ✅ `enrich_knowledge_report_producer_metadata_v1` on `/api/knowledge/report` |
| KL decisions enriched | ✅ `enrich_knowledge_report_merchant_decisions_v1` |
| Routing feed for KL surface | ❌ Not wired — JS selects from raw API |
| JS selection logic | ❌ Active — documented violation |

#### Target state

```
/api/knowledge/report (producer metadata)
        ↓
route_knowledge_for_surface_v1(surface="knowledge_layer")
        ↓
merchant_knowledge_layer.js — projection only
```

- Server returns **pre-routed, pre-ordered** KL-eligible items.  
- JS renders cards from routed payload — layout, truncation, evidence display only.  
- No `pickTopInsights`, no `INSIGHT_PRIORITY`, no OIA domain branching for selection.

#### Phase 1 verification checklist

- [x] `INSIGHT_PRIORITY` removed or dead — grep gate clean  
- [x] `pickTopInsights` removed or dead — grep gate clean  
- [x] No JS sort by local score maps  
- [x] No JS filter that excludes items routing marked eligible  
- [x] KL cards trace to `knowledge_id` + routing observability  
- [x] Same insight priority on KL and Brief when both surface same item  
- [x] Tests cover routed KL feed contract  
- [x] **Certified routing consumer** sign-off recorded  

#### Phase 1 must not change

Truth · Evidence · Proof · Decision · Merchant Explanation · Routing algorithms (extend surface eligibility only if required — not business rules)

---

### Phase 2 — Cart Detail

**Priority:** Second — explanation consumed; visibility gate still local.

#### Goals

- **Consume routed knowledge** for cart-scoped items  
- **Consume Merchant Explanation** (`merchant_explanation_v1`) — already primary path  
- **Remove remaining local eligibility logic**  
- **Routing owns visibility** — surface owns presentation  

#### Current state

| Check | Status |
|-------|--------|
| `merchant_explanation_v1` on cart row | ✅ Wired in `main.py`; JS reads explanation bundle |
| Proof steps in merchant block | ✅ Removed — explanation only |
| `merchantDecisionExecutable` gate | ❌ JS-local executability — not routing visibility |
| `eligible_surfaces` enforcement | ❌ Not honored in cart detail JS |
| Cart-scoped routing feed | ❌ Not wired |

#### Target state

```
Cart row payload (explanation + decisions + producer metadata)
        ↓
route_knowledge_for_surface_v1(surface="cart_detail", cart_scope=…)
        ↓
Cart detail JS — presentation + interaction only
```

- Action buttons visible when **routing** marks `action_required` + cart_detail eligible — not JS heuristics.  
- `merchantDecisionExecutable` retired or reduced to pure UI enablement of routing-declared actions.  
- Explanation copy from `merchant_explanation_v1` only — no lifecycle `if` copy branches in JS.

#### Phase 2 verification checklist

- [x] No JS logic that hides/shows knowledge routing would exclude  
- [x] `merchantDecisionExecutable` retired — projection reads routing/explanation flags only  
- [x] `eligible_surfaces` includes `cart_detail` honored server-side before JS render  
- [x] Cart detail action set matches Daily Brief for same `knowledge_id`  
- [x] Tests cover cart-scoped routing visibility  
- [x] **Certified routing consumer** sign-off recorded  

#### Phase 2 must not change

Truth · Evidence · Proof · Decision · Merchant Explanation wording · Routing priority formula

---

### Phase 3 — Merchant Home

**Priority:** Third — composition layer; depends on Phases 1–2 feeds.

#### Goals

- **Become a composition layer** — layout regions, not knowledge engine  
- **Consume routed knowledge** — unified Home routing feed  
- **Consume Daily Brief** — already embedded; remain projection-only  
- **Consume KPIs** — read-model metrics; not knowledge selection  
- **Never perform knowledge selection**

#### Current state

| Check | Status |
|-------|--------|
| Daily Brief on Home | ✅ `#ma-daily-brief-root`; routing-backed via Brief API |
| KL section on Home | 🟡 May use pre-migration KL JS selection |
| KPI / summary widgets | 🟡 Read-model fetches — acceptable if not knowledge minting |
| Unified routing feed | ❌ Independent fetches; no single routed Home payload |

#### Target state

```
Unified Home routing feed (Brief slice + KL slice + Home-eligible items)
        ↓
Home template + JS — region composition only
        ├── Achievements region  (routed, achievement narrative_role first)
        ├── Daily Brief region   (existing certified path)
        ├── KL preview region    (routed KL truncate — post Phase 1)
        └── KPI region           (read-model — not knowledge pipeline)
```

- Home does **not** choose which insights appear in KL preview — inherits Phase 1 routed slice (truncated budget).  
- Home does **not** reorder Brief items — inherits certified Brief path.  
- KPI widgets display read-model aggregates — never substitute for knowledge routing.

#### Phase 3 verification checklist

- [x] No Home-local insight selection or priority maps  
- [x] KL preview matches KL page truncation of same routed feed  
- [x] Brief on Home identical to standalone Brief API ordering  
- [x] Single observability block traces Home composition sources  
- [x] KPI region documented as read-model — not knowledge consumer conflict  
- [x] **Certified routing consumer** sign-off recorded  

#### Phase 3 must not change

Truth · Evidence · Proof · Decision · Merchant Explanation · Daily Brief routing path · KPI calculation logic

---

## Section 4 — Migration principles

Permanent rules for every phase. Align with ME-1…ME-8 from Merchant Experience Foundation and MEM program-specific constraints.

### MEM-1 — Every migration reduces local logic

Each phase must **delete or retire** surface-owned selection code — not wrap it. Wrapping local logic behind an API is not migration; **removal** is migration.

### MEM-2 — Every migration increases platform consistency

After each phase, the same `knowledge_id` must appear with the same priority and eligibility across all surfaces that consume it. Regression tests compare Brief ↔ KL ↔ Cart Detail ↔ Home.

### MEM-3 — No surface owns business knowledge

Business meaning lives in producers and routing. Surfaces own **layout, copy projection, navigation, and interaction** — not meaning.

### MEM-4 — Presentation belongs to the surface. Knowledge belongs to the platform.

CSS, card layout, mobile truncation, achievement-first section ordering (within routed sets) = surface.  
Selection, ranking, aggregation, eligibility = platform.

### MEM-5 — Migration must never change upstream governance

**Frozen during all phases:**

| Layer | Migration may touch? |
|-------|---------------------|
| Truth | **No** |
| Evidence | **No** |
| Proof | **No** |
| Decision | **No** |
| Merchant Explanation | **No** (read only) |
| Knowledge Routing | **Extend surface wiring only** — no new business rules |

Routing may add `surface="knowledge_layer"`, `surface="cart_detail"`, `surface="merchant_home"` distribution paths. It may **not** introduce purchase/return/hesitation branching to compensate for surface logic removal.

### MEM-6 — Merchant experience becomes more consistent after every migration. Never more complicated.

If a migration adds merchant-visible complexity (more cards, duplicate items, conflicting actions), the phase is **not complete** — simplify projection before sign-off.

---

## Section 5 — Success criteria (per migrated surface)

For **every** migrated surface, verify before certification:

| Criterion | Pass condition |
|-----------|----------------|
| **Knowledge consumed only** | All displayed items originate from routed feed or certified upstream bundle (`merchant_explanation_v1`) — not JS-invented |
| **No local selection** | No filter that removes routing-eligible items |
| **No local ranking** | No sort by surface priority maps, scores, or timestamps |
| **No local aggregation** | No surface-side grouping that merges/splits routed items |
| **No local explanation generation** | No OIA builders or lifecycle branches that compose new merchant meaning |
| **No duplicated ownership** | Same `knowledge_id` — one platform owner; surface projects once |

### Certification record template

Each phase completion adds an entry to the program certification table (implementation docs update separately):

| Surface | Phase | Certified date | Routing entrypoint | Verified by |
|---------|-------|----------------|-------------------|-------------|
| Daily Brief | 0 (reference) | 2026-07-05 | `route_daily_brief_knowledge_v1` | Closure Review V1 |
| Knowledge Layer | 1 | 2026-07-05 | `route_knowledge_layer_knowledge_v1` | `tests/test_knowledge_layer_migration_v1.py` |
| Cart Detail | 2 | 2026-07-05 | `route_cart_detail_knowledge_v1` | `tests/test_cart_detail_migration_v1.py` |
| Merchant Home | 3 | 2026-07-05 | `route_merchant_home_knowledge_v1` + composition | `tests/test_merchant_home_experience_v1.py` |

---

## Section 6 — Program completion

**Merchant Experience Migration Program V1 is complete only when:**

| Surface | Requirement |
|---------|-------------|
| **Knowledge Layer** | Certified routing consumer — Phase 1 checklist pass |
| **Cart Detail** | Certified routing consumer — Phase 2 checklist pass |
| **Merchant Home** | Certified routing consumer — Phase 3 checklist pass |

### Completion outcomes

When all three are certified:

1. **Surfaces Never Decide** — satisfied platform-wide for merchant-facing knowledge  
2. **Closure Review Verdict B** — consumer migration debt closed; eligible for Verdict A surface audit (separate review)  
3. **Greenfield era opens** — Weekly Brief, Monthly Summary, Notifications, Executive, AI may begin as **new routing consumers** only  

### Completion does not include

- Dashboard carts tab filters (read-model — acceptable per Closure Review)  
- Admin surfaces  
- Widget / storefront layers  

---

## Section 7 — Out of scope

The following **must not begin** until this migration program completes:

| Capability | Reason |
|------------|--------|
| **Weekly Brief** | New consumer — requires consistent routing baseline |
| **Monthly Summary** | New consumer — same |
| **Notifications** | New consumer — must not inherit KL/Home selection debt |
| **Executive Dashboard** | New consumer |
| **AI Assistant** | New consumer — must not learn from parallel JS logic |

Also out of scope for this program:

- UI redesign unrelated to removing local logic  
- New producer metadata fields (unless required for surface eligibility wiring)  
- Routing priority formula changes  
- Truth / Decision / Explanation behavior changes  
- Parallel "quick fix" surface logic that bypasses routing  

---

## Section 8 — Dependencies and sequencing

```
Phase 0: Daily Brief (complete) ─────────────────────────────┐
                                                              │
Phase 1: Knowledge Layer ────────────────────────────────────┤
         (routing KL surface + JS retirement)                │
                                                              ├──→ Phase 3: Merchant Home
Phase 2: Cart Detail ────────────────────────────────────────┤         (unified composition)
         (cart-scoped routing + gate retirement)             │
                                                              │
Phase 1 + 2 should complete before Phase 3 KL preview ───────┘
```

| Phase | Depends on | Blocks |
|-------|------------|--------|
| 1 — KL | Routing V1, producer metadata | Home KL preview (Phase 3) |
| 2 — Cart Detail | Explanation V1, routing cart surface | — |
| 3 — Home | Phases 1 + 2 + certified Brief | Greenfield consumers |

Phases 1 and 2 may run **in parallel** if staffing allows — they touch disjoint code paths. Phase 3 requires both.

---

## Section 9 — Anti-patterns (program violations)

| Anti-pattern | Why it fails MEM-1 / MEM-5 |
|--------------|---------------------------|
| Call routing API but keep `pickTopInsights` as fallback | Dual pipeline — forbidden |
| Server routes then JS re-sorts "for UX" | Surface-owned ranking |
| Add Home-specific `if purchase` branches | Surface-owned knowledge |
| Change Decision Layer to match JS expectations | Upstream change — out of scope |
| Ship Weekly Brief before KL migration | New consumer on inconsistent base |
| Wrap legacy selection in new function names | No logic reduction — not migration |

**Grep gate (recommended CI):** `pickTopInsights|INSIGHT_PRIORITY|merchantDecisionExecutable` in `static/` — must trend to zero through program phases.

---

## Section 10 — Related documents

| Document | Role |
|----------|------|
| [`merchant_experience_foundation_v1.md`](merchant_experience_foundation_v1.md) | Era 2 principles ME-1…ME-8; surface contracts |
| [`merchant_knowledge_infrastructure_closure_review_v1.md`](merchant_knowledge_infrastructure_closure_review_v1.md) | Era 1 closure; Verdict B; violation inventory |
| [`knowledge_routing_implementation_v1.md`](knowledge_routing_implementation_v1.md) | Routing V1 module; Daily Brief reference |
| [`knowledge_routing_foundation_v1.md`](knowledge_routing_foundation_v1.md) | KR-1…KR-12; KP-1…KP-10 |
| [`knowledge_production_standardization_v1.md`](knowledge_production_standardization_v1.md) | Surface selection freeze; violation grep |
| [`knowledge_routing_readiness_review_v1.md`](knowledge_routing_readiness_review_v1.md) | Original violation audit |
| [`merchant_daily_brief_composer_v2.md`](merchant_daily_brief_composer_v2.md) | Projection-only reference pattern |

---

## Section 11 — Program success statement

When Merchant Experience Migration Program V1 completes:

**Merchant Experience becomes fully aligned with Merchant Knowledge Infrastructure.**

Every merchant-facing surface expresses the **same governed knowledge**.

The merchant experiences **one platform** — not multiple independent screens.

---

## Merchant Experience Migration Program Declaration

This program is the **first operational act** of the Merchant Experience Era.

Infrastructure is complete. Foundation is ratified. **Migration is the work.**

CartFlow will not build new merchant intelligence until existing surfaces stop owning it.

**Knowledge Layer · Cart Detail · Merchant Home** — three phases, one outcome: **Infrastructure Consumer, never Infrastructure Owner.**

Upon program completion, CartFlow opens the greenfield experience era — Weekly, Monthly, Notifications, Executive, AI — on a **single consistent platform intelligence**.

**Merchant Experience Migration Program V1 — ratified.**
