# CartFlow Merchant Decision Governance V1

**Status:** Governance (authoritative decision contract) — no implementation, no runtime change, no UI design  
**Date (UTC):** 2026-07-04  
**Phase:** Merchant Value Era — Foundation → **Governance** → (future) Decision Engine → Surfaces → Enforcement  
**Domain:** Merchant-facing **decisions** — attention, priority, eligibility, expiration, and action prompts  
**Single source of concepts:** [`docs/merchant_decision_foundation_v1.md`](merchant_decision_foundation_v1.md)  
**Precedence:** Subordinate to [`engineering_constitution_v1.md`](engineering_constitution_v1.md) for engineering truth; subordinate to [`proof_of_value_governance_v1.md`](proof_of_value_governance_v1.md) for proof-stage rules; **owns the Decision stage only** in the Truth→Evidence→Proof→**Decision**→Action→Outcome pipeline. Peer to Proof of Value Governance for merchant attention — does not override Purchase Truth, Lifecycle Truth (LT-C1), Provider Truth, or Evidence Registry ownership.

> This document defines **WHEN CartFlow may ask for merchant attention** and **HOW decisions must be governed** — not how decisions are scored, ranked, or rendered. Future Daily Brief, Decision Engine, notifications, and AI summaries **implement this governance**; they do not invent decision behavior.

**Canonical inputs (no new decision types invented):**

| Document | Role |
|----------|------|
| [`merchant_decision_foundation_v1.md`](merchant_decision_foundation_v1.md) | Decision classes, vocabulary, attention model, foundation contract |
| [`proof_of_value_governance_v1.md`](proof_of_value_governance_v1.md) | PG-2/3/5, PV-4/17/18 — proof-stage gates decisions must pass |
| [`merchant_evidence_registry_foundation_v1.md`](merchant_evidence_registry_foundation_v1.md) | Normalized `evidence_id` authority |
| [`claim_level_evidence_ownership_v1.md`](claim_level_evidence_ownership_v1.md) | Per-claim evidence + confidence |
| [`proof_surface_implementation_v1.md`](proof_surface_implementation_v1.md) | Proof composition input to decisions |
| [`cartflow_merchant_action_matrix_v1.md`](cartflow_merchant_action_matrix_v1.md) | Eligible action registry (partial today) |
| [`merchant_value_audit_v1.md`](merchant_value_audit_v1.md) | Decision maturity **Level 0–1**; open gaps |

---

## 0. Scope, authority, and traceability

**In scope:** every merchant-visible **decision** — attention requests, priority rankings, brief slots, notification triggers, imperative CTAs framed as «what to do next», and class declarations (Observation through Critical Action).

**Out of scope (governed elsewhere, must not be weakened):**

| Area | Governed by |
|------|-------------|
| Truth minting | Engineering Constitution; LT-C1 CI gate |
| Evidence labels | Merchant Evidence Registry |
| Proof composition | Proof of Value Governance PG-3; Proof Surface |
| Scoring / ranking algorithms | Future implementation — must comply with this governance |
| AI narration | Tier 3 — never creates decisions |
| Daily Brief product code | Future — must implement MD contracts |

**Decision Governance owns only the Decision stage:**

```
Truth → Evidence → Proof → [DECISION GOVERNANCE] → Merchant Action → Business Outcome
```

**Current compliance posture (honest baseline):** KL cards are **Observations** with claim-level evidence — not full decisions. `#carts` lifecycle surfaces proof + partial decision copy. **PV-17 open:** intervention without executable action. **PV-18 open:** Daily Brief not shipped. Governance adoption defines target state — not full compliance today.

---

## Section 1 — Decision Governance Principles

Permanent principles. Ordered — earlier principles constrain later ones. Map to foundation §3 and Proof of Value PG-* where noted.

