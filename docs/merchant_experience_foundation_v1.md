# CartFlow Merchant Experience Foundation V1

**Status:** Ratified baseline — permanent experience architecture for Merchant Value  
**Date (UTC):** 2026-07-05  
**Scope:** Defines **how merchants experience governed platform knowledge** across their workday — not how knowledge is produced, proven, routed, or implemented  
**Authority:** Opens the **Merchant Experience Era**, which begins after the formal closure of Merchant Knowledge Infrastructure V1 ([`merchant_knowledge_infrastructure_closure_review_v1.md`](merchant_knowledge_infrastructure_closure_review_v1.md)). Subordinate to the **Merchant Knowledge Infrastructure Declaration** and **Permanent Architectural Rule** — experience expresses infrastructure; it never replaces it.  
**Audience:** Product, engineering, commercial, operations, design  

**Explicitly out of scope (this document):** Implementation, UI redesign, routing migration, AI, notification engine, Weekly Brief implementation, Monthly Summary implementation, code changes.

---

## Executive summary

Merchant Experience is **not** a collection of screens.

Merchant Experience is the **governed presentation of platform knowledge**.

CartFlow's first major architectural era — **Merchant Knowledge Infrastructure** — is complete. Truth through Knowledge Routing is platform-owned, certified, and permanently declared. The second major era — **Merchant Experience** — defines how merchants **consume** that knowledge throughout their workday without recreating it, bypassing it, or increasing cognitive load.

The experience must express the architecture. **It must never replace it.**

Future merchant-facing capabilities — Daily, Weekly, Monthly, Notifications, Mobile, Executive, AI — are built on this foundation as **experience consumers**, not as independent knowledge systems.

---

## Section 1 — Purpose

CartFlow exists to reduce merchant thinking.

The merchant should never wonder:

| Question | Platform obligation |
|----------|---------------------|
| **What happened?** | Answered before the merchant asks — through governed awareness surfaces |
| **What should I do?** | Answered only when action is truly required — through routed decisions and explanations |
| **Did CartFlow already handle this?** | Answered first — achievements and completed work visible before problems |

Merchant Experience is the permanent contract for **how** these answers appear across surfaces, cadences, and contexts — without any surface owning Truth, Evidence, Proof, Decision, Explanation, Routing, or Knowledge Production.

---

## Section 2 — Architectural position

Merchant Experience sits **above** Merchant Knowledge Infrastructure and **below** individual experience cadences and surfaces.

```
Merchant Knowledge Infrastructure          ← Era 1 (closed)
  Truth → Evidence → Proof → Decision
  → Explanation → Producer → Routing → Projection
        ↓
Merchant Experience                        ← Era 2 (this foundation)
        ↓
Daily Experience      (Daily Brief, Home, Cart Detail, KL)
Weekly Experience     (Weekly Brief — future)
Monthly Experience    (Monthly Summary — future)
Notifications         (interrupt-only — future)
Mobile Experience     (future)
Executive Experience  (future)
AI Experience         (future)
```

| Layer | Owns | Does not own |
|-------|------|--------------|
| **Merchant Knowledge Infrastructure** | Truth, Evidence, Proof, Decision, Explanation, Producer metadata, Routing, Projection contract | Layout, cadence, merchant emotional framing, screen composition |
| **Merchant Experience** | Experience principles, surface responsibilities, attention model, merchant day model, experience pyramid | Knowledge production, routing logic, decision minting, truth writes |
| **Individual surfaces** | Presentation layout, copy projection, navigation, calm/achievement ordering within routed budget | Selection, prioritization, eligibility, reinterpretation of platform knowledge |

**Relationship to closure declaration:** The Merchant Knowledge Infrastructure Declaration certifies that surfaces consume routed knowledge without recreating, reinterpreting, reprioritizing, or redistributing platform knowledge. Merchant Experience Foundation V1 defines **what that consumption means** for merchant-facing work — across time, attention, and emotional trust.

---

## Section 3 — Mission

**CartFlow should reduce merchant thinking.**

Every experience decision — what to show, when to show it, in what order, with what tone — must serve that mission.

| Anti-mission | Why forbidden |
|--------------|---------------|
| Increase reading load | Merchant attention is scarce; more text ≠ more value |
| Recreate knowledge in UI | Violates Permanent Architectural Rule; creates parallel pipelines |
| Show everything at once | KPI walls destroy trust and attention |
| Lead with problems | Merchant must feel platform control before detail |
| Require merchant inference | Platform must answer before the merchant asks |

