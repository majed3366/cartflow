# Cart Workspace Constitution V2

**Status:** RATIFIED — Cart Workspace Governance Pack  
**Date (UTC):** 2026-07-12  
**Authority:** Highest governing reference for Cart Workspace (merchant decision surface)  
**Ratification:** [`cart_workspace_ratification_v1.md`](cart_workspace_ratification_v1.md) — **Verdict A**  
**Governance Pack peers:** [`cart_workspace_constitutional_decisions_log_v1.md`](cart_workspace_constitutional_decisions_log_v1.md), [`cart_workspace_glossary_v1.md`](cart_workspace_glossary_v1.md)  
**Supersedes:** Cart Workspace Constitution V1.0 (Draft)  
**Related (subordinate or peer):**  
[`cart_page_product_constitution.md`](cart_page_product_constitution.md) *(subordinate on Workspace conflicts — Ratification Q3)*,  
[`merchant_decision_governance_v1.md`](../merchant_decision_governance_v1.md),  
[`merchant_decision_foundation_v1.md`](../merchant_decision_foundation_v1.md),  
[`engineering_constitution_v1.md`](../engineering_constitution_v1.md)

**Explicitly out of scope of this document:** UI design, implementation, Decision Admission Matrix detail, ownership map tables, architecture blueprints.

---

# Part A — Constitution

## 0. Authority and precedence

1. This Constitution governs **Cart Workspace** — the merchant-facing surface whose sole job is to request human judgment when automation can no longer produce the best recovery outcome.
2. Platform truth, evidence, proof, and engineering ownership remain governed by Engineering Constitution, Lifecycle Truth (LT-C1), Purchase Truth, and Merchant Decision Governance. This Constitution **does not mint truth** and **does not override** those authorities.
3. Downstream work (Merchant Decision & Ownership Map, Decision Admission Matrix, UX Blueprint, Architecture, Implementation) **derives from** this Constitution and the Governance Pack. They may not redefine it.
4. On Cart Workspace product-identity conflicts with the Cart Page Product Constitution, **this Constitution prevails** (Ratification Q3).

---

## 1. Purpose

### 1.1 Mission

Cart Workspace exists to **protect merchant attention** while **maximizing recovered revenue**.

It does not exist to display carts.  
It does not exist to expose internal system activity.  
It exists to present **only the human decisions** expected to create measurable business value.

### 1.2 Definition

Cart Workspace is the operational surface through which CartFlow asks the merchant for **human judgment** only when automation can no longer create the best outcome.

### 1.3 Singular identity

Cart Workspace is a **Decision Workspace**.

That identity is exclusive. See §9 (Boundaries).

---

## 2. Product philosophy

1. **CartFlow owns the recovery journey** (Execution Ownership — §4).
2. **The merchant owns business judgment** when Decision Admission has admitted a decision (Decision Ownership — §4).
3. The platform must continuously **maximize automation** and **minimize unnecessary human intervention**.
4. The merchant is never expected to supervise CartFlow.  
   **CartFlow supervises itself.**

---

## 3. Core mission question

The workspace exists to answer **one question only**:

**ما يحتاج قرارك؟**

Everything displayed must help answer that question.  
Nothing else belongs on this surface.

Supporting context (what happened, what CartFlow tried, why automation stopped) is allowed **only** insofar as it enables that decision (§6.6 Explain Before Asking).

---

## 4. Constitutional definitions

These definitions are binding. No informal reinterpretation.

| Term | Definition |
|------|------------|
| **Signal** | A raw operational event or measurement observed by the platform (e.g. message accepted, phone absent, timer fired). Signals are not merchant decisions and are not workspace categories. |
| **Evidence** | Normalized, owned claim material derived from signals/truth under Evidence Registry / claim-level ownership rules. Evidence supports proof; it is not a decision. |
| **Status** | An internal or system-facing lifecycle/process label describing where automation is (e.g. waiting, sent, replied). Statuses serve the platform. They are not workspace categories. |
| **Proof** | Composed, governed demonstration that evidence supports a claim at a declared confidence. Proof precedes Decision Admission. |
| **Decision** | A governed request for merchant judgment: a single business choice CartFlow cannot safely improve further under current policy. A Decision has one purpose, one explanation contract, and one primary action. |
| **Action** | The executable primary control attached to an admitted Decision (or an explicit non-action such as deliberate wait when that *is* the admitted decision). Actions without Decisions are prohibited on this surface. |
| **Escalation** | The governed transition by which Execution Ownership remains with CartFlow (or is constrained by policy) while Decision Ownership is offered or transferred to the merchant after Decision Admission. Escalation is exceptional; automation is default. |
| **Automation** | CartFlow’s autonomous execution of the recovery journey without requiring merchant attention. |
| **Human Judgment** | Merchant business judgment applied to an admitted Decision. Invited only when expected to outperform continued automation. |
| **Execution Ownership** | Who is responsible for **running** recovery work right now (scheduling, messaging, observation, lifecycle progression). Exactly one Execution Owner at all times: **CartFlow** or, under rare explicit handoff policy, **Merchant** for a scoped manual execution path. |
| **Decision Ownership** | Who is responsible for the **next business judgment** on this cart. Either **CartFlow** (no admitted Decision — merchant must not be interrupted) or **Merchant** (Decision admitted — merchant attention is requested). Never both. Never neither. |
| **Operational Owner** *(composite term)* | Informal umbrella; **not** used alone in V2 norms. Prefer Execution Ownership and Decision Ownership. |
| **Decision Owner** | Synonym of Decision Ownership holder: CartFlow or Merchant. |
| **Priority Override** | The constitutional operational layer for carts under VIP (or future equivalent override) policy. It is not “higher sort order.” It is a **different policy**: immediate notification and dedicated admission path; it does not wait behind normal Decision queues. |
| **Attention Budget** | The finite merchant attention the workspace is sworn to protect. Visibility requires expected decision value exceeding attention cost. |
| **Decision Admission** | The constitutional gate that verifies automation cannot safely improve further (under applicable policy) **before** a Decision may appear in Cart Workspace. No card without Admission. |

