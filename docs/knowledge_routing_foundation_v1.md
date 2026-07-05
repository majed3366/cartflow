# CartFlow Knowledge Routing Foundation V1

**Status:** Ratified baseline — permanent routing architecture for Merchant Value  
**Date (UTC):** 2026-07-05  
**Scope:** Defines **where verified merchant knowledge may appear** and **which knowledge deserves attention first** across CartFlow surfaces — not how knowledge is created, proven, or decided  
**Authority:** This document is the **routing counterpart** to [`merchant_decision_foundation_v1.md`](merchant_decision_foundation_v1.md), [`merchant_explanation_unification_v1.md`](merchant_explanation_unification_v1.md), and [`proof_of_value_foundation_v1.md`](proof_of_value_foundation_v1.md). Future Dashboard, Daily Brief, Knowledge Layer, Monthly Summary, Notifications, Admin, and AI surfaces **must consume routed knowledge** — not independently select what to display.  
**Audience:** Product, engineering, commercial, operations  

**Explicitly out of scope (this document):** Implementation, code, UI, Composer changes, Decision Layer changes, Daily Brief changes, Knowledge Layer changes, notifications delivery, AI generation.

---

## Executive summary

CartFlow knowledge must be **platform-owned**, not **page-owned**.

Today, surfaces may show, hide, duplicate, or miss the same verified fact independently — and may rank attention differently. Knowledge Routing establishes the permanent layer that answers: *given governed knowledge upstream, which surfaces may consume it, in what form, for how long, with what visibility, and in what order?*

Routing **never** creates truth, evidence, proof, or decisions. It **routes** outputs that already passed upstream governance — including **platform-owned prioritization** consumed identically by every surface.

---

## Section 1 — Architectural position

```
Truth
  ↓
Evidence
  ↓
Proof
  ↓
Decision
  ↓
Merchant Explanation
  ↓
Knowledge Routing                    ← this foundation
    ├── Eligibility
    ├── Prioritization
    ├── Lifetime
    └── Surface Visibility
  ↓
Surface Composition
  ↓
Dashboard · Daily Brief · Cart Detail · Knowledge Layer · Monthly Summary · Notifications · Future AI
```

| Stage | Routing may read | Routing may write |
|-------|------------------|-------------------|
| Truth | No | No |
| Evidence | No | No |
| Proof | Yes (metadata only) | No |
| Decision | Yes (published decisions) | No |
| Merchant Explanation | Yes (`merchant_explanation_v1`) | No |
| **Knowledge Routing** | Upstream contracts | **Routed knowledge items only** (eligibility, prioritization, lifetime, visibility) |
| Surface Composition | Routed items (pre-ordered) | Presentation layout only |

**Core principle:** Knowledge belongs to the platform. Surfaces consume knowledge. Surfaces do not own knowledge selection **or prioritization**.

---

## Section 2 — Permanent vocabulary

### 2.1 Knowledge item

A **knowledge item** is a governed, traceable unit of merchant-relevant information that has already passed upstream stages (proof and/or decision and/or explanation).

| Property | Definition |
|----------|------------|
| **What it is** | A platform-owned record describing *what CartFlow knows* and *why it is allowed to say it* — before any surface chooses layout |
| **What it is not** | Raw lifecycle state, a dashboard row, a brief bullet, or a KL card |
| **Minimum upstream** | At least one of: governed proof bundle, published decision, or unified merchant explanation |
| **Example** | «Customer returned after recovery message; follow-up paused; resume scheduled» tied to `explanation_id=return_without_purchase` |

### 2.2 Routed knowledge item

A **routed knowledge item** is a knowledge item **plus routing metadata** declaring which surfaces may consume it and under what rules.

| Property | Definition |
|----------|------------|
| **Adds to knowledge item** | `routing_priority`, `eligible_surfaces`, `surface_lifetime`, visibility flags, aggregation/narrative eligibility |
| **Produced by** | Future Knowledge Routing engine (not implemented in V1 foundation) |
| **Consumed by** | Surface composers only — never by Truth modules |