---

## Section 4 — Experience principles

These principles are permanent. Every merchant-facing surface, cadence, and future capability **must implement** them.

### ME-1 — Experience consumes governed knowledge

Experience **never recreates** knowledge.

Surfaces read routed knowledge items and project them. They do not mint decisions, compose proof, infer truth, or build parallel insight selection (`pickTopInsights`, surface-local priority tables, lifecycle `if` branches).

### ME-2 — Experience reduces thinking

Experience **does not increase reading**.

Copy, layout, and cadence exist to compress understanding — not to expose every upstream field. One clear action beats five explanatory paragraphs.

### ME-3 — Merchant attention is scarce

**Every screen protects attention.**

Attention budgets are real (Daily Brief ≤5 items; notifications interrupt-only). Surfaces truncate presentation; they never expand selection beyond routed budgets.

### ME-4 — CartFlow acts first

**Merchant acts only when necessary.**

Automated recovery, scheduling, monitoring, and lifecycle handling are achievements — shown before attention items. The merchant intervenes when the platform cannot or should not act alone.

### ME-5 — Experience reflects architecture

Presentation **never bypasses**:

- Truth  
- Decision  
- Merchant Explanation  
- Knowledge Routing  

No shortcut from raw dashboard rows to merchant advice. No widget-local business logic that skips upstream governance.

### ME-6 — Calm before information

The merchant should feel **"The platform is under control."** before seeing details.

Opening states, empty states, and hero regions establish operational confidence — then reveal specifics. Panic-inducing density is an experience failure.

### ME-7 — Achievements before problems

Begin by showing **what CartFlow accomplished** while the merchant was away.

Only then show what needs attention. Achievements are routed knowledge with `narrative_role=achievement` (or equivalent producer metadata) — not marketing copy invented by surfaces.

### ME-8 — No KPI walls

**Knowledge should be organized into actions, explanations, and outcomes** — not metric grids.

Dashboards that become walls of numbers violate ME-2 and ME-3. Experience organizes knowledge into merchant-meaningful structures: what happened, why it matters, what to do (if anything).

---

## Section 5 — Merchant day model

The merchant journey defines **when** experiences activate and **what cadence** each surface serves.

```
Morning
  ↓
Open CartFlow
  ↓
See what CartFlow already completed        ← Achievements (ME-7)
  ↓
See only today's required actions          ← Routed attention budget (ME-3, ME-4)
  ↓
Leave                                      ← Merchant returns to store operations
  ↓
Receive only important notifications       ← Interrupt-only; routing-eligible
  ↓
Weekly reflection                          ← Weekly Brief (future)
  ↓
Monthly business understanding             ← Monthly Summary (future)
```

| Phase | Primary surfaces | Experience goal |
|-------|------------------|-----------------|
| **Morning open** | Merchant Home, Daily Brief | Trust + today's action queue |
| **In-session work** | Cart Detail, Knowledge Layer, Dashboard carts | Contextual explanation + drill-down |
| **Away / async** | Notifications (future) | Critical attention only — never duplicate Brief |
| **Weekly** | Weekly Brief (future) | Pattern awareness — not daily rehash |
| **Monthly** | Monthly Summary (future) | Business understanding — outcomes over activity |

The day model is **architectural**, not a scheduling engine. Implementation of cadence triggers belongs to future experience builds — governed by this model.

---

## Section 6 — Experience surfaces

Each surface is an **experience consumer**. For every surface: why it exists, when it is used, what experience it provides, what knowledge it consumes, and what it must never own.

### 6.1 Merchant Home

| Dimension | Definition |
|-----------|------------|
| **Why it exists** | First landing after login — establishes daily trust and orients the merchant's session |
| **When it is used** | Every session open; primary morning entry point |
| **Experience provided** | Calm operational summary (ME-6); achievements visible first (ME-7); today's action queue without KPI wall (ME-8) |
| **Knowledge consumed** | Routed Daily Brief slice; summary bootstrap; future unified routing feed (Home + Brief + activity) |
| **Must never own** | Decision minting; insight selection; prioritization; truth interpretation; parallel brief composition |

### 6.2 Daily Brief