---

## 5. Constitutional layers

Cart Workspace participates in a fixed layer stack. Lower layers must not bypass upper gates.

```
L0  Priority Override          ← VIP / override policy (if applicable)
        ↓
L1  Decision Admission         ← may a Decision exist at all?
        ↓
L2  Merchant Workspace         ← Cart Workspace surface (this Constitution)
        ↓
L3  Operational Background     ← automation, signals, statuses (invisible by default)
        ↓
L4  Completed Outcomes         ← resolved / archived / purchased results (not active Decision surface)
```

### Layer rules

| Layer | Visible in Cart Workspace by default? | Rule |
|-------|----------------------------------------|------|
| **L0 Priority Override** | Yes, when active — via admitted Decisions / dedicated override surface policy | Override policy applies **before** normal queueing; does not skip Explain Before Asking or One Card = One Decision |
| **L1 Decision Admission** | No (gate, not UI) | Nothing reaches L2 without Admission |
| **L2 Merchant Workspace** | Yes | Only admitted Decisions (+ required explanation) |
| **L3 Operational Background** | No | Signals/statuses/automation remain invisible unless promoted through Admission into a Decision explanation |
| **L4 Completed Outcomes** | Separate from active Decision Workspace | History/archive/success are not “what needs your decision now”; they must not pollute L2 |

**Quiet by Default** applies at L2: when L1 admits nothing, L2 is calm.  
**Priority Override** does not violate Quiet: override carts are admitted under L0 policy into L1/L2; non-override silence remains mandatory.

---

## 6. Operating principles

Principles are ordered. Earlier principles constrain later ones.

### 6.1 Merchant Time First

Merchant attention is the most valuable operational resource.  
The system may consume it only when expected business value exceeds attention cost.

**Engineering norm:** Attention is finite; cognitive load must be minimized; information alone never justifies visibility.  
**UI norm:** The page requests Decisions; it does not “show activity.”  
**Acceptance:** If removing an element does not reduce decision quality, the element must not exist.

### 6.2 Automation Before Escalation

Automation is always the default Execution Owner.  
Human escalation (Decision Ownership → Merchant) is exceptional and requires Decision Admission.

**Acceptance:** No cart may reach Cart Workspace merely because a Signal or Status changed.

### 6.3 Priority Override (VIP operational layer)

VIP does **not** mean “higher priority in the same queue.”  
VIP means **Priority Override policy** (L0):

**Immediate policy effects (constitutional minimum):**

1. Notify merchant (subject to merchant notification configuration).  
2. Notify customer service **if configured**.  
3. Present through the **Priority Override admission path** (dedicated override surface or equivalently isolated override Decisions — product shape is downstream; isolation is constitutional).  
4. CartFlow **continues Execution Ownership** (observation / policy-constrained automation) unless/until Decision Ownership rules say otherwise (§7).  
5. Human Decision Ownership is eligible **immediately** under override policy — override carts **never wait** behind normal Decision queues.

**Acceptance:** VIP never waits behind normal operational Decision queues.

### 6.4 Dual ownership (Execution vs Decision)

Every cart always has:

- exactly one **Execution Owner**, and  
- exactly one **Decision Owner**.

| | CartFlow | Merchant |
|--|----------|----------|
| **Execution Ownership** | Default for recovery journey | Only under explicit scoped manual-execution policy |
| **Decision Ownership** | Default when no Decision is admitted | Only after Decision Admission |

**Forbidden:**

