# Cart Workspace Glossary V1

**Status:** Authoritative linguistic reference — Cart Workspace Governance Pack  
**Date (UTC):** 2026-07-12  
**Scope:** Canonical vocabulary for Cart Workspace and dependent CartFlow surfaces  
**Law:** [`cart_workspace_constitution_v2.md`](cart_workspace_constitution_v2.md)  
**Reasoning memory:** [`cart_workspace_constitutional_decisions_log_v1.md`](cart_workspace_constitutional_decisions_log_v1.md)  
**Ratification:** [`cart_workspace_ratification_v1.md`](cart_workspace_ratification_v1.md) — **Verdict A**  
**Validation:** [`cart_workspace_constitution_v2_validation.md`](cart_workspace_constitution_v2_validation.md)

---

## Document purpose

Every important Cart Workspace term has **exactly one** canonical meaning.

- This document defines **language**, not implementation.  
- No future document may redefine these terms.  
- New concepts **extend** this Glossary; they do not silently change existing meanings.  
- Product, UX, Engineering, Knowledge Layer, Admin Operations, and future contributors must use these definitions.

**Amendment rule:** Add or revise only via explicit Glossary version bumps / additive entries. Do not overwrite history in place without a versioned change note.

---

## 1. Constitutional Terms

### Decision

**Definition:** A business judgment requested from the merchant because human judgment is expected to create measurable value beyond what continued automation can safely achieve (under applicable policy, including Priority Override).

A Decision has one purpose, one explanation contract, and one primary Action. It appears in Workspace only after successful Decision Admission.

**Does not mean:** notification; message; event; signal; status; proof bundle; knowledge card; generic alert.

**Depends on / used by:** Constitution §§1, 3, 4, 6.5–6.8, 6.12; CDR-003, CDR-004, CDR-008; Admission; Decision Card; Decision Ownership.

---

### Automation

**Definition:** Operational work performed autonomously by CartFlow without requiring merchant attention.

Automation is the default mode of recovery Execution Ownership.

**Does not mean:** “no system activity”; “merchant has no visibility anywhere in the product”; “no logging or proof upstream.”

**Depends on / used by:** Constitution §§2, 6.2, 6.8, 6.12; CDR-002; Execution Ownership; Background Operations; Quiet by Default.

---

### Escalation

**Definition:** The governed transfer of **Decision Ownership** from CartFlow to the merchant after successful **Decision Admission** (normal path or Priority Override path).

Escalation is triggered by **expected human value** (or Override policy requiring immediate Decision eligibility)—not by the mere occurrence of events, messages, or status changes.

**Does not mean:** any notification; any customer reply; any failed send; any VIP detection without Admission; transfer of Execution Ownership; opening Admin Operations.

**Depends on / used by:** Constitution §§4, 6.2, 6.12, 7; CDR-002, CDR-006; Decision Admission; Decision Ownership.

---

### Priority Override

**Definition:** A constitutional operational mode (Layer L0) reserved for exceptional business-value situations (for example VIP). It applies a **different policy**: immediate merchant notification; customer-service notification if configured; Override Admission path that must not wait behind normal Decision queues; immediate Decision Ownership transfer upon Override Admission; continued CartFlow Execution Ownership unless a scoped manual-execution handoff occurs.

**Does not mean:** higher sort order inside the same queue; “more important status”; stopping all CartFlow execution; bypassing Decision Admission entirely; a separate product identity outside Cart Workspace law.

**Depends on / used by:** Constitution §§5, 6.3, 7; CDR-005, CDR-006; Validation Scenario D; Escalation (override path).

---

### Attention Budget

**Definition:** The finite amount of merchant attention CartFlow is permitted to consume on Cart Workspace. Attention is an **operational resource**. Visibility, cards, and fields are allowed only when expected Operational Value exceeds attention cost.

**Does not mean:** unlimited context is always helpful; engagement metrics; notification volume targets; “show activity so merchants feel informed.”

**Depends on / used by:** Constitution §§6.1, 6.9, 6.10; CDR-001, CDR-009; Quiet by Default; Decision Admission; Decision Card.

---

### Quiet by Default

**Definition:** The preferred Workspace state when no human Decision is admitted. Silence is success. Canonical meaning: nothing requires the merchant’s decision now; CartFlow continues recovery automatically.

