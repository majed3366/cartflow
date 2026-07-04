# CartFlow Merchant Decision Foundation V1

**Status:** Ratified baseline — permanent decision architecture for Merchant Value  
**Date (UTC):** 2026-07-04  
**Scope:** Defines **what qualifies as a merchant decision**, **how attention is governed**, and **how decisions connect to proof and action** — not how decisions are scored, ranked, or rendered  
**Authority:** This document is the **decision counterpart** to [`proof_of_value_foundation_v1.md`](proof_of_value_foundation_v1.md) and [`merchant_evidence_registry_foundation_v1.md`](merchant_evidence_registry_foundation_v1.md). Future Daily Brief, Decision Engine, notifications, and recommendations **must implement** this foundation — not invent decision behavior.  
**Audience:** Product, engineering, commercial, and operations — anyone who surfaces merchant-facing priorities or actions  

**Explicitly out of scope:** Implementation, scoring engines, AI, prioritization algorithms, UI, recommendations, Daily Brief product code.

**Canonical inputs:**

| Document | Role |
|----------|------|
| [`proof_of_value_foundation_v1.md`](proof_of_value_foundation_v1.md) | Proof domains, evidence hierarchy, PV-4/17/18 decision contracts |
| [`proof_of_value_governance_v1.md`](proof_of_value_governance_v1.md) | PG principles, proof lifecycle, commercial integrity |
| [`merchant_evidence_registry_foundation_v1.md`](merchant_evidence_registry_foundation_v1.md) | Governed evidence labels per claim |
| [`claim_level_evidence_ownership_v1.md`](claim_level_evidence_ownership_v1.md) | Each claim owns evidence + confidence |
| [`merchant_decision_layer_v1.md`](merchant_decision_layer_v1.md) | Cart-state decision design (future implementation of this foundation per cart) |
| [`cartflow_value_validation_foundation_v1.md`](cartflow_value_validation_foundation_v1.md) | Daily Brief contract (3–5 items; what/why/action) |

---

## Executive summary

CartFlow must never surface information simply because it exists.

**Merchant attention is a governed resource.** Every surfaced insight must justify why it deserves the merchant's attention — with evidence, confidence, and commercial purpose — before any recommendation or action is offered.

This foundation establishes the permanent architecture between **Proof of Value** (what CartFlow may claim) and **Merchant Action** (what the merchant may do). It does not implement recommendations, AI, or Daily Brief. It defines the contract those features must follow.

---

## Section 1 — Core principle chain

No stage may skip the previous one.

```
Truth
  ↓
Evidence
  ↓
Proof
  ↓
Decision
  ↓
Merchant Action
  ↓
Business Outcome
```

| Stage | Question answered | Owner layer (today) |
|-------|-------------------|---------------------|
| **Truth** | What happened in the store? | Purchase / Lifecycle / Recovery / Provider / Widget Truth |
| **Evidence** | What raw facts support a claim? | Tier-0–2 sources per Proof of Value §3 |
| **Proof** | What may CartFlow show the merchant? | Proof Surface, KL, Evidence Registry (presentation) |
| **Decision** | Does this deserve merchant attention now? | **This foundation** — future Decision Engine implements |
| **Merchant Action** | What can the merchant do? | Eligible action matrix (PV-17); cart/archive/VIP paths |
| **Business Outcome** | Why does this matter commercially? | Value domains (recovery, conversion, workload, confidence) |

**Rule MD-1:** A merchant-visible **decision** may not exist without upstream **proof** composed from governed **evidence** rooted in owned **truth**.

**Rule MD-2:** A **recommendation** or **action prompt** may not exist without a declared **decision** that passes this foundation's contract (§5).

---

## Section 2 — Permanent vocabulary

These terms are **permanently separate**. Mixing them creates weak advice and erodes trust.

### 2.1 Observation

| Field | Definition |
|-------|------------|
| **What it is** | A factual statement about store state, pattern, or event — without telling the merchant what to do |
| **Requires** | Evidence + confidence + proof source |
| **Does not require** | Recommended action, urgency, or attention ranking |
| **Example** | «سبب التردد الأبرز هذا الأسبوع: السعر» (KL insight with `hesitation_reason` evidence) |
| **Merchant expectation** | «CartFlow noticed something — I can learn from it» |
| **Not** | A decision, recommendation, or alert |