### 2.3 Surface

A **surface** is a merchant- or admin-facing composition zone with its own layout rules but **no independent knowledge authority**.

| Surface ID | Merchant-facing | Primary question |
|------------|-----------------|------------------|
| `cart_detail` | Yes | What happened on *this* cart and what happens next? |
| `daily_brief` | Yes | What mattered while I was away / what needs attention today? |
| `merchant_home` | Yes | What is the store pulse right now? |
| `knowledge_layer` | Yes | What patterns explain customer behavior? |
| `monthly_summary` | Yes | What outcomes and trends define this period? |
| `notifications` | Yes | What requires immediate out-of-band attention? |
| `admin_operations` | No (admin) | What operational/diagnostic truth supports support and ops? |
| `future_ai` | TBD | Reserved — must consume routed items; no direct Truth |
| `email_digest` | Yes | Async summary of routed attention + achievements |
| `whatsapp_merchant_digest` | Yes | Async merchant digest — governed subset only |

### 2.4 Surface eligibility

**Surface eligibility** is the governed rule set answering: *may this knowledge type appear on this surface, in what shape?*

Eligibility is declared on the **routed knowledge item**, not invented by the surface.

### 2.5 Routing priority

**Routing priority** (`routing_priority`) is the platform-owned integer that determines **which knowledge deserves attention first** across all surfaces.

| Property | Definition |
|----------|------------|
| **Owned by** | Knowledge Routing — calculated once per routed item |
| **Consumed by** | All surfaces identically — Dashboard, Daily Brief, Notifications, Knowledge Layer, Monthly Summary, Future AI |
| **Independent from** | `confidence`, merchant decision class, UI render order, chronological order |
| **Not** | A surface-local sort key, cart `updated_at`, or Composer re-ranking |

Surfaces apply the budget (e.g. Daily Brief shows first 3–5 items) but **never decide which items win**.

### 2.6 Surface lifetime

**Surface lifetime** defines when a routed item remains eligible for a surface (TTL, resolve-on-purchase, resolve-on-archive, session window, brief-date scope). Lifetime does **not** delete upstream truth.

### 2.7 Merchant visibility vs admin visibility

| Flag | Meaning |
|------|---------|
| `merchant_visibility` | May appear on merchant surfaces when routing + eligibility allow |
| `admin_visibility` | May appear on admin/ops surfaces including diagnostics |

**Rule KR-7:** Merchant visibility ≠ admin visibility. Diagnostics default to admin-only.

### 2.8 Notification eligibility

**Notification eligibility** is a strict subset of routing: only routed items explicitly marked `notifications` eligible AND passing attention thresholds may trigger push/email/WhatsApp merchant alerts. Default: **no**.

### 2.9 Aggregation eligibility

**Aggregation eligibility** declares whether a knowledge type may be **grouped** on a surface (e.g. five return events → one Daily Brief achievement topic). Aggregation keys must be stable and traceable.

### 2.10 Narrative eligibility

**Narrative eligibility** declares whether a surface may **compose prose** across multiple routed items (e.g. monthly summary trend sentence). Narrative layers may not invent facts — only connect routed items.

---

## Section 3 — Knowledge item contract (future routed item)

Every routed knowledge item **must** declare the following fields. V1 foundation defines the contract; implementation is future work.