**Does not mean:** the platform is idle; VIP must be silent; history/knowledge surfaces must be empty; merchants may never receive notifications outside Workspace.

**Depends on / used by:** Constitution §6.11; CDR-007; Attention Budget; Decision Admission (reject → quiet); Validation Scenarios A, B, E, F.

---

## 2. Ownership Terms

### Execution Ownership

**Definition:** Who currently executes operational recovery—scheduling, messaging, observation, lifecycle progression, and related autonomous or scoped manual work.

Exactly one Execution Owner at all times. Default: **CartFlow**. Merchant holds Execution Ownership only under explicit scoped manual-execution policy.

**Does not mean:** who must make the next business judgment; who sees Workspace cards; who owns truth minting.

**Depends on / used by:** Constitution §§4, 6.4, 7; CDR-006; Automation; Priority Override; Ownership Transition.

---

### Decision Ownership

**Definition:** Who currently owns the next business judgment for a cart.

Exactly one Decision Owner at all times: **CartFlow** when no Decision is admitted (merchant must not be interrupted), or **Merchant** after successful Decision Admission (including Override Admission).

**Does not mean:** who runs messaging; who owns Admin Operations; shared/ambiguous “both responsible.”

**Depends on / used by:** Constitution §§4, 6.4, 6.2, 7; CDR-002, CDR-006; Escalation; Decision; Decision Admission.

---

### Operational Owner

**Definition:** In Cart Workspace vocabulary, the **canonical party responsible for execution**—i.e. the current **Execution Owner**.

Prefer saying **Execution Ownership** in new documents. “Operational Owner” is retained only as a synonym for Execution Owner to avoid legacy ambiguity with Decision Ownership.

**Does not mean:** Decision Owner; dual owner of “the cart” as a single undifferentiated responsibility.

**Depends on / used by:** Constitution §4 (composite term demoted); CDR-006; Ownership Transition.

---

### Ownership Transition

**Definition:** The governed, deterministic transfer of either Execution Ownership or Decision Ownership from one party to another, under an explicit gate (e.g. Decision Admission success; Decision resolved/expired/returned; scoped manual-execution handoff; exit from active Workspace scope to Completed Outcome).

Transitions must be explainable: from → to → gate → policy basis.

**Does not mean:** informal “merchant took over”; UI navigation; notification delivery alone; status change alone.

**Depends on / used by:** Constitution §7; CDR-006; Escalation; Decision Admission; Ownership Map (downstream).

---

## 3. Decision Engine Terms

### Signal

**Definition:** A raw operational observation (e.g. message accepted, phone absent, timer fired, customer reply detected).

Signals are platform observations. They are not merchant Decisions and not Workspace categories.

**Does not mean:** Decision; Evidence; Proof; Workspace card; escalation trigger by itself.

**Depends on / used by:** Constitution §§4, 6.5; CDR-004; Evidence; Background Operations; Observation Layer.

---

### Evidence

**Definition:** Validated information derived from one or more Signals (and governed truth sources), under evidence-ownership rules. Evidence supports Proof; it is not itself a Decision.

**Does not mean:** raw log line; UI copy; Decision; Status category; unrestricted “facts” without ownership.

**Depends on / used by:** Constitution §4; CDR-004; Proof; Decision Admission; Knowledge / Evidence Registry (upstream authorities).

---

### Status

**Definition:** An internal operational state describing where automation or lifecycle work is (e.g. waiting, sent, replied).

Statuses serve the platform. They must never be used as merchant-facing Workspace organizing categories.

**Does not mean:** Decision; Action; Workspace section; Proof.

**Depends on / used by:** Constitution §§4, 6.5; CDR-004; Background Operations; Quiet by Default.

---

### Proof

**Definition:** Evidence composed to a governed standard sufficient to support business reasoning and to precede Decision Admission. Proof demonstrates that claims are warranted at a declared confidence posture.

**Does not mean:** Decision; Action; merchant interruption; Workspace card by itself.

**Depends on / used by:** Constitution §4; Decision Admission; Evidence; Merchant Decision Governance / Proof of Value (peer authorities).

---

### Decision Admission

**Definition:** The constitutional gate that determines whether consuming merchant attention is justified—i.e. whether a Decision may exist and appear in Workspace. Nothing reaches Workspace without Admission (normal path or Priority Override path). Admission verifies that automation cannot safely improve further under policy, or that Override policy requires immediate Decision eligibility.