- Two Decision Owners at once  
- Zero Decision Owners  
- Merchant Decision Ownership without Admission  
- Workspace interruption while Decision Owner is still CartFlow  

**Ownership transitions** must be deterministic and explainable (from → to → gate that fired → timestamp/policy id). Downstream Ownership Map must implement this; it may not invent a third owner type.

### 6.5 Decision Over Status

Statuses exist for the platform.  
Decisions exist for the merchant.

Cart Workspace displays **Decisions**, not Statuses, Signals, or raw Evidence lists.

**Therefore these are not workspace categories:**

- Message Sent  
- Phone Missing  
- Customer Replied  
- Waiting *(as a status category)*  

They may appear only as **explanation material inside an admitted Decision**, never as the organizing taxonomy of the surface.

### 6.6 Explain Before Asking

Before requesting human Action, CartFlow must make available:

1. What happened (Signal→Evidence summary, merchant-safe).  
2. What CartFlow already attempted (Execution history, merchant-safe).  
3. Why automation stopped / why Admission fired.  
4. What Decision is expected.

**Acceptance:** No Action control may appear without that operational context.

### 6.7 One Card = One Decision

Every card represents exactly one business Decision: one purpose, one explanation, one primary Action.

**Acceptance:** Multi-purpose cards are prohibited.

### 6.8 Automation Confidence

If CartFlow can safely continue under current policy, the merchant must not be interrupted.

**Engineering norm:** Decision Admission must verify that automation cannot safely improve further (or override policy requires immediate Decision Ownership eligibility).

### 6.9 Attention Budget

The workspace protects attention, not information density.

**Acceptance:** Adding information or cards requires proving decision value. Workspace complexity must remain intentionally limited.

### 6.10 Operational Success

Success is measured by:

- Merchant Decisions avoided  
- Merchant attention preserved  
- Faster *correct* Decisions when invited  
- Recovery attributable to meaningful human intervention  

Not by: card count, event count, or visible widget count.

### 6.11 Quiet by Default

When Decision Admission admits nothing for the normal path, Cart Workspace is calm.

Canonical calm state (wording may be localized; meaning is fixed):

> لا يوجد ما يحتاج قرارك الآن. CartFlow يتابع عمليات الاسترداد تلقائيًا.

Silence is preferable to operational noise.

**Coexistence with Priority Override:** Calm means “no *admitted* Decisions for this merchant context,” not “VIP is silent.” Override-admitted Decisions may still appear; they do not authorize turning L3 background into L2 noise.

### 6.12 Human Judgment Exists to Increase Recovery

The merchant is invited only when human judgment is expected to outperform continued automation (or when Priority Override policy requires immediate Decision eligibility).

Otherwise CartFlow continues autonomously under Execution Ownership.

---

## 7. Ownership transition rules (deterministic)

Minimum constitutional state machine (detail tables are downstream):

| From (Decision Owner) | To | Gate |
|-----------------------|----|------|
| CartFlow | Merchant | Decision Admission success (normal or Priority Override path) |
| Merchant | CartFlow | Decision resolved, expired, returned, or superseded per policy; or cart leaves L2 scope (e.g. completed → L4) |

| From (Execution Owner) | To | Gate |
|------------------------|----|------|
| CartFlow | Merchant | Explicit scoped manual-execution handoff only |
| Merchant | CartFlow | Manual scope closed or policy return |

During Priority Override: **Execution Owner remains CartFlow** unless a scoped manual-execution handoff occurs. **Decision Owner** may become Merchant immediately upon override Admission.

---

## 8. Relationship to adjacent constitutions

| Layer / doc | Relationship to Cart Workspace Constitution |
|-------------|-----------------------------------------------|
| **Knowledge Layer** | Produces knowledge/claims for proof — not workspace cards by default |
| **Observation / Evidence / Proof** | Upstream of Decision Admission; never skip into L2 |
| **Merchant Decision Governance / Foundation** | Peer governance for *when* decisions may exist platform-wide; Cart Workspace is the **surface law** for how admitted decisions appear to merchants on this page |
| **Merchant Decision Engine** | Future scorer/ranker — must obey Admission + this Constitution; cannot create workspace noise |
| **Admin Operations** | Separate operator surface — must not be merged into Cart Workspace |
| **Operational Excellence / metrics** | Measure success per §6.10 — must not redefine workspace identity |
| **Cart Page Product Constitution** | Sibling product law for carts page questions/actions; after ratification, conflicts are resolved by explicit amendment (see Open Questions) |

---

## 9. Constitutional boundaries — what Cart Workspace must never become

Cart Workspace must never become:

1. A CRM  
2. A generic cart list  
3. A reporting or analytics dashboard  
4. A notification center or notification feed  
5. An operational monitor / health screen  
6. A message inbox or message center  
7. A timeline viewer (as primary identity)  
8. A database browser  
9. A task manager or generic todo board  
10. A workflow engine builder  
11. An Admin Operations console  
12. A Knowledge / insights browser  

