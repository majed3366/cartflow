# Decision Workspace Constitution V1

**Status:** Foundational product constitution — governance only.  
**Surface:** Decision Workspace (`#workspace`)  
**Date (UTC):** 2026-07-28  
**Non-goals of this pack:** No UI redesign. No implementation. No diagnostic / evidence / collector changes.

**Authority:** Normative behavioural law for Decision Workspace.  
**Related:** Product Constitution V1 §4.2 · Principle 0 · Principle 7 (Executive Editorial Exclusivity) · Home Constitution V2 · Diagnostic Reasoning Foundation V1 · Collector Constitution V1 (subordinate — Collectors feed evidence; Workspace never collects).

This document defines **constitutional behaviour**. Implementation must conform after approval. Improvisation beyond this law is forbidden.

---

## 1. Mission

Decision Workspace exists for **one purpose only**:

> Help the merchant make the next correct business decision.

Nothing else.

If an element does not serve that purpose, it does not belong on this page.

---

## 2. The Question

This page answers **exactly one question**:

> What decision should I make now, and why?

Every element must help answer this question.

Anything that does not help answer it **must be removed**.

The question may appear once as page purpose. Synonym headlines that restate the same job without advancing the decision are forbidden.

---

## 3. This Is Not

Decision Workspace is **not**:

| Forbidden identity | Belongs elsewhere |
|--------------------|-------------------|
| Analytics | Reports / analytics surfaces (if any) |
| Dashboard | Home is the executive briefing — not this page |
| Reports | Outside Workspace |
| KPI page | Domains are not KPIs (Article 8) |
| Timeline | Operational / history owners |
| Cart list | Carts (`#carts`) |
| Communication history | Communication (`#communication`) |

Those surfaces may be **linked for execution** after a decision; they must not become the job of Workspace.

---

## 4. The Decision Law

**One decision at a time.**

The page must never feel like a list of reports.

The merchant should immediately know:

> Start here.

If the merchant cannot identify the primary decision within moments, the page has failed this Constitution.

---

## 5. Decision Hierarchy

### 5.1 Primary

Only **one** decision may be **Primary**.

### 5.2 Next decisions

Everything else becomes **Next decisions** (secondary).

### 5.3 Competing primary ban

Never show multiple competing primary decisions.

Cognitive load law (Article 9): the merchant processes at most one primary decision at once.

---

## 6. Decision Structure

Every decision must follow **exactly** this order:

| Step | Name | Merchant meaning |
|------|------|------------------|
| 1 | **Diagnosis** | What is happening? |
| 2 | **Why** | Why does CartFlow believe this? |
| 3 | **Evidence** | Only the evidence required for confidence — not raw logs |
| 4 | **Business Impact** | What happens if nothing changes? |
| 5 | **Recommended Action** | Exactly one next action |
| 6 | **Expected Outcome** | What improvement is expected? |

### 6.1 Order is law

Skipping, reordering, or collapsing steps so that Recommendation precedes Diagnosis is unconstitutional.

### 6.2 Evidence budget

Evidence is the **minimum** needed for trust. Raw logs, dumps, technical IDs, and diagnostic internals are forbidden as primary content.

---

## 7. Forbidden Openings

Do **not** start with:

- Review…
- Check…
- Improve…
- Consider…

The page **starts with diagnosis**.

Recommendation comes **later** (step 5), after Diagnosis → Why → Evidence → Business Impact.

---

## 8. Decision Sequence

The page must feel like:

```
Current Decision
  ↓
Complete it
  ↓
Next Decision appears
```

Not:

```
Decision
Decision
Decision
Decision
```

A vertical stack of equal-weight “decisions” that compete for attention violates the Decision Law and Decision Hierarchy.

---

## 9. Decision Domains

The top categories are **not** KPIs.

They are **Business Decision Domains**.

Examples:

- Pricing  
- Shipping  
- Recovery  
- Communication  
- Products  
- Operations  

### 9.1 Domain question

Each domain answers:

> Is there currently a decision here?

Not:

> How many?

### 9.2 Counts ban as domain job

Domain chrome must not become a KPI strip, badge wall, or volume scoreboard. Counts may appear only if they are necessary to make the **current** decision (and still subordinate to Diagnosis).

---

## 10. Cognitive Load

The merchant should never process more than **one primary decision** at once.

Additional decisions remain **secondary** (Next decisions) until the primary is completed, dismissed by constitutional rules, or superseded by a higher-priority primary under a single explicit hierarchy.

---

## 11. Decision Termination Law

Decision Workspace must **never** become an infinite decision list.

Every decision must have a clear lifecycle:

```
Candidate
  ↓
Active Decision
  ↓
Waiting for Merchant
  ↓
Resolved
  ↓
Archived
```

### 11.1 Attention rule

Only **Active Decisions** may compete for merchant attention.

**Resolved** or **Waiting for Merchant** decisions must not continue occupying **primary** decision space.