| # | Principle | Governs | It is failing when… |
|---|-----------|---------|---------------------|
| **DG-1** | **Decision Before Presentation** | Attention, badges, brief slots, notifications are decision outputs | UI layout or copy creates urgency without declared decision class + contract |
| **DG-2** | **Proof Before Decision** | No decision without upstream proof bundle | Decision shown without `proof_source` trace to Tier 0–2 evidence |
| **DG-3** | **No Decision Without Evidence** | Every decision lists normalized registry `evidence_id`(s) | Decision uses hard-coded wording or merged evidence meanings |
| **DG-4** | **Unknown Never Produces Action** | `confidence=insufficient` or `unknown` → no Suggested/Critical class | Weak evidence triggers imperative CTA or alert |
| **DG-5** | **Silence Is Better Than Weak Advice** | Withhold decision when contract cannot be met | Empty slot filled with low-confidence guess |
| **DG-6** | **Merchant Attention Is Protected** | Attention budget enforced per surface (§5) | Dashboard floods merchant with equal-priority items |
| **DG-7** | **Every Decision Must Be Explainable** | what / why / why now / if omitted / evidence / confidence | Merchant sees «act now» without rationale |
| **DG-8** | **Every Decision Must Have Commercial Purpose** | One primary `commercial_goal` (§7) | Decision exists only because data is available |
| **DG-9** | **No Decision Without Eligible Action** | Suggested/Critical requires action path or honest downgrade (PV-17) | Button or imperative with no executable path |
| **DG-10** | **Decision Confidence Must Be Honest** | Weakest-link across evidence; presentation cannot raise (PG-2) | Styled urgency contradicts confidence level |

**Prime directive (Decision domain):**

> CartFlow must **earn** the right to interrupt the merchant — with proof, purpose, and an honest path forward — or **remain silent**.

---

## Section 2 — Decision Ownership

Every decision capability requires **named ownership** across six dimensions. Presentation **consumes** decisions; presentation **never creates** decisions (DG-1).

### 2.1 Ownership dimensions

| Dimension | Owner role (future module) | Responsibility | Must not… |
|-----------|---------------------------|----------------|-----------|
| **Decision eligibility** | Decision Engine / eligibility evaluator | Determine whether proof qualifies for a decision class | Infer truth not in proof bundle |
| **Decision confidence** | Decision Engine + evidence chain | Assign weakest-link confidence from proof inputs | Override KL or Proof Surface confidence upward |
| **Decision priority** | Attention allocator (future) | Rank within surface budget | Prioritize without class + commercial goal |
| **Decision expiration** | Decision lifecycle manager | TTL, auto-resolve, snooze, dismiss | Leave stale Critical decisions visible |
| **Decision suppression** | Silence gate (future) | Apply §5 silence rules | Suppress without audit log |
| **Decision lifecycle** | Decision registry (future) | mint → surface → act/dismiss → expire → archive | Skip contract registration |

### 2.2 Three-owner model (aligns with Proof of Value §2)

| Role | Decision domain responsibility | Owner (today / future) |
|------|-------------------------------|------------------------|
| **Truth owner** | Supplies Tier 0–1 facts decisions depend on | LT-C1, Purchase/Recovery/Provider Truth modules |
| **Proof owner** | Composes merchant-visible proof bundle | `merchant_proof_surface_v1`, KL API + claim evidence enrichers |
| **Decision owner** | Mints governed decision contract; eligibility + class | **Future** `merchant_decision_engine_v1` — governance defined here |
| **Presentation owner** | Renders decision payload read-only | Dashboard lazy loaders, future Daily Brief UI, notifications |
| **Governance owner** | MD contract compliance, attention rules, release gate | This document; product + merchant-surfaces engineering lead |

### 2.3 Ownership contracts

| ID | Contract |
|----|----------|
| **MD-O-1** | No merchant surface may **mint** a decision — only consume decision registry payload. |
| **MD-O-2** | Presentation styling (color, badge, position) must not imply higher class than declared `decision_class`. |
| **MD-O-3** | Decision owner registers every new `decision_id` with governance before ship (DG-1 + MD-G-1). |
| **MD-O-4** | Expiration and suppression events are auditable — merchant dismissals respected within TTL. |
| **MD-O-5** | Proof owner and Decision owner are separate modules — Proof Surface must not embed class escalation logic. |

### 2.4 Current ownership map (baseline)