**Allowed:** A Decision Workspace that shows only admitted Decisions with required explanation and one primary Action — and a calm empty state when none exist.

---

## 10. Closing statement

Cart Workspace is not designed to expose system activity.  
It is designed to preserve merchant attention, maximize automation, and request human judgment only when that judgment is expected to create measurable business value — under deterministic ownership and Decision Admission.

---

# Part B — Constitutional Change Log (V1 → V2)

| ID | Change | Why | Why V2 is stronger |
|----|--------|-----|-------------------|
| **C1** | Split “one operational owner” into **Execution Ownership** vs **Decision Ownership** | V1’s single owner conflicted with VIP “CartFlow continues observing” while “human intervention starts immediately” | Removes the dual-owner paradox; makes handoffs deterministic |
| **C2** | Redefined VIP as **Priority Override Layer (L0)**, not “higher priority” | V1 wording invited queue-priority thinking and fought Quiet by Default | Quiet and Override coexist: Override admits differently; Quiet still bans L3 noise |
| **C3** | Added formal **Signal / Evidence / Status / Proof / Decision / Action** taxonomy | V1 mixed status examples with decision language | Prevents status-driven IA from returning under new names |
| **C4** | Added full **Definitions** section | V1 left terms to interpretation | Years-stable vocabulary; implementers cannot redefine in code reviews |
| **C5** | Added **Constitutional Layers** L0–L4 | V1 had principles without structural stack | Admission and background cannot bypass the surface law |
| **C6** | Clarified **Waiting** is not a workspace category (status); wait-as-decision only if admitted | V1 listed Waiting as banned category without defining wait-as-decision | Compatible with sibling cart-page “Wait” primary when it is the Decision |
| **C7** | Expanded **Never Become** list (task manager, workflow engine, notification feed, admin console, knowledge browser) | V1 list was strong but incomplete vs platform growth | Protects identity as Admin Ops, Knowledge, OE mature |
| **C8** | Added **Ownership transition rules** | V1 required explainability without a minimum state machine | Downstream maps have a constitutional skeleton |
| **C9** | Added **Adjacent constitutions** compatibility section | V1 did not situate itself in CartFlow’s constitutional system | Prevents Cart Workspace from absorbing Knowledge/Admin/Engine roles |
| **C10** | Added **Authority / precedence** | V1 could be misread as overriding truth governance | Explicit subordination to truth/evidence authorities |
| **C11** | Reordered principles; marked order as constraining | V1 list was parallel; conflicts were unresolved | Earlier principles win; reviewable |
| **C12** | Replaced informal “Operational Owner” as primary term | Ambiguous under dual ownership | Composite term demoted; precise terms required |

---

# Part C — Constitutional Questions (Closed at Ratification)

All former open questions are **Closed**. Binding text: [`cart_workspace_ratification_v1.md`](cart_workspace_ratification_v1.md) §2; CDRs 005–006, 010–014.

| # | Topic | Status | Governing closure |
|---|--------|--------|-------------------|
| **Q1** | VIP Decision Ownership timing | **Closed** | Immediate transfer on Override Admission |
| **Q2** | Wait vs Decision | **Closed** | Wait = operational strategy / Status; not Workspace category |
| **Q3** | Precedence vs Cart Page Product Constitution | **Closed** | This Pack prevails on Workspace conflicts |
| **Q4** | Operational History / archive scope | **Closed** | Outside L2; L4 / history surfaces |
| **Q5** | CS notify | **Closed** | Configurable; absence does not violate L0 |
| **Q6** | Dedicated VIP surface | **Closed** | Allowed; remains Cart Workspace identity |

Reopening requires the amendment process in the Ratification record.

---

# Part D — Constitution Stability Assessment

### Ready to become the governing reference?

**Yes — Verdict A (Ratified).** See [`cart_workspace_ratification_v1.md`](cart_workspace_ratification_v1.md).

| Criterion | Result |
|-----------|--------|
| Internal consistency (Quiet ↔ Override; dual ownership) | **Pass** |
| Ownership determinism | **Pass** at constitutional minimum; Ownership Map next |
| Decision vs Status separation | **Pass** |
| Definitions completeness | **Pass** (Glossary V1) |
| Layer model | **Pass** |
| Boundaries / identity protection | **Pass** |
| Compatibility with Knowledge / Decision Governance / Admin Ops / OE | **Pass** |
| Constitutional questions Q1–Q6 | **Closed** |

### What does *not* need to exist for ratification

- UI mockups  
- Admission Matrix  
- Implementation  
- Public process `git_sha` or runtime probes  

Those remain correctly downstream under the ratified hierarchy.

---

**End of Cart Workspace Constitution V2 package.**