| Field | Type / notes | Routing may change? |
|-------|----------------|---------------------|
| `knowledge_id` | Stable platform ID (e.g. `kr:return_without_purchase:cart:{recovery_key}`) | No — assigned once |
| `knowledge_type` | Canonical type enum (see §4) | No |
| `source_domain` | `recovery` \| `understanding` \| `decision` \| `operational` \| `commercial` | No |
| `evidence_ids` | From Evidence Registry | No |
| `proof_sources` | e.g. `recovery_key`, `insight_key:` | No |
| `decision_ids` | Published decision IDs if applicable | No |
| `explanation_id` | From `merchant_explanation_v1` if applicable | No |
| `confidence` | Governed vocabulary: high / medium / low / insufficient | **No (KR-5)** |
| `merchant_visibility` | bool or scope enum | Routing assigns |
| `admin_visibility` | bool or scope enum | Routing assigns |
| `eligible_surfaces` | Ordered list of surface IDs | Routing assigns |
| `routing_priority` | Platform integer — attention order (see §7) | Routing assigns — **once** |
| `surface_lifetime` | TTL / resolve rules | Routing assigns |
| `action_required` | bool | No — from decision/explanation |
| `attention_level` | `none` \| `informational` \| `attention` \| `urgent` | No — from upstream |
| `aggregation_key` | Deterministic merge key for composers | Routing assigns |
| `narrative_role` | `fact` \| `achievement` \| `attention` \| `trend` \| `closure` \| `diagnostic` | Routing assigns |
| `expiration_rule` | `{ ttl_hours, resolve_on_purchase, resolve_on_archive, … }` | Routing assigns |
| `traceability` | `{ knowledge_id, proof_sources, decision_ids, explanation_id, routed_at }` | Routing adds `routed_at` only |

**Prep today:** `merchant_explanation_v1` already exposes `explanation_id`, `knowledge_event_type`, `eligible_surfaces`, `action_required`, `attention_level` as **non-routing placeholders** until the routing engine ships.

---

## Section 4 — Knowledge types (canonical enum)

One routing rule per knowledge type (**KR-11**).

| `knowledge_type` | Typical upstream | Default `narrative_role` |
|------------------|------------------|--------------------------|
| `cart_lifecycle_event` | Explanation + lifecycle | `fact` |
| `return_without_purchase` | Explanation + monitor decision | `fact` / `achievement` |
| `purchase_confirmed` | Purchase truth + explanation | `closure` |
| `recovery_needs_attention` | Decision (intervention) | `attention` |
| `recovery_scheduled` | Recovery proof | `fact` |
| `message_sent_waiting_reply` | Provider + lifecycle | `fact` |
| `hesitation_pattern` | KL insight + decision observation | `trend` |
| `operational_health` | Ops metrics | `diagnostic` (admin) |
| `merchant_achievement` | Published observation decision | `achievement` |

New types require foundation amendment — surfaces must not invent local types (**KR-12**).

---

## Section 5 — Surface eligibility matrix (governed defaults)

Legend: **Y** = may consume (subject to routing item flags) · **N** = must not · **Agg** = may aggregate · **Nar** = may narrate · **Attn** = may trigger attention UI · **Diag** = diagnostics allowed

| Surface | cart lifecycle | decisions | explanations | KL patterns | achievements | diagnostics |
|---------|----------------|-----------|--------------|-------------|--------------|-------------|
| `cart_detail` | Y | Y (action only) | Y full | N | N | N |
| `daily_brief` | Agg | Y | Agg | Agg | Y | N |
| `merchant_home` | Agg | Y | Agg | Y summary | Y | N |
| `knowledge_layer` | N | Y obs | N | Y | N | N |
| `monthly_summary` | Agg | Agg | Agg | Y trend | Y | N |
| `notifications` | N | Y critical | N | N | N | N |
| `admin_operations` | Y | Y | Y | Y | Y | Y Diag |
| `future_ai` | Routed only | Routed only | Routed only | Routed only | Routed only | Admin pipe |
| `email_digest` | Agg | Y | Agg | Agg | Y | N |
| `whatsapp_merchant_digest` | Agg | Y | Agg | N | Y | N |

### 5.1 Per-surface rules (summary)

**cart_detail**
- May consume: full merchant explanation, single-cart decision action line
- Must not: aggregate cross-cart patterns, show proof diagnostics, invent copy in JS
- Aggregate: No · Narrate: No · Attention: inline only · Diagnostics: No

**daily_brief**
- May consume: published decisions via Composer (already governed); routed achievements + attention topics
- Must not: read raw Truth, raw carts, or lifecycle state keys
- Aggregate: Yes (Composer V2) · Narrate: limited (topic headline) · Attention: Yes · Diagnostics: No