| Capability | Truth | Proof | Decision | Presentation | Compliance |
|------------|-------|-------|----------|--------------|------------|
| KL insight card | KL metrics | Claim evidence enricher | **Not minted** (Observation) | `merchant_knowledge_layer.js` | Partial |
| `#carts` lifecycle block | LT-C1 | Proof Surface bundle | **Partial** (copy only) | `merchant_dashboard_lazy.js` | PV-17 open |
| VIP merchant alert | VIP + lifecycle | Row context | **Suggested Action** (manual path) | VIP dashboard | Executable |
| Archive / reopen | Lifecycle archive | — | **Suggested Action** (partial UX) | `#carts` | Partial |
| Daily Brief | Composite | Composite | **Not implemented** | **Future** | PV-18 open |

---

## Section 3 — Decision Pipeline Governance

Decision Governance applies **after** Proof stage succeeds and **before** Merchant Action is offered.

### 3.1 Stage gate rules

| Gate | Requirement | Blocked when |
|------|-------------|--------------|
| **G-Proof** | Valid proof bundle with `proof_source` + confidence | Missing trace (PV-7) |
| **G-Evidence** | ≥1 registry `evidence_id` per foundation §4 | Unnormalized or merged evidence |
| **G-Class** | Declared class meets minimum proof + confidence (§4) | Class inflation |
| **G-Attention** | Passes attention gates (§5) | Budget exceeded; duplicate merge_key |
| **G-Commercial** | Primary `commercial_goal` declared (§7) | No business purpose |
| **G-Action** | Suggested/Critical has eligible action or downgrade (DG-9) | Fake CTA |
| **G-Contract** | Full MD contract (§6) present | Any required field missing |

### 3.2 Pipeline contracts

| ID | Contract |
|----|----------|
| **MD-P-1** | Skipping Proof stage to reach Decision is a **P1** governance defect. |
| **MD-P-2** | Merchant Action surfaces may not appear without passing Decision stage (except raw navigation unrelated to attention). |
| **MD-P-3** | If proof confidence downgrades, decision class must downgrade or suppress automatically (MD-P-4). |
| **MD-P-4** | Stale decisions re-evaluate on proof refresh — frozen optimistic decisions forbidden. |

---

## Section 4 — Decision Class Governance

Permanent classes from foundation §4 — **governance adds enforceable minimums and presentation rules**.

```
Observation → Needs Attention → Suggested Action → Critical Action
```

### 4.1 Class governance matrix

| Class | Min proof | Min confidence | Merchant expectation | Allowed presentation | Commercial objective |
|-------|-----------|----------------|---------------------|----------------------|----------------------|
| **Observation** | 1 registry evidence + proof_source | Any (labelled) | «Good to know» | KL card, footnote, report section — **no** urgency chrome | Inform (understanding) |
| **Needs Attention** | Tier 0–2 proof bundle | **Medium** | «I should be aware» | Home highlight, cart row banner — **no** imperative verb | Awareness before loss |
| **Suggested Action** | Full proof + **eligible action** | **Medium**; **High** if revenue impact | «CartFlow suggests I do X» | CTA button, brief action line | recover_revenue, reduce_hesitation, improve_conversion, reduce_workload |
| **Critical Action** | Tier 0 block evidence | **High** only | «I must act or dismiss consciously» | Alert, notification, brief top slot | recover_revenue, improve_operations |

### 4.2 Class escalation governance

| Rule | Enforcement |
|------|-------------|
| **MD-C-1** | Class is **declared in payload** — never inferred from CSS |
| **MD-C-2** | Confidence downgrade demotes class one level (foundation CL-2) |
| **MD-C-3** | Missing eligible action caps at **Needs Attention** (MD-G-9) |
| **MD-C-4** | Same `merge_key` → single decision, highest class, combined evidence list |
| **MD-C-5** | Critical Action requires `verification_method` + governance review on first ship |

### 4.3 Presentation allowances by class

| Presentation element | Observation | Needs Attention | Suggested Action | Critical Action |
|------------------------|:-----------:|:---------------:|:----------------:|:---------------:|
| Confidence label | Required | Required | Required | Required |
| Evidence source (المصدر) | Required | Required | Required | Required |
| «Why now» line | Optional | Required | Required | Required |
| «If omitted» line | Optional | Required | Required | Required |
| Primary CTA | **Forbidden** | Optional (info link) | Required if eligible | Required |
| Push notification | **Forbidden** | **Forbidden** | Optional | Allowed (default Critical only) |
| Daily Brief slot | Optional | Allowed | Allowed | Priority |

---

## Section 5 — Attention Governance

