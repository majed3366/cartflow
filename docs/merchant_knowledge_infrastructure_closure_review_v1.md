# CartFlow Merchant Knowledge Infrastructure Closure Review V1

**Status:** Finalized — official architectural declaration recorded  
**Date (UTC):** 2026-07-05  
**Scope:** Integrated pipeline review (Truth → Surface) — certification only, no code changes  
**Authority:** Closes the Merchant Knowledge Infrastructure build era documented across Foundation, Standardization, Producer Metadata, Routing Implementation, and prior readiness reviews  
**Audience:** Product, engineering, architecture review  

**Explicitly out of scope:** Code changes, implementation, UI redesign.

---

## Executive summary

CartFlow now possesses a **governed, platform-owned Merchant Knowledge Infrastructure** with a complete documented lifecycle from Truth through Knowledge Routing to Surface Projection.

The **infrastructure stack is certified complete**. **Surface migration is partially complete** — Daily Brief is the first fully routed consumer; Knowledge Layer JS, Cart Detail gates, and future surfaces retain documented selection debt.

**Final verdict: B — Minor architectural refinements remain** (infrastructure complete; consumer migration only).

This document includes the official **Merchant Knowledge Infrastructure Declaration** and **Permanent Architectural Rule**. The Merchant Knowledge Infrastructure era is **officially closed**.

---

## Pipeline under review

```
Truth
  ↓
Evidence Registry
  ↓
Proof Surface
  ↓
Merchant Decision Layer
  ↓
Merchant Explanation
  ↓
Knowledge Producer (metadata)
  ↓
Knowledge Routing
  ↓
Projection
  ↓
Surface Composition
  ↓
Dashboard · Daily Brief · Cart Detail · Knowledge Layer · (future surfaces)
```

---

## Section 1 — Truth ownership

| Check | Status | Evidence |
|-------|--------|----------|
| Truth remains authoritative | **Pass** | `purchase_truth`, `recovery_truth_timeline_v1`, `customer_lifecycle_states_v1`, `lifecycle_closure_records_v1` — write durable state only |
| Downstream never recreates Truth | **Pass** | Decision, Explanation, Proof, Routing, Composer read upstream; no Truth writes in presentation path |
| Downstream never modifies Truth | **Pass** | Routing V1 and Producer Metadata are additive metadata only; no Truth module edits in this era |

**Certification:** Truth ownership intact. Purchase, Lifecycle, Recovery, Provider Truth modules unaffected by Merchant Knowledge Infrastructure work.

---

## Section 2 — Evidence ownership

| Check | Status | Evidence |
|-------|--------|----------|
| Evidence Registry single authority | **Pass** | `merchant_evidence_registry_v1.py` — stable `evidence_id` → label |
| Claim-level evidence ownership | **Pass** | `merchant_claim_evidence_v1.py` — per-insight `evidence_id`; no section footnote |
| Registry-driven wording | **Pass** | Proof Surface + KL API consume registry; normalization split (`hesitation_reason` / `customer_reply`) |

**Certification:** Evidence Before Advice satisfied. No duplicate evidence vocabulary introduced in Routing or Composer.

---

## Section 3 — Proof ownership

| Check | Status | Evidence |
|-------|--------|----------|
| Proof Surface proves only | **Pass** | `merchant_proof_surface_v1.py` — composes steps, confidence, evidence; no decisions |
| Proof logic not in Decision | **Pass** | Decision Layer reads proof bundle; does not mint recovery/provider truth |
| Proof logic not in Routing | **Pass** | Routing reads `confidence`, `proof_sources` metadata; never evaluates proof steps |

**Note:** Proof block attached server-side but not rendered in cart detail merchant block (pre-existing). Not an ownership violation — presentation gap only.

---

## Section 4 — Decision ownership

| Check | Status | Evidence |
|-------|--------|----------|
| Decision Layer sole decision owner | **Pass** | `merchant_decision_layer_v1.py` + registry — mints `merchant_decisions_v1` |
| Routing never creates decisions | **Pass** | `knowledge_routing_v1.py` — routes existing items only |
| Composer never creates decisions | **Pass** | Composer V2 projects routed items; no decision minting |
| Dashboard never creates decisions | **Pass** | JS reads payloads; no decision generation |