| Dimension | Definition |
|-----------|------------|
| **Why it exists** | Answers "what happened / why / what to do today" in one governed morning read |
| **When it is used** | Daily; embedded on Home; primary attention budget surface |
| **Experience provided** | Briefing UX — greeting, achievements, ≤5 attention topics (ME-2, ME-3, ME-7) |
| **Knowledge consumed** | `route_daily_brief_knowledge_v1()` output → Composer V2 projection; published decisions + KL insights via routing |
| **Must never own** | Select/rank/filter/aggregate (routing owns); decision logic; domain headline templates that reinterpret knowledge |

**Certified reference consumer:** Daily Brief is the first fully routed experience — all future cadences follow this pattern.

### 6.3 Weekly Brief (future)

| Dimension | Definition |
|-----------|------------|
| **Why it exists** | Weekly reflection — patterns and outcomes the daily cadence intentionally omits |
| **When it is used** | Once per week; not a daily re-read |
| **Experience provided** | "What changed this week" — trend awareness without daily noise (ME-2) |
| **Knowledge consumed** | Routed weekly-eligible knowledge items; aggregated outcomes; achievement rollups |
| **Must never own** | Weekly insight invention; independent ranking; truth aggregation; parallel routing pipeline |

### 6.4 Monthly Summary (future)

| Dimension | Definition |
|-----------|------------|
| **Why it exists** | Monthly business understanding — store health and value proof at business cadence |
| **When it is used** | Monthly; executive and owner review |
| **Experience provided** | Outcomes, recovery value, operational confidence — not activity logs (ME-8) |
| **Knowledge consumed** | Routed monthly-eligible knowledge; proof-of-value metrics as presentation of governed proof |
| **Must never own** | Metric calculation; attribution logic; commercial claims; independent proof composition |

### 6.5 Notifications (future)

| Dimension | Definition |
|-----------|------------|
| **Why it exists** | Interrupt merchant only when routed knowledge requires immediate attention outside session |
| **When it is used** | Async; merchant away from dashboard; critical attention only |
| **Experience provided** | Single clear action or awareness — minimal copy (ME-2, ME-3) |
| **Knowledge consumed** | Routing-eligible notification items; same `routing_priority` as other surfaces — truncated to interrupt budget |
| **Must never own** | Notification-specific decision logic; duplicate Brief content; alert rules that bypass routing |

### 6.6 Knowledge Layer

| Dimension | Definition |
|-----------|------------|
| **Why it exists** | Deeper operational insight for merchants who drill beyond today's Brief |
| **When it is used** | Exploration; operational review; cart-adjacent context |
| **Experience provided** | Insight cards with evidence and confidence — organized understanding, not raw data |
| **Knowledge consumed** | KL producer items via routed feed (target state); today partially via `/api/knowledge/report` with JS selection debt |
| **Must never own** | `pickTopInsights`, `INSIGHT_PRIORITY`, OIA builders, surface-local insight ranking — **Phase 2 migration** |

### 6.7 Cart Detail

| Dimension | Definition |
|-----------|------------|
| **Why it exists** | Single-cart context — explain one customer's journey and required merchant action |
| **When it is used** | Merchant opens a specific cart from dashboard or Brief |
| **Experience provided** | Unified explanation (ME-5); clear action gate when routing marks action required |
| **Knowledge consumed** | `merchant_explanation_v1`; routed cart-scoped decisions; proof as supporting context only |
| **Must never own** | `merchantDecisionExecutable` business logic independent of routing visibility; lifecycle copy invention; decision minting |

### 6.8 Mobile (future)

| Dimension | Definition |
|-----------|-------|------------|
| **Why it exists** | Same governed experience on mobile contexts — trust and action on the go |
| **When it is used** | Away from desktop; quick check and critical action |
| **Experience provided** | Compressed Brief + notifications + cart action — ME-2 enforced harder on small screens |
| **Knowledge consumed** | Same routed feeds as desktop surfaces — layout differs; knowledge identical |
| **Must never own** | Mobile-specific insight pipeline; simplified decision logic; offline truth invention |

### 6.9 Executive View (future)

| Dimension | Definition |
|-----------|------------|
| **Why it exists** | Owner-level confidence — store performance without operational detail |
| **When it is used** | Weekly/monthly; delegation contexts |
| **Experience provided** | Trust pyramid Levels 1–3 primarily; Level 4–5 on demand (ME-6, ME-8) |
| **Knowledge consumed** | Routed executive-eligible knowledge; monthly proof surfaces; achievement rollups |
| **Must never own** | Executive-specific KPI calculation; commercial claim generation; parallel proof paths |