**Does not mean:** sorting; notification send; VIP detection alone; Knowledge publish; Admin alert; bypass of Explain Before Asking.

**Depends on / used by:** Constitution §§4, 5 (L1), 6.2, 6.8; CDR-002, CDR-005; Escalation; Decision Card; Quiet by Default.

---

### Action

**Definition:** The single primary operational request attached to an admitted Decision—the one thing the merchant is asked to do (or the one admitted non-action that *is* the Decision, if and when constitutionally allowed).

Actions without Decisions are prohibited on Workspace.

**Does not mean:** secondary controls competing as equals; bulk toolbox; status filter; notification; timeline expand.

**Depends on / used by:** Constitution §§4, 6.6, 6.7; CDR-008; Decision; Decision Card.

---

## 4. Workspace Terms

### Decision Card

**Definition:** The Workspace representation of exactly one admitted Decision: one purpose, one explanation, one primary Action.

**Does not mean:** status row; message thread; analytics tile; multi-purpose panel; knowledge insight card.

**Depends on / used by:** Constitution §§6.6–6.7; CDR-008, CDR-009; Decision; Action; Attention Budget.

---

### Workspace

**Definition:** The merchant-facing operational **Decision** surface whose sole mission is to answer: **ما يحتاج قرارك؟** — presenting only admitted Decisions (or Quiet by Default when none exist).

Also called **Cart Workspace**.

**Does not mean:** CRM; dashboard; inbox; reporting page; generic cart list; notification center; task manager; Admin Operations; Knowledge browser; timeline-primary product.

**Depends on / used by:** Constitution §§1, 3, 5 (L2), 9; CDR-003; Quiet by Default; Decision Card.

---

### Background Operations

**Definition:** Operational work intentionally kept out of merchant Attention Budget—Signals, Statuses, Automation execution, and related L3 activity—unless promoted through Proof and Decision Admission into Decision explanation.

**Does not mean:** “unlogged”; “unmonitored by Admin Ops”; “invisible to Knowledge/History surfaces.”

**Depends on / used by:** Constitution §§5 (L3), 6.2, 6.5, 6.11; CDR-002, CDR-007, CDR-010; Automation; Status; Signal.

---

### Completed Outcome

**Definition:** Operationally finished work (e.g. recovery completed automatically, purchased/resolved cases as outcomes). It is **not** an active Decision and must not enter Workspace as a request for judgment.

Completed Outcomes belong to L4 / history / knowledge-appropriate surfaces, not to active Decision Workspace.

**Does not mean:** archived Decision still needing judgment; Quiet empty state; failure disguised as completion.

**Depends on / used by:** Constitution §§5 (L4), Validation Scenario E; CDR-010; Quiet by Default; Ownership Transition (exit L2).

---

## 5. Product Terms

### Human Gain

**Definition:** The expected increase in recovery (or equivalent measurable business outcome) attributable to applying human judgment versus continuing Automation alone.

Human Gain is the economic justification for Escalation and Attention Budget spend.

**Does not mean:** merchant “engagement”; click-through on cards; volume of interruptions.

**Depends on / used by:** Constitution §§1.1, 6.1, 6.12; CDR-001, CDR-002, CDR-009; Decision Admission; Operational Value.

---

### Merchant Attention

**Definition:** The scarce operational resource Cart Workspace is sworn to protect—the merchant’s capacity to notice, understand, and judge.

**Does not mean:** session length; notification inbox size; time spent browsing history.

**Depends on / used by:** Constitution §§1, 6.1, 6.9; CDR-001; Attention Budget; Quiet by Default.

---

### Operational Value

**Definition:** Business value created by consuming Merchant Attention (typically via admitted Decisions that produce Human Gain).

**Does not mean:** information completeness; engineering throughput; number of visible widgets.

**Depends on / used by:** Constitution §§6.1, 6.9, 6.10; CDR-001, CDR-009; Decision Admission; Attention Budget.

---

### Cognitive Load

**Definition:** Mental effort imposed on the merchant by Workspace structure, density, competing actions, and non-decision content.

Reducing Cognitive Load is a constitutional objective because excess load destroys Decision quality and Attention Budget.