Merchant attention is a **protected architectural resource**. Every surfaced decision must answer:

| Question | Governance requirement |
|----------|------------------------|
| **Why is this shown?** | Material `commercial_goal` + class justification — not data availability alone |
| **Why today?** | Temporal trigger documented (`decision_trigger`: event, threshold, deadline, block) |
| **Why now?** | Delay hurts outcome or risk increases — stated in `why_now_ar` or equivalent |
| **What happens if hidden?** | Honest `if_omitted_ar` — automation continues, revenue at risk, or no impact |
| **Can it wait?** | If yes → downgrade class or defer surface (home → report) |
| **Should multiple decisions merge?** | Same subject `merge_key` → one decision (MD-C-4) |
| **When must CartFlow remain silent?** | §5.2 |
| **When should a decision disappear?** | Expiration rule fires: resolved, dismissed, snoozed, proof stale, class demoted to withhold |

### 5.1 Attention budgets (permanent)

| Surface | Max decision slots | Allowed classes | Notes |
|---------|-------------------|-----------------|-------|
| **Daily Brief** | **3–5** (PV-18) | Needs Attention → Critical | One decision per item |
| **Merchant Home hero** | **1–2** | Needs Attention → Critical | Observations unlimited in feed |
| **Cart row** | **0–1** | Suggested → Critical | Observation via proof block only |
| **Push notification** | **1 per event** | Critical default | Merchant opt-in future |
| **Email / mobile summary** | **≤ Daily Brief** | Same as brief | Digest — no duplicate alerts |

### 5.2 Mandatory silence conditions

CartFlow **must not surface** a decision when:

| Condition | Principle |
|-----------|-----------|
| MD contract incomplete | DG-1, MD-G-1 |
| `confidence=insufficient` for claimed class | DG-4 |
| Automation handles safely (`merchant_needed=false`) | DG-6 |
| Duplicate `merge_key` already surfaced higher | MD-C-4 |
| No eligible action for Suggested/Critical | DG-9, PV-17 |
| Merchant dismissed within TTL | MD-O-4 |
| Brief/home budget full — lower priority loses | DG-6 |
| Observation mislabeled as decision | DG-2 |

**MD-A-1:** Silence is a **valid governance outcome** — log internally, do not backfill with weak decisions.

### 5.3 Attention contracts

| ID | Contract |
|----|----------|
| **MD-A-1** | Every surfaced decision passes all §5 gate questions or is suppressed. |
| **MD-A-2** | Daily Brief never exceeds 5 items; each item one `decision_id` (PV-18). |
| **MD-A-3** | Notifications require Critical class or explicit merchant opt-in for lower classes. |
| **MD-A-4** | Dismissed decisions respect snooze TTL before re-surface. |

---

## Section 6 — Decision Governance Contracts

Every future decision **must declare** all required fields. No field → decision does not exist (MD-G-1).

### 6.1 Required contract fields

| Field | Type | Governance rule |
|-------|------|-----------------|
| **decision_id** | string | Stable, registered, unique per logical decision |
| **decision_class** | enum | `observation` \| `needs_attention` \| `suggested_action` \| `critical_action` |
| **evidence_ids** | string[] | Normalized registry IDs — atomic, no «or» labels |
| **proof_source** | string | Trace key (PV-7): `recovery_key`, `insight_key`, lifecycle id, etc. |
| **confidence** | enum | `high` \| `medium` \| `low` \| `insufficient` — weakest-link |
| **commercial_goal** | enum | §7 — exactly one primary |
| **merchant_action** | enum | `execute` \| `wait` \| `dismiss` \| `monitor` \| `none` |
| **expiration_rule** | object | TTL, resolve-on-event, dismiss/snooze behavior |
| **verification_method** | string | Audit path: test name, truth query, manual review |

### 6.2 Recommended fields

| Field | Purpose |
|-------|---------|
| `merge_key` | Attention deduplication |
| `decision_trigger` | Why today / why now |
| `why_now_ar`, `if_omitted_ar`, `decision_rationale_ar` | Explainability (DG-7) |
| `recommended_action_id` | Link to action matrix |
| `owner_module` | Accountability |
| `proof_domain` | Primary Proof of Value domain (Decision, Recovery, …) |

### 6.3 Governed contracts (testable)

**Risk class (decision defects):**