**merchant_home**
- May consume: aggregated activity summaries, KL highlights, brief hero projection
- Must not: duplicate full cart detail blocks
- Aggregate: Yes · Narrate: Yes (short) · Attention: soft · Diagnostics: No

**knowledge_layer**
- May consume: KL insights with claim-level evidence; observation-class decisions
- Must not: per-cart lifecycle diagnostics
- Aggregate: pattern-level · Narrate: Yes · Attention: No by default · Diagnostics: No

**monthly_summary**
- May consume: recovered outcomes, trend aggregates, hesitation patterns
- Must not: urgent intervention items (route to brief/notifications)
- Aggregate: Yes · Narrate: Yes · Attention: No · Diagnostics: No

**notifications**
- May consume: critical-action decisions only when explicitly routed
- Must not: informational achievements, per-cart rows, diagnostics
- Default: **off** for return-without-purchase

**admin_operations**
- May consume: all routed items + diagnostic_internal + proof diagnostic fields
- Aggregate: Yes · Narrate: Yes · Diagnostics: **Yes**

---

## Section 6 — Routing principles (permanent)

| ID | Principle |
|----|-----------|
| **KR-1** | **Platform-owned knowledge** — knowledge items belong to CartFlow platform routing, not to individual pages |
| **KR-2** | **Surfaces consume routed knowledge** — no surface queries Truth directly for merchant display |
| **KR-3** | **No surface-owned selection** — eligibility lives in routing rules, not in template/JS ad hoc filters |
| **KR-4** | **Routing never creates truth** — no new facts at routing stage |
| **KR-5** | **Routing never changes confidence** — confidence is copied from upstream unchanged |
| **KR-6** | **Routing preserves traceability** — every surfaced item links to knowledge_id + upstream IDs |
| **KR-7** | **Merchant visibility ≠ admin visibility** — diagnostics admin-only by default |
| **KR-8** | **Diagnostics never merchant-facing by default** — `diagnostic_internal`, `why_we_know_diagnostic_ar`, ops keys |
| **KR-9** | **Aggregation and narrative are explicit** — must be declared eligible per type + surface |
| **KR-10** | **Unknown remains unknown** — unrouted or ineligible items are omitted, not guessed |
| **KR-11** | **One routing rule per knowledge type** — no duplicate conflicting rules |
| **KR-12** | **Future surfaces extend routing** — register surface ID + eligibility; do not fork selection logic |

---

## Section 7 — Knowledge Prioritization Governance

### Architectural principle

Knowledge Routing is responsible for determining **where** knowledge may appear.

It must also own **which knowledge deserves attention first**.

Surface consumers must **never** invent their own priority model.

| ID | Principle |
|----|-----------|
| **KP-1** | **Priority is platform-owned** — surfaces consume ordered knowledge; they never reorder independently |
| **KP-2** | **Every routed knowledge item must expose `routing_priority`** — independent from `confidence`, merchant decision class, UI order, and chronological order |
| **KP-3** | **Routing priority is calculated once** — Dashboard, Daily Brief, Notifications, Knowledge Layer, and Monthly Summary must all consume the same routing order |
| **KP-4** | **Chronological order is not attention order** — a newer event must never automatically outrank a more important event |
| **KP-5** | **Merchant Attention Budget** — Knowledge Routing owns the attention budget; e.g. Daily Brief may display only the first 3–5 routed items, which must already arrive pre-prioritized; the Daily Brief must not decide which items win |
| **KP-6** | **Surface Independence** — no surface may contain custom selection logic (`if purchase: …`, `if return: …`, `if hesitation: …`); selection belongs to routing; presentation belongs to the surface |
| **KP-7** | **Future-proofing** — adding a new surface requires only consuming routed knowledge; never rebuilding prioritization logic |
| **KP-8** | **Priority must remain deterministic** — no AI, no LLM, no heuristics that differ by surface; given identical knowledge, every surface receives identical ordering |
| **KP-9** | **Knowledge Routing never changes truth** — it only determines visibility, routing, and ordering; Truth, Evidence, Proof, Decision, and Merchant Explanation remain authoritative |
| **KP-10** | **Platform Consistency** — the merchant must never experience Dashboard saying A first, Daily Brief saying B first, and Notifications saying C first for the same operational state; Knowledge Routing guarantees consistency |

