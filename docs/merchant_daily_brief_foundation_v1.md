# CartFlow Merchant Daily Brief Foundation V1

**Status:** Ratified baseline — permanent Daily Brief architecture for Merchant Value  
**Date (UTC):** 2026-07-04  
**Scope:** Defines **what the Merchant Daily Brief is**, **how it consumes decisions**, and **how it protects merchant attention** — not how it is built, ranked, or rendered  
**Authority:** This document is the **Daily Brief counterpart** to [`merchant_decision_foundation_v1.md`](merchant_decision_foundation_v1.md) and [`merchant_decision_governance_v1.md`](merchant_decision_governance_v1.md). Future Daily Brief product code **must implement** this foundation — not invent briefing behavior.  
**Audience:** Product, engineering, commercial, and operations — anyone who surfaces a daily merchant briefing  

**Explicitly out of scope:** Implementation, UI, ranking algorithms, notifications, AI summaries, decision minting, truth evaluation.

**Canonical inputs:**

| Document | Role |
|----------|------|
| [`merchant_decision_foundation_v1.md`](merchant_decision_foundation_v1.md) | Decision classes, attention model, merchant experience contract |
| [`merchant_decision_governance_v1.md`](merchant_decision_governance_v1.md) | DG principles, MD contracts, brief attention budget (§5.1) |
| [`merchant_decision_implementation_v1.md`](merchant_decision_implementation_v1.md) | `merchant_decisions_v1` payload shape; published lifecycle |
| [`proof_of_value_foundation_v1.md`](proof_of_value_foundation_v1.md) | PV-18 Daily Brief contract |
| [`cartflow_value_validation_foundation_v1.md`](cartflow_value_validation_foundation_v1.md) | Original 3–5 item / what-why-action contract |

---

## Executive summary

The Merchant Daily Brief answers one question:

> **If I have only one minute this morning, what are the most important things I should know and act on?**

It is the **first governed consumer** of the Merchant Decision Layer. It **summarizes** published decisions into a concise daily operational briefing. It **never** creates decisions, evaluates truth, or executes business logic.

**Purpose is not reporting.** Purpose is helping merchants know exactly what deserves attention **today**.

---

## Section 1 — Architectural position

The Daily Brief sits **after** the Merchant Decision Layer — never before it.

```
Truth
  ↓
Evidence
  ↓
Proof
  ↓
Merchant Decision Layer     ← sole input authority for brief content
  ↓
Merchant Daily Brief        ← presentation composition only
  ↓
Merchant (reads / acts)
```

| Rule | Meaning |
|------|---------|
| **DB-1** | Daily Brief consumes **`merchant_decisions_v1` published decisions only** — never Truth, Evidence, or Proof directly |
| **DB-2** | Daily Brief **never mints** decisions, recommendations, or actions |
| **DB-3** | Daily Brief **never modifies** decision class, confidence, priority, or suppression |
| **DB-4** | Daily Brief **never runs** business logic (recovery, lifecycle, scoring, AI) |
| **DB-5** | Empty brief is valid — silence protects attention |

**Prime directive:**

> **The brief transforms governed decisions into clarity — it does not create urgency.**

---

## Section 2 — Core principles

Permanent principles. Ordered — earlier principles constrain later ones.

| # | Principle | Governs | It is failing when… |
|---|-----------|---------|---------------------|
| **DBP-1** | **Decisions Are the Only Source** | Every brief item maps 1:1 to a published `decision_id` | Brief item has no decision trace or pulls from KL/truth directly |
| **DBP-2** | **No Decision Generation** | Brief layer is read-only over decision registry output | Brief invents priorities not present in `merchant_decisions_v1` |
| **DBP-3** | **No Recommendation Generation** | Action text comes from decision contract only | Brief adds new CTAs not in decision `merchant_action` / eligible paths |
| **DBP-4** | **No AI Interpretation** | No LLM re-ranking, re-wording that changes meaning, or synthetic items | AI summary replaces or inflates decision contract |
| **DBP-5** | **No Direct Truth Evaluation** | Brief does not read Purchase/Lifecycle/Provider Truth APIs | Brief recomputes «what happened» from raw tables |
| **DBP-6** | **Presentation Only** | Brief composes merchant-readable copy from decision fields | Brief layer owns eligibility or confidence |
| **DBP-7** | **Silence Is Acceptable** | Fewer than 3 items, or zero items, is valid | Brief pads with observations to fill slots |
| **DBP-8** | **Attention Is Protected** | Max 3–5 items (PV-18, MD-A-2) | Brief exceeds budget or duplicates same subject |