**Certification:** Decision Before Presentation satisfied for Daily Brief path.

---

## Section 5 — Merchant Explanation ownership

| Check | Status | Evidence |
|-------|--------|----------|
| Explanation sole cart narrative authority | **Pass (cart detail)** | `merchant_explanation_v1.py` — catalog + sanitizer; cart JS reads `merchant_explanation_v1` |
| No surface generates wording independently | **Partial** | KL insights still mint `title_ar`/`message_ar` in `knowledge_insights_v1.py`; Brief headlines projected from routed payload (neutral format) |
| No lifecycle term leaks | **Pass (cart detail)** | Sanitizer + tests block `waiting_*`, diagnostics admin-only |

**Gap (non-blocking):** `customer_lifecycle_states_v1` still emits parallel Arabic before Explanation sync. Explanation wins on attach order. Legacy modules exist but normal-carts path uses Explanation as canonical display.

**Certification:** Merchant Explanation Before Surface satisfied for **Cart Detail**. KL pattern copy remains a parallel producer path until KL fully consumes routed narrative slices.

---

## Section 6 — Knowledge Producer Standardization

| Check | Status | Evidence |
|-------|--------|----------|
| Only governed producers publish knowledge | **Pass (by contract)** | Explanation, Decision, KL API; JS/templates excluded |
| Producer metadata complete | **Pass** | `knowledge_producer_metadata_v1.py` — 18-field contract |
| `knowledge_id` deterministic | **Pass** | `expl:…`, `dec:…`, `kl:…` — tested for stability |
| Traceability complete | **Pass** | `origin_layer`, `origin_identifier`, `source_records`, `producer_version`, `created_from` |
| Producer contract consistent | **Pass** | `validate_knowledge_metadata_v1()` gate |

**Certification:** Knowledge Production Standardization V1 + Producer Metadata Implementation V1 closed.

---

## Section 7 — Knowledge Routing

| Check | Status | Evidence |
|-------|--------|----------|
| Domain-neutral | **Pass** | No purchase/return/hesitation branching in `knowledge_routing_v1.py`; unit test enforced |
| Consumes standardized knowledge only | **Pass** | Requires `knowledge_id` + metadata validation |
| Owns eligibility | **Pass** | `is_surface_eligible_v1`, `is_merchant_visible_v1` |
| Owns priority | **Pass** | `compute_routing_priority_v1`, `routing_priority` on routed items |
| Owns visibility | **Pass** | Surface filter + merchant/admin flags passed through |
| Owns lifetime | **Pass (read)** | `expiration_rule` passed through; no TTL engine yet |
| Owns distribution | **Pass** | Aggregation by `aggregation_key`; section assignment by metadata |
| Owns nothing else | **Pass** | No truth/decision/explanation minting; no domain templates |

**Certification:** Routing Neutrality and Knowledge Neutrality satisfied. Routing Transparency via `traceability.routing_priority_basis`.

---

## Section 8 — Projection

| Check | Status | Evidence |
|-------|--------|----------|
| Projection only | **Pass (Daily Brief)** | `project_routed_topic_v2` — headline/why/action from `knowledge_payload` |
| No selection | **Pass (Daily Brief compose path)** | Routing selects; Composer iterates routed feed |
| No ranking | **Pass (Daily Brief compose path)** | Order preserved from routing sort |
| No aggregation ownership | **Pass (Daily Brief compose path)** | Routing aggregates |
| No business logic | **Pass (Daily Brief compose path)** | Neutral headline projection; no `DECISION_ID_*` templates in compose path |

**Legacy exports:** `group_decisions_into_topics`, `is_achievement_decision` delegate to routing — test compatibility only.

---

## Section 9 — Surface composition audit