### 7.1 What routing priority is not

| Input | May influence routing priority? | Notes |
|-------|--------------------------------|-------|
| `confidence` | No (copied, not re-ranked) | KR-5 |
| Merchant decision class | Indirectly via routing rules only | Decision layer owns class; routing maps class → priority once |
| Cart `updated_at` / event timestamp | No as primary sort | KP-4 — recency ≠ importance |
| Cart monetary value | No as primary sort | Commercial weight belongs in routing rules, not surface JS |
| UI render convenience | No | KP-6 |
| Surface-specific heuristics | **Forbidden** | KP-8 |

### 7.2 Attention budget (routing-owned)

| Surface | Budget type | Routing delivers | Surface may do |
|---------|-------------|------------------|--------------|
| `daily_brief` | Top 3–5 items | Pre-sorted eligible list | Truncate to budget; layout only |
| `notifications` | Critical subset | Pre-sorted notification-eligible items | Delivery channel only |
| `merchant_home` | Hero + summary counts | Pre-sorted hero candidate | Visual hierarchy only |
| `monthly_summary` | Trend + outcome ordering | Pre-sorted aggregate-eligible items | Narrative glue only |
| `dashboard` (carts list) | Row order ≠ attention order | Per-row knowledge for detail; list sort is read-model concern | Must not override brief/notification priority |

**Rule:** Budget application is **truncation**, not **re-ranking**.

### 7.3 Baseline gap (today)

Daily Brief Composer V2 currently applies decision-family aggregation and implicit priority from `merchant_decisions_v1`. This is acceptable as interim surface composition **until** Knowledge Routing ships. Future implementation must migrate priority to routing; Composer becomes presentation-only over pre-prioritized routed items.

---

## Section 8 — Routing examples

### Example 1 — Customer returned without purchase

**Upstream:** `explanation_id=return_without_purchase`, `decision_id=decision_monitor_return`, `attention_level=informational`, `action_required=false`

| Surface | Routing behavior |
|---------|------------------|
| `cart_detail` | **Show** full explanation (what happened / CartFlow paused / resume later) |
| `daily_brief` | **Show** as achievement if merchant was away OR item still published; **omit** if stale/suppressed |
| `merchant_home` | **Optional** activity summary count («عاد N عميل بعد رسالة الاسترجاع») |
| `monthly_summary` | **Aggregate** only — count + trend, not per-cart list |
| `admin_operations` | **Show** diagnostics (`lifecycle_state`, proof diagnostic chain) |
| `notifications` | **No** by default |
| `knowledge_layer` | **No** (cart-scoped event, not pattern) |

### Example 2 — Repeated shipping hesitation

**Upstream:** KL insight `hesitation_pattern:shipping`, observation decision, evidence `hesitation_reason`

| Surface | Routing behavior |
|---------|------------------|
| `cart_detail` | **Show** per-cart when reason tag = shipping on that row |
| `knowledge_layer` | **Show** as cross-cart pattern card |
| `daily_brief` | **Show** if priority threshold met (pattern becomes attention) |
| `monthly_summary` | **Show** trend narrative |
| `notifications` | **Only if** critical threshold policy exists (future) |
| `admin_operations` | Full trace + insight_key |

### Example 3 — Purchase confirmed

**Upstream:** Purchase truth, `explanation_id=purchase_confirmed`, recovery stopped

| Surface | Routing behavior |
|---------|------------------|
| `cart_detail` | **Show** closure explanation |
| `daily_brief` | **Achievement** topic |
| `monthly_summary` | **Recovered outcome** aggregate |
| `merchant_home` | May increment recovered KPI (read model — not routing mint) |
| `admin_operations` | Diagnostic trace (attribution, timestamps) |
| `notifications` | **No** unless merchant opts in to recovery alerts (future policy) |