**Does not mean:** “make the UI prettier”; “fewer pixels only”; removal of required Explain Before Asking context.

**Depends on / used by:** Constitution §§6.1, 6.7, 6.9; CDR-001, CDR-008, CDR-009; Decision Card; Quiet by Default.

---

## 6. Forbidden Misinterpretations (summary table)

| Term | Must not be treated as |
|------|-------------------------|
| Decision | notification, message, event, signal, status, proof-only card |
| Automation | absence of all platform work; lack of upstream proof |
| Escalation | any event; any reply; VIP detect without Admission; Execution handoff |
| Priority Override | queue priority; Admission bypass; total Execution stop |
| Attention Budget | engagement KPI; “more context is free” |
| Quiet by Default | system failure; VIP silence obligation |
| Execution Ownership | Decision Ownership |
| Decision Ownership | Execution Ownership; shared dual judgment |
| Operational Owner | Decision Owner (use Execution Owner) |
| Ownership Transition | UI click; notify-only; status flip |
| Signal | Decision; Escalation trigger alone |
| Evidence | Decision; Status category |
| Status | Workspace category; Decision |
| Proof | Decision; interruption |
| Decision Admission | sort; notify; publish knowledge |
| Action | toolbox of equal CTAs |
| Decision Card | status row; inbox item; multi-purpose panel |
| Workspace | CRM, dashboard, inbox, report, cart list, notification feed |
| Background Operations | “no ops anywhere” |
| Completed Outcome | active Decision |
| Human Gain | engagement |
| Merchant Attention | vanity time-on-page |
| Operational Value | card count |
| Cognitive Load | aesthetics-only concern |

---

## 7. Cross References — Constitutional dependence

| Glossary term | Primary Constitution anchors |
|---------------|------------------------------|
| Decision | §§1, 3, 4, 6.5–6.8, 6.12 |
| Automation | §§2, 6.2, 6.8, 6.12 |
| Escalation | §§4, 6.2, 6.12, 7 |
| Priority Override | §§5, 6.3, 7 |
| Attention Budget | §§6.1, 6.9, 6.10 |
| Quiet by Default | §6.11 |
| Execution Ownership | §§4, 6.4, 7 |
| Decision Ownership | §§4, 6.4, 7 |
| Operational Owner | §4 (synonym discipline) |
| Ownership Transition | §7 |
| Signal | §§4, 6.5 |
| Evidence | §4 |
| Status | §§4, 6.5 |
| Proof | §4 |
| Decision Admission | §§4, 5, 6.2, 6.8 |
| Action | §§4, 6.6, 6.7 |
| Decision Card | §§6.6, 6.7 |
| Workspace | §§1, 3, 5, 9 |
| Background Operations | §§5, 6.2, 6.5, 6.11 |
| Completed Outcome | §§5, Validation E |
| Human Gain | §§1.1, 6.1, 6.12 |
| Merchant Attention | §§1, 6.1, 6.9 |
| Operational Value | §§6.1, 6.9, 6.10 |
| Cognitive Load | §§6.1, 6.7, 6.9 |

CDR cross-links: see Constitutional Decisions Log V1 (CDR-001…010) for *why* these meanings were locked.

---

## 8. Relationship to other authorities

| Authority | Role relative to this Glossary |
|-----------|--------------------------------|
| Cart Workspace Constitution V2 | Defines law; Glossary defines words used by that law |
| Constitutional Decisions Log V1 | Preserves reasoning; must use Glossary terms |
| Merchant Decision Governance / Foundation | Peer decision-stage governance; must not redefine Workspace terms |
| Engineering / Truth constitutions | Own truth minting; do not redefine Workspace vocabulary |
| Knowledge / Evidence Registry | Own evidence mechanics; “Evidence” here is the Workspace-facing meaning aligned to those authorities |

Where a peer document needs a narrower technical sense, it must **qualify** the term (e.g. “registry evidence_id”) rather than redefine the Glossary entry.

---

## Maintenance

1. **Extend** with new entries when new constitutional concepts appear.  
2. **Never** silently change a definition’s meaning; publish Glossary V2+ with explicit deltas if meaning must change.  
3. Downstream docs (Ownership Map, Admission Matrix, UX Blueprint, etc.) **reference** these definitions; they do not restate competing ones.

---

**End of Cart Workspace Glossary V1.**