| Surface | Consumes knowledge | Owns selection? | Status |
|---------|-------------------|-----------------|--------|
| **Daily Brief** | Routed feed via Composer V2 | **No** (Phase 1 complete) | **Certified consumer** |
| **Cart Detail** | `merchant_explanation_v1` | **Partial** — JS executability gate (`merchantDecisionExecutable`) | Migration Phase 2 |
| **Knowledge Layer** | KL API + metadata | **Yes (violation)** — JS `pickTopInsights`, `INSIGHT_PRIORITY`, OIA builders | Migration Phase 2 |
| **Dashboard (carts)** | Row payloads | **Partial** — tab/heuristic filters (read-model, not knowledge mint) | Acceptable |
| **Merchant Home** | Brief + KL + KPIs | **Partial** — independent fetches, no unified routing feed | Migration Phase 3 |
| **Monthly Summary** | Metrics only | **No** (no knowledge yet) | Greenfield consumer |
| **Notifications** | None | **No** | Greenfield consumer |
| **Future AI** | None | **No** | Must consume routing only |

**Platform-owned knowledge:** Satisfied at infrastructure level. **Surfaces Never Decide:** Satisfied for Daily Brief; **not yet** for Knowledge Layer JS.

---

## Section 10 — Architectural principles

| Principle | Status |
|-----------|--------|
| Truth Before Intelligence | **Pass** |
| Evidence Before Advice | **Pass** |
| Decision Before Presentation | **Pass** |
| Merchant Explanation Before Surface | **Pass (cart detail)** / Partial (KL) |
| Knowledge Before UI | **Pass (Daily Brief)** / Partial (KL) |
| Routing Neutrality | **Pass** |
| Knowledge Neutrality | **Pass** |
| Routing Transparency | **Pass** |
| Platform-owned Knowledge | **Pass** |
| Surfaces Consume | **Partial** — Daily Brief yes; KL no |
| Surfaces Never Decide | **Partial** — KL JS remains |

---

## Section 11 — Pipeline health

| Transition | Governed? | Owner clear? | Duplicate? |
|------------|-----------|--------------|------------|
| Truth → Evidence | Yes | Registry | No |
| Evidence → Proof | Yes | Proof Surface | No |
| Proof → Decision | Yes | Decision Layer | No |
| Decision → Explanation | Yes | Explanation (parallel lifecycle copy mirrored) | Minor mirror only |
| Explanation → Producer | Yes | Producer metadata | No |
| Producer → Routing | Yes | Routing V1 | No |
| Routing → Projection | Yes | Composer V2 | No |
| Projection → Surface | Yes | JS/templates | No |

**No missing layer.** **No orphan layer.** **Duplicate ownership:** KL JS selection (interim); lifecycle SoT parallel copy (mirrored by Explanation).

---

## Section 12 — Scenario traceability

### Scenario 1 — Customer returned without purchase

| Stage | Module | Output |
|-------|--------|--------|
| Truth | Lifecycle + Recovery timeline | `waiting_purchase_window`, return events |
| Evidence | Registry | `customer_journey`, `hesitation_reason` |
| Proof | Proof Surface | Recovery steps, confidence |
| Decision | Decision Layer | `decision_monitor_return` (observation/monitor) |
| Explanation | Explanation V1 | `explanation_id=return_without_purchase` |
| Producer | Metadata | `expl:return_without_purchase:{store}:{rk}` |
| Routing | Routing V1 | Achievement section, aggregated by `aggregation_key` |
| Projection | Composer V2 | Brief achievement topic |
| Surface | Daily Brief JS | Renders projected headline |

**Explainable end-to-end:** Yes.

### Scenario 2 — Shipping hesitation

| Stage | Module | Output |
|-------|--------|--------|
| Truth | Metrics + reason capture | Hesitation bucket `shipping` |
| Evidence | Registry | `hesitation_reason` |
| Proof | KL claim evidence | Per-card evidence |
| Decision | KL observation decision | `decision_kl_observation:hesitation_top_reason` |
| Explanation | N/A (pattern-level) | — |
| Producer | KL metadata | `kl:hesitation_top_reason:{store}:7d` |
| Routing | Routing V1 | Eligible for `daily_brief` + `knowledge_layer` |
| Projection | Composer (brief) / KL JS (KL) | **Brief routed; KL JS still local pick** |
| Surface | Home KL cards | JS OIA builders |

**Explainable:** Yes upstream. **KL surface selection not yet routing-owned.**

### Scenario 3 — Purchase confirmed