---

## Section 9 — Relationship to existing implementations (baseline)

| Layer | Today | After routing implementation |
|-------|-------|----------------------------|
| Cart detail | Consumes `merchant_explanation_v1` directly | Consumes **routed** cart_detail slice of same item |
| Daily Brief | Consumes `merchant_decisions_v1` via Composer V2 | Consumes routed brief-eligible decisions + achievements |
| Knowledge Layer | KL report + claim evidence | Consumes routed pattern items only |
| Proof surface | Attached to rows; **not** merchant cart detail UI | Unchanged upstream; admin/diagnostic path only |
| Explanation | `merchant_explanation_v1` mints copy | Upstream input to routing — not a surface |

**V1 foundation does not change any of the above.** It defines the contract future routing must implement.

---

## Section 10 — Anti-patterns (forbidden)

1. Dashboard JS filtering carts by raw `customer_lifecycle_state` for display copy  
2. Daily Brief reading `AbandonedCart` rows directly  
3. Knowledge Layer minting decisions from raw SQL aggregates without decision layer  
4. Monthly summary listing raw cart IDs as «insights»  
5. Notifications triggered from log status strings (`skipped_anti_spam`, etc.)  
6. Merchant UI rendering `diagnostic_internal` or `why_we_know_diagnostic_ar`  
7. Each surface defining its own `eligible_surfaces` logic diverging from central routing  
8. Daily Brief Composer (or any surface) re-sorting by cart value, recency, or decision class after routing  
9. Notifications choosing a different «top» item than Daily Brief for the same store state  
10. Surface JS containing `if (purchase)` / `if (return)` / `if (hesitation)` selection branches for knowledge inclusion  

---

## Section 11 — Evolution and amendment

| Change type | Process |
|-------------|---------|
| New surface ID | Add row to §5 + §2.3; extend routing registry; KR-12 |
| New knowledge_type | Add to §4 + routing rule; amend SYSTEM_SUMMARY |
| New eligibility default | Version routing policy doc; do not silently change surface behavior |
| Priority rule change | Amend §7 + KP-*; must remain deterministic (KP-8) |
| Implementation | Separate design doc + tests; Truth/Decision/Composer unchanged unless defect |

**Next expected artifact (not this task):** `knowledge_routing_implementation_v1.md` + `services/knowledge_routing_v1.py` consuming `merchant_explanation_v1` + published decisions.

---

## Section 12 — Related documents

| Document | Role |
|----------|------|
| [`proof_of_value_foundation_v1.md`](proof_of_value_foundation_v1.md) | Truth → Evidence → Proof chain |
| [`merchant_decision_foundation_v1.md`](merchant_decision_foundation_v1.md) | Decision stage contract |
| [`merchant_decision_governance_v1.md`](merchant_decision_governance_v1.md) | Decision eligibility and suppression |
| [`merchant_explanation_unification_v1.md`](merchant_explanation_unification_v1.md) | Unified cart explanation (routing input) |
| [`merchant_daily_brief_foundation_v1.md`](merchant_daily_brief_foundation_v1.md) | Brief as decision consumer |
| [`merchant_daily_brief_composer_v2.md`](merchant_daily_brief_composer_v2.md) | Aggregation governance (surface composition) |
| [`return_without_purchase_merchant_explanation_v1.md`](return_without_purchase_merchant_explanation_v1.md) | Reference routing example |

---

## Success criteria (foundation)

- [x] Knowledge item and routed knowledge item defined  
- [x] Surface vocabulary and eligibility matrix defined  
- [x] Full knowledge item contract specified (including `routing_priority`)  
- [x] KR-1…KR-12 principles ratified  
- [x] KP-1…KP-10 prioritization governance ratified  
- [x] Three worked routing examples documented  
- [x] Explicit out-of-scope: no implementation in V1 foundation  