| Class | Meaning | Example |
|-------|---------|---------|
| **D0** | Critical false urgency / harmful action | Critical alert on insufficient evidence |
| **D1** | Material attention misuse | Daily Brief item without commercial goal |
| **D2** | Decision anxiety without closure | Intervention CTA with no path (PV-17) |
| **D3** | Integrity drift | Duplicate decisions same subject |

| ID | Contract (testable) | Owner | Verification | Merchant impact | Risk |
|----|---------------------|-------|--------------|-------------------|------|
| **MD-1** | Every decision payload includes all §6.1 required fields | Decision owner | Schema gate / unit test on mint | Trust in priorities | D1 |
| **MD-2** | `decision_class` matches evidence + confidence minimums (§4.1) | Decision owner | Class vs confidence negative tests | False urgency | D0 |
| **MD-3** | `evidence_ids` ⊆ active Merchant Evidence Registry entries | Decision + registry | Registry lookup test | Wrong source label | D1 |
| **MD-4** | `proof_source` reconstructs proof bundle | Proof + decision | Trace audit sample | Unexplainable advice | D2 |
| **MD-5** | Suggested/Critical → eligible action or class capped at Needs Attention | Decision owner | Action matrix join (PV-17) | Helpless CTAs | D2 |
| **MD-6** | `confidence=insufficient` → class ≤ Observation; no imperative copy | Decision + presentation | Copy audit | Harmful pressure | D0 |
| **MD-7** | Daily Brief ≤5 items; each passes MD-1 (PV-18) | Brief owner | Brief validator | Brief habit | D1 |
| **MD-8** | `commercial_goal` present and from §7 enum | Decision owner | Enum gate | Purposeless noise | D1 |
| **MD-9** | Expiration fires on resolve/dismiss/stale proof | Lifecycle owner | TTL integration test | Stale alerts | D2 |
| **MD-10** | Presentation does not mint decisions (MD-O-1) | Presentation owners | Static analysis / code review | Hidden logic drift | D3 |
| **MD-11** | Same `merge_key` → at most one surfaced decision per surface | Attention allocator | Dedup test | Attention spam | D2 |
| **MD-12** | Critical Action requires `confidence=high` + Tier 0 block proof | Decision owner | Evidence tier check | Crying wolf | D0 |

### 6.4 Contract traceability (audit → contract)

| Merchant Value Audit finding | Contracts | Current compliance |
|------------------------------|-----------|-------------------|
| Decision confidence C− | MD-2, MD-6 | **Open** |
| Intervention without action | MD-5, PV-17 | **Open** |
| No daily brief | MD-7, PV-18 | **Open** |
| KL cards without decision contract | MD-1 (by design — Observation) | **Compliant** as Observation |
| Proof Surface without decision mint | MD-O-5 | **Compliant** — proof only |

---

## Section 7 — Commercial Governance

**No commercial purpose → no decision** (DG-8).

### 7.1 Primary commercial goals (closed enum)

| Goal | Merchant question | Typical class |
|------|-------------------|---------------|
| **recover_revenue** | Will this protect or recover sales? | Suggested → Critical |
| **reduce_hesitation** | Will this reduce checkout friction? | Observation → Suggested |
| **improve_conversion** | Will this improve cart-to-purchase? | Needs Attention → Suggested |
| **improve_operations** | Will this fix store/platform ops? | Suggested → Critical |
| **reduce_workload** | Will this save merchant time? | Observation (wait/monitor decisions) |
| **increase_confidence** | Will this improve trust in CartFlow? | Needs Attention |

**MD-G-8:** Secondary goals optional in metadata — ranking uses **primary** only.

**MD-G-9:** High commercial potential **never** overrides DG-4, DG-9, or MD-2.

### 7.2 Commercial integrity alignment

Decision governance **implements** Proof of Value commercial integrity (CI-1…CI-10) at the decision layer:

| CI rule | Decision governance enforcement |
|---------|--------------------------------|
| No fake urgency for growth | DG-5, MD-2, MD-12 |
| No action without path | DG-9, MD-5 |
| Unknown stays unknown | DG-4, MD-6 |
| Tier claims match proof | Decisions must not upsell tier capabilities as Critical |

---

## Section 8 — Integration (no duplicated governance)

