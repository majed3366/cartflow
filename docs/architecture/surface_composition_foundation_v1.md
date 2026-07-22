# CartFlow Surface Composition Foundation V1

**Status:** Governed platform layer (architecture + runtime)  
**Date (UTC):** 2026-07-22  
**Authority:** Subordinate to [`merchant_presentation_foundation_v1.md`](merchant_presentation_foundation_v1.md) and Guidance Routing.  
**Audience:** Product, engineering, architecture  
**Explicitly out of scope:** Home redesign, Decision Workspace redesign, Carts/Communication/Settings redesign, Figma, CSS, components, frontend implementation, AI summaries, notifications, new business logic, routing decisions

> **Law:** Surface Composition answers only *what each merchant surface should receive*, *where it belongs*, *how important it is*, and *when it must disappear*.  
> Routing decides destinations. Presentation decides representation. Composition decides surface binding, priority, cognitive load, freshness, and duplicate governance.  
> Pages consume compositions. Pages never decide.

---

## 0. Purpose

Create one governed orchestration layer that composes merchant-facing surfaces from existing governed outputs.

| This layer does | This layer must never |
|-----------------|------------------------|
| Bind governed items to surfaces | Redesign pages / UI |
| Enforce cognitive-load limits | Invent business logic |
| Govern duplicates + freshness | Decide routing |
| Account every input outcome | Read raw widget/WhatsApp/purchase tables |
| Materialize projection records | Generate AI summaries or recommendations |

---

## 1. Placement

```text
Canonical Domain Truth
        ↓
Evidence
        ↓
Commerce Intelligence Synthesis
        ↓
Knowledge
        ↓
Commercial Guidance
        ↓
Guidance Routing
        ↓
Merchant Presentation
        ↓
Surface Composition  ← THIS LAYER
        ↓
Merchant Pages (consumers only)
```

**Note:** Merchant Presentation is already production-closed. Surface Composition consumes Presentation contracts (which embed Routing destinations and Guidance lineage) plus Knowledge statements. It does not re-open Presentation ownership.

---

## 2. Architecture inventory (pre-implementation)

| Concern | Current owner | Duplication / page-owned risk | Migration stance |
|---------|---------------|-------------------------------|------------------|
| Home projections | `merchant_home_composition_v1`, activation, semantic/adaptive bridges | Page selects/dedupes/ranks | Migrate later to consume SCF |
| Dashboard / summary cards | `finalize_dashboard_summary_payload`, Pulse | Page-attached composition | Consume SCF projections |
| Decision Workspace | `cart_workspace/projection_v1` | Zone projection of admitted decisions | Keep decision admission upstream; SCF binds attention |
| Cart projections | `cart_detail_projection_v1`, merchant value stories | Local story selection | Consume SCF for attention classes |
| Communication | WhatsApp readiness presentation (legacy) | Not wired to GRF `communication` | SCF empty-state until routed |
| Knowledge projections | Knowledge Foundation + KL projection | Dual spines | SCF Knowledge class from KF only |
| Guidance / Presentation | CGF / GRF / MPF | Canonical Product Performance stack | **Do not duplicate** — SCF consumes MPF |
| Routing modules | `guidance_routing_*`, `guidance_surface_registry_v1` | Surface eligibility owned by GRF | SCF routing_policy = consume only |
| Projection registries | GRF/MPF/CGF registries | Code-owned | SCF adds `surface_registry_v1` for composition policies only |

Reusable contracts: `mpf_v1` presentations, `kf_v1` knowledge statements, GRF surface keys (`home`, `decision_workspace`, `carts`, `communication`, `settings`).

---

## 3. Ownership

| Question | Owner |
|----------|-------|
| What guidance exists? | Commercial Guidance |
| Which surface may receive it? | Guidance Routing |
| How may it be represented? | Merchant Presentation |
| What should each surface receive now? | **Surface Composition** |
| How is it painted on screen? | Merchant pages / Design System (future) |

Every V1 surface has one composition owner: `surface_composition_foundation_v1`.

---

## 4. Input boundary

**Allowed:**

- Merchant Presentation (`generate_merchant_presentations_v1`) — primary guidance-backed input (Routing destinations included)
- Knowledge (`generate_knowledge_v1`) — Knowledge information class
- Surface registry composition policies

**Forbidden direct reads:**

- Widget events, WhatsApp events
- Purchase / timeline / movement tables
- Provider payloads
- Commerce Intelligence Synthesis
- Commercial Guidance / Eligibility evaluators (lineage only via Presentation)