### 2.2 Decision

| Field | Definition |
|-------|------------|
| **What it is** | A governed judgment that **something deserves merchant attention** — with stated reason, confidence, and commercial purpose |
| **Requires** | Full decision contract (§5); attention justification (§6) |
| **May include** | Observation text, but must add **why now** and **what if omitted** |
| **Example** | «سلة VIP بقيمة ٤٥٠٠ ر.س تحتاج جوالك قبل أن يتابع النظام — بدون رقم لن يُرسل استرجاع» |
| **Merchant expectation** | «CartFlow is telling me this matters — I understand the stakes» |
| **Not** | Raw data, a chart, or an unexplained alert |

### 2.3 Recommendation

| Field | Definition |
|-------|------------|
| **What it is** | A **suggested response** to a decision — one primary path CartFlow believes is appropriate |
| **Requires** | Parent decision + eligible action (PV-17) + confidence ≥ class minimum (§4) |
| **Must declare** | What to do, why this suggestion, what happens if ignored |
| **Example** | «أضف رقم الجوال من لوحة السلال» (only if action is executable in-product) |
| **Merchant expectation** | «CartFlow suggests a specific next step I can take» |
| **Not** | Generic advice («حسّن تجربة العميل») without eligible action |

### 2.4 Action

| Field | Definition |
|-------|------------|
| **What it is** | An **executable merchant operation** tied to a recommendation or explicit inaction choice |
| **Requires** | Documented eligibility path; UI/API affordance or honest external path |
| **Types** | **Execute** (archive, reopen, VIP alert, save phone, fix settings) · **Wait** (automation continues) · **Dismiss** (archive / acknowledge) · **Monitor** (no button — awareness only) |
| **Example** | `POST /api/dashboard/vip-cart/{id}/merchant-alert` |
| **Merchant expectation** | «I can do this now — or CartFlow honestly says I cannot yet» |
| **Not** | A label without a path; a button that does nothing |

### 2.5 Relationship diagram

```
Observation ──(may inform)──► Decision ──(may produce)──► Recommendation ──(must map to)──► Action
                                    │
                                    └── may conclude: «No action needed» (valid decision)
                                    └── may conclude: «Remain silent» (valid outcome)
```

---

## Section 3 — Decision philosophy

Permanent principles. Ordered — earlier principles constrain later ones.

### 3.1 Decision Before Presentation

Attention, ranking, badges, and brief slots are **decision outputs** — not layout choices. Presentation composes decisions; it does not create them.

*Aligns with:* Proof of Value PG-3 (Presentation composes proof); Evidence Registry (labels from registry only).

### 3.2 Evidence Before Decision

No decision without identifiable evidence sources and minimum confidence for its class (§4). Patterns, heuristics, and AI summaries are inputs — not substitutes for evidence.

*Aligns with:* PG-2 Evidence Before Confidence; Merchant Evidence Registry normalization.

### 3.3 Unknown Must Not Produce Action

When confidence is **insufficient** or evidence is **unknown**, CartFlow may show observation with uncertainty — but **must not** recommend action that implies certainty.

*Aligns with:* PV-5; PG-5 Unknown Remains Unknown.

### 3.4 Low Confidence Requires Caution

**Low** or **medium** confidence decisions downgrade class automatically: Suggested Action becomes Needs Attention; Critical Action is forbidden until evidence supports it.

### 3.5 Silence Is Better Than Weak Advice

If a decision cannot meet its class contract, CartFlow **withholds** it. Empty Daily Brief beats misleading priority.

*Aligns with:* Proof of Value §1.5 Merchant Trust Before Growth.

### 3.6 Merchant Attention Is Limited

CartFlow assumes the merchant has **finite daily attention**. Surfaces compete for the same resource — home, brief, notifications, cart rows.

*Implied limit:* Daily Brief max **3–5** items (Value Validation §5); notification budget TBD by future governance.

### 3.7 Explain Every Decision

Every decision must answer: **what**, **why it matters**, **why now**, **evidence**, **confidence**, **what if I do nothing**.

*Aligns with:* PV-7 proof source traceability; claim-level evidence ownership.

### 3.8 Every Decision Must Be Actionable

A decision without a valid outcome path — execute, wait, dismiss, or monitor — is **not a decision**. It is an observation mislabeled.