This domain **extends** — does not replace — existing governance.

| Layer | Document | Decision governance relationship |
|-------|----------|----------------------------------|
| Engineering truth | `engineering_constitution_v1.md` | Decisions read truth — never mint |
| Merchant value | `cartflow_value_validation_foundation_v1.md` | Value domains inform `commercial_goal` |
| Proof foundation | `proof_of_value_foundation_v1.md` | PV-4/17/18 are proof-stage inputs to MD-5/7 |
| Proof governance | `proof_of_value_governance_v1.md` | PG-2/3/5 gate decision inputs; §2.4 Decision Proof presentation map |
| Decision foundation | `merchant_decision_foundation_v1.md` | **Concepts** — classes, vocabulary, foundation contract |
| Evidence registry | `merchant_evidence_registry_v1.py` | `evidence_ids` must resolve here |
| Claim evidence | `merchant_claim_evidence_v1.py` | KL observations supply evidence — not decisions |
| Proof Surface | `merchant_proof_surface_v1.py` | Proof bundle input — MD-O-5 separation |
| Cart decision design | `merchant_decision_layer_v1.md` | Per-cart implementation of this governance |

**Integration rules:**

| ID | Rule |
|----|------|
| **MD-I-1** | Do not duplicate PV contracts — reference PV-17/18 and add decision-stage MD-* obligations. |
| **MD-I-2** | Do not duplicate Evidence Registry entries — reference `evidence_id` only. |
| **MD-I-3** | Foundation defines **what**; this document defines **enforceable how**. |
| **MD-I-4** | Future Decision Engine is the single decision minter — presentation consumers only. |

---

## Section 9 — Future consumers (mandatory compliance)

| Consumer | Governance obligations |
|----------|------------------------|
| **Daily Brief** | MD-7, MD-A-2, PV-18, §5 budget |
| **Merchant Home** | MD-A-2 hero limits, Observation vs decision separation |
| **Merchant Understanding** | Observation default; decisions need behavior evidence maturity |
| **Product Intelligence** | PV-16 + MD-3 before product-linked decisions |
| **Decision Engine** | MD-1…12 minter; MD-O-* ownership |
| **Notifications** | MD-A-3, Critical default |
| **Email summaries** | ≤ brief budget; no duplicate merge_key |
| **Mobile summaries** | Same as brief |
| **Future AI** | Tier 3 — narrates decisions; **must not mint** (MD-O-1, PG-4) |

---

## Section 10 — Maturity, enforcement, and evolution

### 10.1 Domain maturity

| Level | Meaning |
|-------|---------|
| **L0** | Ad hoc attention in UI |
| **L1 Working** | Observations + partial decision copy (today) |
| **L2 Governed** | Decision Engine mints MD contract; release gate on MD-1…12 |
| **L3 Proven** | Attention metrics + merchant dismiss feedback loop |
| **L4+** | Optimized ranking within governance bounds |

**Target:** Decision domain **L2 Governed** when Decision Engine ships with CI gate.

### 10.2 Future enforcement candidates (not shipped)

| Gate | Contract set |
|------|--------------|
| Decision schema validator on API responses | MD-1, MD-3 |
| Brief slot linter | MD-7, MD-A-2 |
| Presentation static analysis — no class in JS | MD-10, MD-O-1 |
| Action matrix join test | MD-5 |

### 10.3 Evolution

| Change | Process |
|--------|---------|
| New decision class | Foundation + governance amendment |
| New commercial goal | §7 enum extension + commercial review |
| Weaken silence rules | **Forbidden** without trust review |
| New consumer surface | Register attention budget in §5.1 |

---

## Section 11 — Governance validation checklist

| Requirement | Status |
|-------------|--------|
| Decision stage owned separately from Proof | **Defined** (§0, §3) |
| DG principles (10) | **Defined** (§1) |
| Six ownership dimensions | **Defined** (§2) |
| Four governed classes | **Defined** (§4) |
| Attention gates + silence | **Defined** (§5) |
| Mandatory decision contract | **Defined** (§6) |
| Commercial goal required | **Defined** (§7) |
| Integration without duplication | **Defined** (§8) |
| Future consumer mandate | **Defined** (§9) |
| Implementation | **Future** |

---

*End of Merchant Decision Governance V1.*