Operational Truth / Merchant Operational State have no closed Product Performance foundations in V1; empty/operational calm states are composed from presentation/knowledge absence only (no admin health scrape).

---

## 5. Surface registry (`surface_registry_v1`)

Each surface defines:

- `surface_id`, purpose, merchant question answered, owner
- supported information classes
- maximum cognitive load
- refresh / priority / collapse / stale / routing / ordering policies
- version (`sreg_v1`)

Canonical surfaces only: Home, Decision Workspace, Carts, Communication, Settings.

---

## 6. Information classes

Pages consume classes, not business rules:

Executive Summary, Critical Attention, Commercial Guidance, Knowledge, Operational Health, Recovery Health, Evidence Gap, Trend, Observation, Timeline, Action Queue, Configuration, Empty State.

---

## 7. Composition item contract

Every composed item defines:

source, source lineage, information class, merchant value, urgency, freshness, confidence, expiry, visibility, destination surfaces, duplicate group, suppression rules, presentation intent, priority, accounting outcome, fingerprint, deterministic `composition_id`.

**Presentation intent (semantic only):** Hero, Headline, Priority Card, Insight Card, Summary Card, Operational State, Evidence Notice, Warning, Information, Configuration, Timeline, Reference.

No pixels. No CSS.

---

## 8. Cognitive load

Example (Home):

- Hero: 1
- Executive summaries: max 4
- Critical attention: max 5
- Knowledge highlights: max 3
- Guidance highlights: max 3

Overflow never expands indefinitely — it enters governed collapse (`visibility=collapsed`, accounting=`collapsed`).

---

## 9. Duplicate governance

Every item belongs to a `duplicate_group`.

Exactly one surface owns the full explanation (`owns_full_explanation=true`) per class ownership map. Other surfaces reference it (`presentation_intent=reference`). Within a surface, only one current winner per group remains visible.

---

## 10. Freshness + visibility

Freshness: `fresh` → `aging` → `stale` → `expired` (from `valid_until` vs `as_of`).  
Expired composition disappears automatically (`visibility=expired`).

Visibility: `visible` | `collapsed` | `hidden` | `suppressed` | `expired` — reasons explicit.

---

## 11. Priority

Deterministic score from merchant impact (route role), urgency (presentation state), freshness, confidence/evidence completeness, operational severity. Pages must never invent ordering.

---

## 12. Empty-state governance

If no commercial guidance / visible items exist for a surface, compose truthful states only:

- evidence still growing
- no operational issues
- insufficient evidence
- nothing requiring action

Never fabricate content.

---

## 13. Routing contract

Surface Composition consumes Guidance Routing destinations via Presentation `surface_key`. It does not decide routing. It only composes routed outputs.

---

## 14. Data model

Projection table `surface_compositions` (`scf_v1`).

Key fields: `composition_id`, `surface_id`, `source_type`, `source_id`, `information_class`, `presentation_intent`, `priority`, `freshness_state`, `visibility`, `duplicate_group`, `expiry`, `version`, `fingerprint`, `is_current`.

Same inputs → same composition identity. No duplicate current rows per store×surface×source.

Lifecycle: create, update, unchanged, supersede, expire, suppress.

---

## 15. Full accounting

Every routed/presented/knowledge input becomes one of:

Composed | Collapsed | Suppressed | Expired | Deferred | Rejected | Failed

No silent loss.

---

## 16. Performance

Merchant requests consume **current** compositions.  
Never rebuild composition inside page requests (pages are not implementers in this task).

---

## 17. Runtime

| Item | Value |
|------|-------|
| Modules | `services/product_data/surface_composition_*_v1.py` |
| Flag | `CARTFLOW_SURFACE_COMPOSITION_V1` (default on) |
| Probe | `GET /dev/surface-composition?store=demo` |
| Table | `surface_compositions` |
| Alembic | `h7i8j9k0l1m2` |
| Versions | `scf_v1` / `scf_v1_gen` / `sreg_v1` |

---

## 18. Forbidden scope

Do not implement in this foundation:

- Home / Decision Workspace / Carts / Communication / Settings redesign
- Figma, CSS, components, frontend
- AI summaries, notifications
- New commercial business logic
- Routing decisions
- Action execution

**STOP:** After implementation, testing, deployment, production verification, and closure documentation — do not redesign any page until Surface Composition V1 is reviewed and approved.