*Aligns with:* Decision Proof domain §2.3; eligible inaction is valid when automation consequence is stated.

### 3.9 No Recommendation Without Eligible Action

Recommendations that cannot be executed (in-product or via documented honest path) **downgrade to informational observation only** (PV-17).

*Audit baseline:* Normal-carts executable actions **gap** — foundation forbids pretending otherwise.

---

## Section 4 — Decision classification

Four permanent classes. **Higher classes require stricter evidence and confidence.**

```
Observation
    ↓
Needs Attention
    ↓
Suggested Action
    ↓
Critical Action
```

### 4.1 Class summary

| Class | Purpose | Min confidence | Min evidence | Merchant expectation |
|-------|---------|----------------|--------------|-------------------|
| **Observation** | Inform without demanding attention | Any (labelled) | ≥1 registry evidence source | «Good to know» |
| **Needs Attention** | Merchant should be aware; may not act today | **Medium** | ≥1 Tier-0–2 source + proof bundle | «Keep an eye on this» |
| **Suggested Action** | Merchant should consider acting | **Medium–High** | Proof + eligible action path | «CartFlow suggests I do X» |
| **Critical Action** | Merchant must act or accept explicit loss | **High** | Tier-0 truth + blocked automation or high-value risk | «I need to act or dismiss consciously» |

### 4.2 Observation

| Field | Requirement |
|-------|-------------|
| **Purpose** | Surface pattern, metric, or state change without priority claim |
| **Confidence** | Must be labelled; **insufficient** → show coverage caveat only |
| **Minimum evidence** | One normalized `evidence_id` from Merchant Evidence Registry |
| **Merchant expectation** | No urgency implied; no action button required |
| **Silence rule** | Omit if duplicate of higher-class decision for same subject |
| **Examples today** | KL insight cards (Understanding); weekly reason distribution |

### 4.3 Needs Attention

| Field | Requirement |
|-------|-------------|
| **Purpose** | Flag material state the merchant should track |
| **Confidence** | **Medium** minimum; **Low** forbidden |
| **Minimum evidence** | Lifecycle or recovery proof + `proof_source` |
| **Merchant expectation** | Awareness + stated consequence if ignored |
| **Silence rule** | Suppress if automation handles safely and merchant_needed = false |
| **Examples today** | VIP cart banner; lifecycle «تدخل التاجر: نعم» (partial — action gap) |

### 4.4 Suggested Action

| Field | Requirement |
|-------|-------------|
| **Purpose** | Recommend one primary merchant response |
| **Confidence** | **Medium** minimum; **High** for revenue-impacting suggestions |
| **Minimum evidence** | Full proof chain + **eligible action** registered |
| **Merchant expectation** | Clear CTA or honest «path not yet in product» downgrade |
| **Silence rule** | No suggestion without eligible action (PV-17) |
| **Examples today** | VIP merchant alert (executable); archive/reopen (partial UX) |

### 4.5 Critical Action

| Field | Requirement |
|-------|-------------|
| **Purpose** | Blocked automation, channel failure, or high-value loss requiring immediate merchant choice |
| **Confidence** | **High** only — Tier-0 truth required |
| **Minimum evidence** | Provider / lifecycle / recovery truth showing hard block |
| **Merchant expectation** | Act, fix, contact manually, or explicitly dismiss |
| **Silence rule** | Never inflate urgency; never use for marketing |
| **Examples today** | Send failure on active recovery (design in `merchant_decision_layer_v1.md`); not fully surfaced as Critical class yet |

### 4.6 Class escalation rules

| Rule | Meaning |
|------|---------|
| **CL-1** | Class is **declared**, not inferred from UI styling |
| **CL-2** | Confidence downgrade **demotes** class one level |
| **CL-3** | Missing eligible action **caps** class at Needs Attention |
| **CL-4** | Two decisions on same subject **merge** to highest class with combined evidence |
| **CL-5** | Critical Action requires **explicit verification method** in contract |

---

## Section 5 — Decision contract

Every future merchant decision **must declare** all fields. No field → no decision.