| Stage | Module | Output |
|-------|--------|--------|
| Truth | Purchase Truth | Purchase record |
| Evidence | Registry | Purchase/lifecycle evidence |
| Proof | Proof Surface | Closure steps |
| Decision | Suppressed / addressed | `already_addressed` |
| Explanation | Explanation V1 | `explanation_id=purchase_confirmed`, `narrative_role=closure` |
| Producer | Metadata | `expl:purchase_confirmed:…` |
| Routing | Brief-ineligible (typically) | Cart detail eligible |
| Projection | Cart detail JS | Explanation block |
| Surface | Cart row | Closure copy |

**Explainable:** Yes. Brief correctly omits closed carts via decision suppression + routing eligibility.

### Scenario 4 — No contact available

| Stage | Module | Output |
|-------|--------|--------|
| Truth | Lifecycle | `needs_intervention`, missing phone |
| Decision | Decision Layer | `decision_obtain_contact` |
| Producer | Metadata | `dec:decision_obtain_contact:…` |
| Routing | Attention section, priority from metadata | Brief topic |
| Surface | Daily Brief | Aggregated attention topic |

**Explainable:** Yes.

### Scenario 5 — Merchant intervention required

| Stage | Module | Output |
|-------|--------|--------|
| Truth + Decision | Intervention decision | `decision_contact_customer`, `action_required` |
| Explanation | `needs_merchant_attention` | Urgent attention metadata |
| Routing | Attention section, high priority | Routed item |
| Cart Detail | Attention semantics + JS gate | Executable WhatsApp when eligible |

**Explainable:** Yes. Cart executability gate is **presentation/interaction**, not knowledge minting — migrate to routing visibility in Phase 2.

---

## Section 13 — Regression

| Area | Status |
|------|--------|
| Purchase Truth | Unchanged |
| Lifecycle Truth | Unchanged (parallel copy mirror only) |
| Recovery scheduling | Unchanged |
| Provider Truth | Unchanged |
| Merchant workflow | Preserved |
| UI shape | Preserved — Brief payload shape intact; aggregated headline copy neutralized (non-breaking) |

**Tests:** 39/39 passing on routing + brief + producer suites (2026-07-05 verification).

---

## Section 14 — Future readiness

Can the following be built as **pure routing consumers** without new knowledge ownership?

| Future consumer | Ready? | Notes |
|-----------------|--------|-------|
| Weekly Brief | **Yes** | Same routing feed as Daily Brief; different projection/budget |
| Monthly Summary | **Yes** | Consume routed `narrative_role: trend` + aggregates |
| Merchant Notifications | **Yes** | `eligible_surfaces: notifications` + attention threshold |
| Executive Summary | **Yes** | Routing feed + narrative projection |
| Merchant Mobile App | **Yes** | Consume routed API; no local selection |
| Merchant AI Assistant | **Yes (with guardrails)** | Must read routed items + traceability only; no direct Truth |
| Revenue Intelligence | **Partial** | Needs future Attribution producer — infrastructure slot defined |
| Product Intelligence | **Partial** | Future producer type in Standardization §1.2 |

**Do not build new knowledge selection in any consumer.** Extend routing registry for new surfaces only.

---

## Section 15 — Remaining refinements (Phase 2–3)

These are **surface migration** items — not missing infrastructure:

1. **Knowledge Layer JS** — retire `pickTopInsights` / `INSIGHT_PRIORITY`; consume routed KL slice  
2. **Cart Detail** — honor `eligible_surfaces`; migrate executability gate to routing visibility  
3. **Merchant Home** — unified routing feed (Brief + KL + activity)  
4. **Explanation routing input** — include explanation items in brief routing feed where eligible  
5. **Legacy lifecycle parallel copy** — deprecate duplicate Arabic from lifecycle SoT display path  
6. **Notifications / Monthly Summary** — implement as greenfield routing consumers  

---

## Section 16 — Final verdict

### **B — Minor architectural refinements remain**

### Infrastructure Status

**Merchant Knowledge Infrastructure is architecturally complete.**

The remaining work consists of migrating existing merchant-facing consumers to the governed infrastructure — for example Knowledge Layer JS, Cart Detail routing consumption, and Merchant Home routing consumption.

These are **migration items**. They are **not** infrastructure gaps.