### 11.2 Infinite list ban

A Workspace that accumulates open decisions without termination paths is unconstitutional.

---

## 12. Decision Saturation Law

The merchant must never feel overwhelmed.

If ten valid decisions exist, CartFlow does **not** display ten.

CartFlow **prioritizes**.

The merchant always sees:

1. **One** primary decision  
2. A **limited** number of next decisions  
3. **Everything else waits**

Saturation is enforced even when every waiting item is “valid.” Validity does not entitle a decision to screen space.

---

## 13. No Decision Should Exist Forever

Every decision must eventually become one of:

- **Resolved**  
- **Superseded**  
- **Withdrawn**  
- **Insufficient evidence**  
- **Archived**

### 13.1 Permanent open ban

**No permanent “open recommendations.”**

A recommendation that never reaches a terminal state violates this Constitution.

---

## 14. No Duplication (Home ↔ Workspace)

**Home introduces. Workspace explains.**

If Home already says:

> Shipping needs attention

Workspace must **never** repeat Home’s executive introduction as a new executive message.

Workspace **explains** it: Diagnosis → Why → Evidence → Impact → Action → Outcome.

This article aligns with Product Constitution Principle 7 (Executive Editorial Exclusivity).

---

## 15. No Hidden Reasoning

Every recommendation must be traceable:

```
Diagnosis
  ↓
Evidence
  ↓
Recommendation
```

**Never Recommendation first.**

If evidence is insufficient, the page must say so honestly — it must not invent a confident recommended action. (Diagnostic honesty: `insufficient_evidence` / `conflicting_evidence` remain valid outcomes; they still follow Diagnosis → Why → Evidence before any cautious next step.)

---

## 16. Ownership Boundaries

| Concern | Owner |
|---------|--------|
| Executive introduction of a commercial situation | Home |
| Business decision + explanation + Product Intelligence | Decision Workspace (exclusive) |
| Cart operations | Carts |
| Communication execution / status | Communication |
| Configuration | Settings |
| Collection of new observables | Collectors (off path) — never Workspace |
| Diagnosis computation | Diagnostic / snapshot pipeline — Workspace **reads** published diagnosis; does not recompute on merchant whim |

Workspace may deep-link to Carts / Communication / Settings for **execution after** Recommended Action. Those destinations do not own the decision.

---

## 17. Executive Commitment Law

Decision Workspace exists to create **commitment**.

Every Primary Decision must answer:

> What am I committing to do?

### 17.1 Leave-state

The merchant should leave the page with **one clear commitment**.

Not with:

- more knowledge  
- more reports  
- more ideas  

### 17.2 Success gate

The page succeeds **only** if it produces **one committed business action**.

Knowledge without commitment is failure. Explanation without a commitable action is failure. A menu of ideas is failure.

### 17.3 Relation to Recommended Action

The constitutional Recommended Action (structure step 5) is the commitment candidate. Ambiguous, multiple, or soft openings (“Review… / Consider…”) do not satisfy this Law.

Honest insufficient evidence may produce a commitment to **wait / gather evidence / not act yet** — that is still one clear commitment, not an open idea list.

---

## 18. Success

A successful Decision Workspace allows a merchant to:

```
Understand
  ↓
Trust
  ↓
Decide
  ↓
Act (commit)
```

**without** reading unnecessary information.

Decision Workspace behaves like an **executive task queue**, not an endless report.

The page succeeds only if it produces **one committed business action** (Executive Commitment Law).

Success is not: more panels, more charts, more decisions visible at once, permanent open recommendations, or more knowledge without commitment.

---

## 19. Ratification checklist (pre-implementation)

Before any UI redesign or implementation:

- [ ] Mission: next correct business decision only  
- [ ] Single question enforced  
- [ ] Not analytics / dashboard / reports / KPI / timeline / cart list / comms history  
- [ ] One primary decision; others are Next decisions  
- [ ] Structure order 1–6 preserved  
- [ ] No Review/Check/Improve/Consider openings  
- [ ] Sequence: Current → Complete → Next (not equal stack)  
- [ ] Domains answer “is there a decision?” not “how many?”  
- [ ] Decision Termination Law: lifecycle + only Active compete for attention  
- [ ] Decision Saturation Law: one primary + limited next; everything else waits  
- [ ] No permanent open recommendations; every decision reaches a terminal state  
- [ ] Executive Commitment Law: leave with one clear commitment / one committed business action  
- [ ] No Home executive duplication  
- [ ] Traceable Diagnosis → Evidence → Recommendation  
- [ ] Success: Understand → Trust → Decide → Act (commit); executive task queue, not endless report  

---

## 20. Explicit stop

**No implementation** under this task.

Do not redesign UI yet.  
Do not change diagnostics, evidence, or collectors.

Await constitutional approval before any Decision Workspace implementation work.

**STOP.**