### 6.10 Future AI Experience

| Dimension | Definition |
|-----------|------------|
| **Why it exists** | Natural-language access to governed knowledge — not a second intelligence layer |
| **When it is used** | Merchant asks questions in conversational UI |
| **Experience provided** | Answers grounded in routed knowledge with traceability — ME-5 strictly enforced |
| **Knowledge consumed** | Routed knowledge items only; traceability links to evidence, proof, decisions |
| **Must never own** | Truth creation; decision minting; unsourced recommendations; AI-generated proof or evidence |

---

## Section 7 — Merchant Experience Pyramid

Experience depth progresses through five levels. Surfaces may emphasize different levels by cadence — but **Trust must precede Attention**.

```
Level 5 — Improvement
  "I understand how my store becomes better."
        ↑
Level 4 — Decision
  "I know what action matters."
        ↑
Level 3 — Attention
  "I know what deserves my attention."
        ↑
Level 2 — Awareness
  "I know what happened."
        ↑
Level 1 — Trust
  "I know CartFlow is working."
```

| Level | Merchant feeling | Primary surfaces | Principle alignment |
|-------|------------------|------------------|---------------------|
| **1 — Trust** | Platform is under control | Home hero, achievements, calm empty states | ME-6, ME-7 |
| **2 — Awareness** | Events and outcomes understood | Daily Brief, KL, Cart Detail explanation | ME-1, ME-5 |
| **3 — Attention** | Only worthy items surfaced | Daily Brief queue, notifications (future) | ME-3, ME-4 |
| **4 — Decision** | Clear action when needed | Brief actions, Cart Detail gates | ME-4, ME-5 |
| **5 — Improvement** | Business learning over time | Weekly Brief, Monthly Summary, Executive (future) | ME-8 |

**Rule:** No surface may skip Level 1 to deliver Level 3 content. Problem-first presentation violates the pyramid and ME-7.

---

## Section 8 — Architectural rules

These rules extend the **Permanent Architectural Rule** from Merchant Knowledge Infrastructure Closure into the experience era.

### 8.1 Experience consumption rule

**Experience consumes. Experience never owns.**

No experience surface or cadence may own:

| Forbidden ownership | Governed owner |
|--------------------|----------------|
| Truth | Purchase / Lifecycle / Recovery / Provider Truth modules |
| Evidence | Merchant Evidence Registry |
| Proof | Proof Surface |
| Decision | Merchant Decision Layer |
| Explanation | Merchant Explanation |
| Routing | Knowledge Routing |
| Knowledge Production | Governed producers (Explanation, Decision, KL, Proof metadata) |

### 8.2 No parallel experience pipelines

No experience may introduce a **second path** from raw data to merchant advice.

Weekly Brief, Monthly Summary, Notifications, Mobile, Executive, and AI must consume **the same routed knowledge infrastructure** — with cadence- and surface-specific **projection** only.

### 8.3 Projection boundary

**Projection** (layout, copy shortening, visual hierarchy, achievement ordering within routed sets) is permitted.

**Reinterpretation** (new priority, new eligibility, new decision framing, new proof narrative) is forbidden.

Composer V2 after Routing V1 migration is the reference projection boundary.

### 8.4 Attention inheritance

Experience surfaces inherit attention budgets from routing — they do not define independent budgets that reorder platform priority.

| Surface | Budget source |
|---------|---------------|
| Daily Brief | Routing daily budget (≤5 attention topics) |
| Notifications | Routing notification-eligible subset — stricter interrupt cap |
| KL | Routing KL-eligible items — no JS reorder |
| Home | Composed from routed feeds — no Home-local selection |

### 8.5 Achievement-first presentation

Within any routed feed, experience projection **must** present achievements before attention items where both exist (ME-7). This is presentation order of pre-routed content — not surface-side achievement detection.

---

## Section 9 — Relationship to Merchant Knowledge Infrastructure