Aligns with: **DG-1** Decision Before Presentation, **DG-6** Merchant Attention Is Protected, **PV-18** Daily Brief contract.

---

## Section 3 — Merchant experience contract

Each brief item answers exactly three merchant questions — nothing else.

| Question | Source in decision contract |
|----------|----------------------------|
| **What happened?** | `decision_explanation.rationale_ar` (+ decision class context) |
| **Why does it matter?** | `decision_explanation.why_now_ar` + `commercial_goal` (merchant label) |
| **What should I do?** | `merchant_action` + eligible action path (when Suggested/Critical) |

**Forbidden in brief items:**

- KPI walls, chart dumps, trend tables
- Engineering terms (`lifecycle_truth`, `recovery_key`, module names)
- Duplicate «what happened» across items (same `merge_key`)
- Imperative action when decision class is Observation or Needs Attention without eligible path

**Empty brief copy (when zero published decisions):**

> No decision-required items today — CartFlow is handling routine cases automatically.

(Specific merchant-facing wording is presentation implementation — semantic: **no manufactured urgency**.)

---

## Section 4 — Attention model

Merchant attention is the scarcest resource the brief manages.

### 4.1 Budget

| Constraint | Value | Authority |
|------------|-------|-----------|
| Maximum items | **5** | PV-18, MD-A-2 |
| Target range | **3–5** | Value Validation §5 |
| Minimum items | **0** | DBP-7 — show fewer if fewer exist |
| One decision per item | **Required** | PV-18 |

### 4.2 Selection rules (foundation — not algorithm)

Future implementation selects from **published decisions only**, using **governance-defined priority** already on each decision:

1. Filter: `lifecycle_state == published` and `verification_status == passed`
2. Exclude: suppressed, candidate, eligible-not-published, expired, archived, resolved
3. Sort: by `priority` (class-based, from Decision Layer) — **no new ranking logic**
4. Dedupe: by `merge_key` — one item per subject
5. Cap: take top **≤5** after dedupe

**DBP-9:** Brief selection **must not** introduce AI ranking, heuristic scoring, or commercial-weight tuning beyond decision `priority`.

### 4.3 Silence rules

| Condition | Brief behavior |
|-----------|----------------|
| Zero published decisions | Show empty / calm state — **do not** pull KL cards or raw metrics |
| Fewer than 3 decisions | Show only what exists |
| All decisions Observation class | Valid brief — informational, no false urgency |
| Merchant dismissed decision (future) | Exclude until TTL expires |

---

## Section 5 — Decision eligibility

Daily Brief may **only** surface decisions in **Published** state.

| Lifecycle state | Brief eligible? |
|-----------------|-----------------|
| `candidate` | **No** |
| `eligible` | **No** |
| `published` | **Yes** |
| `consumed` | **No** (already shown — future tracking) |
| `resolved` | **No** |
| `expired` | **No** |
| `archived` | **No** |

| Suppression / verification | Brief eligible? |
|----------------------------|-----------------|
| `suppression_state != none` | **No** |
| `verification_status == suppressed` | **No** |
| `verification_status == passed` | **Yes** (if published) |

**DBP-10:** Brief **never** promotes suppressed decisions to fill slots.

---

## Section 6 — Presentation principles

Foundation constraints for future UI — not visual design.

| Principle | Requirement |
|-----------|-------------|
| **Simple** | One card per decision; scannable in under 60 seconds total |
| **Readable** | Arabic merchant language; confidence and evidence source visible per item |
| **Mobile-first** | Brief must work on phone before desktop |
| **Action-oriented** | Suggested/Critical items show one primary action when decision declares `execute` |
| **No dashboard walls** | Not a replacement for `#carts`, `#home`, or KL — a **daily entry point** |
| **No KPI overload** | No aggregate metrics unless each maps to a published decision (future) |
| **No engineering terminology** | Labels from Merchant Evidence Registry + decision explanation only |