**No additional infrastructure layers are required.**

Future work focuses on **migration and new consumers** rather than new architectural foundations.

| Criterion | Assessment |
|-----------|------------|
| Infrastructure stack complete | **Yes** — Truth through Routing documented and implemented |
| Governed lifecycle exists | **Yes** |
| Daily Brief certified consumer | **Yes** |
| All surfaces migrated | **No** — KL JS primary gap |
| Safe to build new consumers | **Yes** — as routing consumers only |
| Infrastructure era closed | **Yes** — no new infrastructure layers required |

### Interpretation

The **Merchant Knowledge Infrastructure era is formally closed.** CartFlow has a permanent platform capability:

- Producers publish standardized knowledge  
- Routing distributes it domain-neutrally  
- Surfaces project it  

Remaining work is **consumer migration and new consumer build** — not infrastructure invention.

**Not A** because Knowledge Layer still owns selection in JS.  
**Not C** because no pipeline layer is missing.  
**Not D** because new consumers can proceed using the Daily Brief pattern while Phase 2 migration runs in parallel.

---

## Section 17 — Related documents

| Document | Role |
|----------|------|
| [`proof_of_value_foundation_v1.md`](proof_of_value_foundation_v1.md) | Truth → Proof chain |
| [`merchant_decision_foundation_v1.md`](merchant_decision_foundation_v1.md) | Decision architecture |
| [`merchant_explanation_unification_v1.md`](merchant_explanation_unification_v1.md) | Explanation layer |
| [`knowledge_production_standardization_v1.md`](knowledge_production_standardization_v1.md) | Producer standard |
| [`knowledge_producer_metadata_implementation_v1.md`](knowledge_producer_metadata_implementation_v1.md) | Producer metadata |
| [`knowledge_routing_foundation_v1.md`](knowledge_routing_foundation_v1.md) | Routing foundation |
| [`knowledge_routing_implementation_v1.md`](knowledge_routing_implementation_v1.md) | Routing V1 |
| [`knowledge_routing_readiness_review_v1.md`](knowledge_routing_readiness_review_v1.md) | Pre-routing gate |

---

## Success criteria (closure review)

- [x] Complete pipeline reviewed as integrated system  
- [x] All 9 verification areas addressed  
- [x] Architectural principles assessed  
- [x] Five scenario traces documented  
- [x] Regression confirmed  
- [x] Future readiness assessed  
- [x] Single verdict: **B**  
- [x] Merchant Knowledge Infrastructure era certified closed  
- [x] Official declaration and permanent architectural rule recorded  

---

## Merchant Knowledge Infrastructure Declaration

This review formally certifies that CartFlow now possesses a governed Merchant Knowledge Infrastructure.

Merchant knowledge is no longer owned by individual pages, widgets, or user interfaces.

Instead, merchant knowledge is produced, governed, routed, and consumed through a single platform-owned pipeline.

Architectural responsibilities are permanently defined as follows:

**Truth** is produced once.

**Evidence** is registered once.

**Proof** is evaluated once.

**Merchant Decisions** are minted once.

**Merchant Explanations** are authored once.

**Knowledge** is published once by governed producers.

**Knowledge Routing** determines where knowledge belongs.

**Projection** prepares routed knowledge for presentation.

**Surfaces** consume routed knowledge without recreating, reinterpreting, reprioritizing, or redistributing platform knowledge.

Merchant-facing experiences are therefore **consumers of platform knowledge** rather than independent owners of business logic.

Future capabilities—including Weekly Brief, Monthly Summary, Notifications, Executive Dashboards, Mobile Applications, AI Assistants, Product Intelligence, Revenue Intelligence, and future merchant experiences—**must integrate into this governed pipeline** rather than creating parallel knowledge paths.

**This declaration establishes Merchant Knowledge as a permanent platform capability of CartFlow.**

From this point forward, new features extend the platform by **consuming governed knowledge**, not by rebuilding knowledge ownership.

---

## Permanent Architectural Rule

**No future feature may introduce a second merchant knowledge pipeline.**

Every new capability must integrate into the existing Merchant Knowledge Infrastructure.

**Parallel knowledge ownership is permanently prohibited.**