| Infrastructure artifact | Experience era usage |
|-------------------------|---------------------|
| **Closure Review Verdict B** | Infrastructure complete; experience work is migration + new consumers — not new layers |
| **Merchant Knowledge Infrastructure Declaration** | Experience surfaces are certified consumers |
| **Permanent Architectural Rule** | Experience era inherits — no second pipeline via UI or cadence |
| **Knowledge Routing Foundation KR-1…KR-12** | Routing rules bind all experience surfaces |
| **Knowledge Prioritization Governance KP-1…KP-10** | Surfaces truncate; never re-rank |
| **Daily Brief (certified consumer)** | Template for all future experience builds |

**Era boundary:**

- **Era 1 closed:** Build Merchant Knowledge Infrastructure (Truth → Routing).  
- **Era 2 open:** Build Merchant Experience (presentation, cadence, trust, attention) on top of governed routing.

---

## Section 10 — Out of scope

The following are explicitly **not** part of Merchant Experience Foundation V1:

- Implementation of any surface or cadence  
- UI redesign or visual system changes  
- Routing migration (KL JS, Cart Detail, Home unified feed)  
- AI assistants or generative copy  
- Notification delivery engine  
- Weekly Brief or Monthly Summary product build  
- New producer metadata or routing rules  
- Changes to Truth, Decision, Explanation, or Proof modules  

Foundation defines **architecture and responsibility** — implementation follows in governed phases.

---

## Section 11 — Future experience build sequence (guidance)

Recommended order for experience-era implementation — **not ratified as mandatory**, provided for planning alignment:

| Phase | Focus | Depends on |
|-------|-------|------------|
| **E1** | Complete surface migration to routing (KL, Cart Detail, Home) | Routing V1 + this foundation |
| **E2** | Notifications as interrupt-only routing consumer | E1 patterns |
| **E3** | Weekly Brief | E1 + weekly routing eligibility |
| **E4** | Monthly Summary | Proof metrics presentation + monthly routing |
| **E5** | Mobile / Executive / AI | All above as reference consumers |

Each phase is an **experience build** — not an infrastructure reinvention.

---

## Section 12 — Related documents

| Document | Role |
|----------|------|
| [`merchant_knowledge_infrastructure_closure_review_v1.md`](merchant_knowledge_infrastructure_closure_review_v1.md) | Era 1 closure; Declaration; Permanent Architectural Rule |
| [`knowledge_routing_foundation_v1.md`](knowledge_routing_foundation_v1.md) | Routing principles KR-1…KR-12; surface eligibility |
| [`knowledge_routing_implementation_v1.md`](knowledge_routing_implementation_v1.md) | Routing V1; Daily Brief reference consumer |
| [`merchant_daily_brief_foundation_v1.md`](merchant_daily_brief_foundation_v1.md) | Daily Brief architecture |
| [`merchant_daily_brief_composer_v2.md`](merchant_daily_brief_composer_v2.md) | Projection-only composer; aggregation governance |
| [`proof_of_value_foundation_v1.md`](proof_of_value_foundation_v1.md) | Value proof domains — Monthly/Executive consume |
| [`merchant_decision_foundation_v1.md`](merchant_decision_foundation_v1.md) | Decision classes — experience projects, never mints |

---

## Section 13 — Success criteria

- [x] Merchant Experience defined as governed presentation — not screen collection  
- [x] Architectural position below Infrastructure, above cadences — documented  
- [x] Mission and merchant day model defined  
- [x] Experience principles ME-1…ME-8 ratified  
- [x] Ten experience surfaces defined with consumption/ownership contract  
- [x] Merchant Experience Pyramid (5 levels) defined  
- [x] Architectural rules extend Permanent Architectural Rule into experience era  
- [x] Explicit out-of-scope boundary — no implementation in this document  
- [x] Era 2 officially opened — experience expresses infrastructure, never replaces it  

---

## Merchant Experience Era Declaration

This foundation formally opens the **Merchant Experience Era** — the second major architectural era of CartFlow.

Merchant Knowledge Infrastructure is complete. Merchant Experience defines how merchants **live inside** that infrastructure throughout their workday.

**Merchant Experience is the expression of Merchant Knowledge Infrastructure — not an independent system.**

From this point forward:

- New merchant-facing capabilities are **experience builds** on governed routing.  
- Surfaces project knowledge; they do not own it.  
- Calm, achievement-first, action-bounded presentation is architectural — not cosmetic preference.  
- CartFlow reduces merchant thinking by answering before the merchant asks.

**Merchant Experience Foundation V1 is the permanent reference for all future merchant-facing capabilities.**