| Field | Required | Definition |
|-------|----------|------------|
| **Decision ID** | Yes | Stable identifier (e.g. `decision_vip_missing_phone`, `decision_recovery_send_blocked`) |
| **Decision Type** | Yes | One of §4 classes |
| **Evidence Sources** | Yes | List of registry `evidence_id` values (normalized, atomic) |
| **Confidence** | Yes | `high` \| `medium` \| `low` \| `insufficient` — weakest-link across sources |
| **Required Action** | Yes | `execute` \| `wait` \| `dismiss` \| `monitor` \| `none` (explicit acceptable inaction) |
| **Business Goal** | Yes | One primary commercial goal (§7) |
| **Owner** | Yes | Module or surface that mints the decision (governance accountability) |
| **Verification Method** | Yes | How to audit the decision was correct (test, truth query, manual review) |

### 5.1 Optional but recommended fields

| Field | Purpose |
|-------|---------|
| `decision_title_ar` | Merchant headline |
| `decision_rationale_ar` | Why this decision exists |
| `why_now_ar` | Temporal justification |
| `if_omitted_ar` | Consequence of merchant ignoring |
| `recommended_action_id` | Link to eligible action registry (future) |
| `proof_source` | Trace key (recovery_key, insight_key, lifecycle state) |
| `expires_at` | When decision should be re-evaluated or auto-silenced |
| `merge_key` | Dedup key for attention model (§6) |

### 5.2 JSON contract sketch (future implementation)

```json
{
  "decision_id": "decision_vip_missing_phone",
  "decision_type": "suggested_action",
  "decision_class": "suggested_action",
  "evidence_sources": ["store_activity", "hesitation_reason"],
  "confidence": "high",
  "required_action": "execute",
  "business_goal": "recover_revenue",
  "owner": "merchant_decision_engine_v1",
  "verification_method": "lifecycle_truth_query + vip_threshold_check",
  "proof_source": "recovery_key:store:123:session:abc",
  "why_now_ar": "سلة VIP تجاوزت العتبة قبل ٢ ساعة",
  "if_omitted_ar": "لن يبدأ الاسترجاع الآلي بدون رقم جوال"
}
```

---

## Section 6 — Merchant attention model

CartFlow protects merchant attention as a **scarce governed resource**.

### 6.1 Attention gate questions

Every decision must pass all gates before surfacing:

| Question | Pass criterion |
|----------|----------------|
| **Why should this appear?** | Material impact on business goal (§7) — not mere data availability |
| **Why today?** | Temporal trigger: new event, threshold crossed, deadline, automation blocked |
| **Why now?** | Delaying reduces outcome or increases risk — stated explicitly |
| **What happens if omitted?** | Honest consequence: revenue at risk, automation continues, or no impact |
| **Can two decisions be merged?** | Same `merge_key` / subject → one decision, highest class |
| **Can this wait until tomorrow?** | If yes → downgrade class or defer to non-intrusive surface |
| **When should CartFlow remain silent?** | See §6.2 |

### 6.2 Silence rules (permanent)

CartFlow **remains silent** when:

| Condition | Rationale |
|-----------|-----------|
| Confidence is **insufficient** for claimed class | Unknown Must Not Produce Action |
| Automation handles case safely (`merchant_needed = false`) | Merchant Attention Is Limited |
| Duplicate of existing decision on same subject | Attention deduplication |
| No eligible action and class would be Suggested/Critical | PV-17 downgrade — silence preferred over fake CTA |
| Merchant dismissed / snoozed decision within TTL | Respect explicit dismissal |
| Daily Brief budget full (3–5) and lower priority | Rank by class + commercial weight |
| Observation-only insight with no decision justification | KL cards stay Observation unless decision contract met |

### 6.3 Attention surfaces (future consumers)

| Surface | Attention budget | Primary class range |
|---------|------------------|---------------------|
| **Daily Brief** | 3–5 decisions max | Needs Attention → Critical Action |
| **Merchant Home** | 1–2 hero decisions + observations | Mixed |
| **Cart row** | 0–1 decision per row | Suggested → Critical |
| **Notifications** | Strict; Critical only by default | Critical Action |
| **KL cards** | Observations default | Observation |
| **Admin insights** | Internal; not merchant attention | N/A |

---

## Section 7 — Commercial alignment

**No decision may exist without commercial purpose.**

Every decision declares one **primary business goal**:

| Business goal | Merchant question | Example decision |
|---------------|-------------------|------------------|
| **recover_revenue** | Will this help get money back? | VIP phone missing; send blocked |
| **reduce_hesitation** | Will this reduce checkout friction? | Top hesitation reason spike |
| **improve_conversion** | Will this improve cart-to-purchase? | High-intent return without purchase |
| **reduce_workload** | Will this save merchant time? | «Automation handling — no action needed» |
| **increase_confidence** | Will this improve trust in CartFlow data? | Setup incomplete blocking proof |
| **improve_operations** | Will this fix platform/store operations? | WhatsApp channel disconnected |

**Rule MD-3:** Secondary goals allowed in metadata — one **primary** goal required for ranking and brief slots.

**Rule MD-4:** Commercial goals **never override** proof rules. A high revenue potential does not justify Critical Action without High confidence evidence.

*Aligns with:* Proof of Value Commercial Proof domain; CI-1…CI-10 commercial integrity.

---

## Section 8 — Future consumers

This foundation is designed so these features **implement the contract** without architectural redesign:

| Consumer | Uses foundation for |
|----------|---------------------|
| **Daily Brief** | Class filter, attention budget, 3–5 decision slots, PV-18 |
| **Merchant Home** | Hero decisions + observation feed separation |
| **Product Intelligence** | Observation → Needs Attention when product truth matures |
| **Merchant Understanding** | Behavior-backed decisions with `behavior_truth` evidence |
| **Decision Engine** | Mints `Decision ID` + class + contract fields |
| **Notifications** | Critical Action gate + silence rules |
| **Admin Insights** | Internal verification; not merchant attention |
| **Knowledge Layer** | Observations by default; decisions only with full contract |
| **Proof Surface** | Evidence input to decisions — not decisions themselves |

**Existing partial implementations:**

| Today | Foundation mapping |
|-------|-------------------|
| KL insight cards | **Observation** (claim-level evidence + confidence) |
| Proof Surface on `#carts` | **Evidence → Proof** input; not yet Decision class |
| VIP merchant alert | **Suggested Action** (executable) |
| Lifecycle «تدخل التاجر» | **Needs Attention → Suggested Action** (action gap) |
| `merchant_decision_layer_v1.md` | Per-cart **decision design** — implements this foundation for cart domain |

---

## Section 9 — Governance validation

| Requirement | Source | Status |
|-------------|--------|--------|
| Truth → Evidence → Proof → Decision chain | Engineering Constitution; PoV §3 | **Defined** |
| Decision Before Presentation | PG-3 | **Defined** |
| Evidence Before Decision | PG-2; Evidence Registry | **Defined** |
| Unknown Must Not Produce Action | PV-5; PG-5 | **Defined** |
| No recommendation without eligible action | PV-17 | **Defined** |
| Daily Brief contract | PV-18; Value Validation §5 | **Referenced** |
| Claim-level evidence ownership | Claim-Level Evidence V1 | **Shipped** (observation layer) |
| Registry semantic atomicity | Registry Normalization V1 | **Shipped** |
| Decision Engine implementation | — | **Future** |
| Scoring / prioritization algorithm | — | **Out of scope** |

---

## Section 10 — Evolution

| Change type | Process |
|-------------|---------|
| New decision class | Foundation amendment + governance review |
| New business goal | Add to §7 with commercial justification |
| New consumer surface | Must declare attention budget in §6.3 |
| Weakening silence rules | **Forbidden** without explicit merchant-trust review |

**Maturity target:** Decision architecture **Level 2 Governed** when Decision Engine mints contract-compliant decisions with CI release gate. Current baseline: **Level 0–1 Working** (observations shipped; decisions partial).

---

## Section 11 — Related documents

| Document | Relationship |
|----------|--------------|
| [`merchant_decision_layer_v1.md`](merchant_decision_layer_v1.md) | Cart-state **implementation design** — subordinate to this foundation |
| [`merchant_decision_layer_v1a_implementation_design.md`](merchant_decision_layer_v1a_implementation_design.md) | Technical design — future code |
| [`proof_surface_implementation_v1.md`](proof_surface_implementation_v1.md) | Proof layer — feeds decisions, does not replace them |
| [`merchant_action_matrix_v1.md`](cartflow_merchant_action_matrix_v1.md) | Eligible actions inventory (if present) |

---

*End of Merchant Decision Foundation V1.*