Evidence labels: resolve via `evidence_ids` → registry — same rule as KL and Proof Surface.

---

## Section 7 — Brief item contract (future implementation)

Each brief item is a **view** over one published decision — not a new entity.

| Field | Source |
|-------|--------|
| `brief_item_id` | Stable: `daily_brief:{date}:{decision_id}` |
| `decision_id` | From decision contract (required) |
| `decision_class` | Pass-through — unchanged |
| `priority` | Pass-through — unchanged |
| `what_ar` | From `decision_explanation.rationale_ar` |
| `why_ar` | From `decision_explanation.why_now_ar` |
| `action_ar` | Derived from `merchant_action` + class (no new actions) |
| `if_omitted_ar` | Pass-through from decision |
| `confidence` | Pass-through |
| `evidence_ids` | Pass-through |
| `commercial_goal` | Pass-through |
| `proof_sources` | Pass-through (internal trace — optional merchant display) |

**DBP-11:** Brief item schema is a **projection** — violating fields on the decision contract is forbidden.

---

## Section 8 — Integration (no duplicated governance)

| Layer | Relationship to Daily Brief |
|-------|----------------------------|
| **Merchant Decision Layer** | **Only input** — `merchant_decisions_v1.decisions[]` |
| **Merchant Decision Governance** | Brief must satisfy MD-A-2, MD-7, DG-6 |
| **Proof of Value PV-18** | Brief implements PV-18 — does not redefine it |
| **Knowledge Layer** | **Not** a brief source — KL observations become brief-eligible only after Decision Layer publishes them |
| **Proof Surface** | **Not** a brief source — proof feeds decisions, not brief |
| **Home Overview (`#home`)** | Separate surface — brief may link to Home but must not duplicate unbounded KL feed |
| **Notifications / email** | Future consumers — same decision input, different channel budget |

**Integration rules:**

| ID | Rule |
|----|------|
| **DB-I-1** | Do not duplicate MD-* contracts — reference Decision Governance for eligibility |
| **DB-I-2** | Do not duplicate PV-18 — brief implements max 3–5 / what-why-action |
| **DB-I-3** | Foundation defines **what**; future Daily Brief Governance (optional) defines **enforceable how** |

---

## Section 9 — Ownership model (future)

| Role | Responsibility |
|------|----------------|
| **Decision owner** | `merchant_decision_layer_v1` — mints published decisions |
| **Brief composer** | Future `merchant_daily_brief_v1` — selects + projects published decisions read-only |
| **Presentation owner** | Future Home / mobile UI — renders brief payload |
| **Governance owner** | This foundation + PV-18 + MD-A-2 compliance |

**DB-O-1:** Brief composer may not write back to Decision Layer except **consume** lifecycle (future `consumed` state).

---

## Section 10 — Current baseline

| Capability | Status |
|------------|--------|
| Decision Layer publishes `merchant_decisions_v1` | **Shipped** (cart rows + KL API) |
| Daily Brief composer | **Not implemented** |
| Daily Brief UI | **Not implemented** |
| `#home` KL cards as partial brief | **Legacy pattern** — not governed brief; future brief replaces ad-hoc curation |
| PV-18 enforcement | **Open** until brief ships |

**Maturity target:** Daily Brief **Level 2 Governed** when composer + PV-18 validation gate ship.

---

## Section 11 — Evolution

| Change | Process |
|--------|---------|
| Increase item budget above 5 | **Forbidden** without foundation amendment + trust review |
| Add non-decision brief sources | **Forbidden** — violates DB-1 |
| AI narration layer | Tier 3 only — must cite decision_id; cannot add items |
| New brief consumer (email digest) | Same foundation — channel-specific budget only |

---

## Section 12 — Governance validation checklist

| Requirement | Status |
|-------------|--------|
| Decisions-only input | **Defined** (§1, DB-1) |
| No truth / proof direct consumption | **Defined** (DB-5) |
| Max 3–5 items | **Defined** (§4, PV-18) |
| Published-only eligibility | **Defined** (§5) |
| What / why / action experience | **Defined** (§3) |
| Silence acceptable | **Defined** (DBP-7) |
| No AI / no ranking in foundation | **Defined** (DBP-4, DBP-9) |
| Implementation | **Future** |

---

*End of Merchant Daily Brief Foundation V1.*
