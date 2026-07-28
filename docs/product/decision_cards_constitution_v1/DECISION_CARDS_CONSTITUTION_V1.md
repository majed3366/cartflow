# Decision Cards Constitution V1

**Status:** Product architecture only — governance for every Decision Card.  
**Date (UTC):** 2026-07-28  
**Object:** Decision Card (the executive decision object on Decision Workspace and any surface that presents a card-shaped decision)  
**Non-goals of this pack:** No UI. No implementation. No coding. **No Storyboard changes.**

**Authority:** Constitutional behaviour of every Decision Card.  
**Related (superior / peer):**  
- [`Decision Workspace Constitution V1`](../decision_workspace_constitution_v1/DECISION_WORKSPACE_CONSTITUTION_V1.md)  
- [`Decision Workspace Information Budget V1`](../decision_workspace_information_budget_v1/DECISION_WORKSPACE_INFORMATION_BUDGET_V1.md)  
- [`Decision Workspace Storyboard V1`](../decision_workspace_storyboard_v1/DECISION_WORKSPACE_STORYBOARD_V1.md) (journey — unchanged by this pack)  
- Product Constitution V1 · Principle 7 · Diagnostic Reasoning honesty  

A Decision Card that violates this Constitution is **unconstitutional**, even if it is visually polished or data-complete.

---

## 1. Mission

A Decision Card is **not** an information card.

It is an **executive decision object**.

Every card exists to move the merchant from **understanding to commitment**.

If a card only informs, reports, or lists options without producing commitment, it has failed this Constitution.

---

## 2. One Card = One Decision

A card must never contain multiple competing decisions.

| Required singularity | Forbidden |
|----------------------|-----------|
| **One** diagnosis | Multiple diagnoses or “also consider…” siblings |
| **One** commitment | Multiple actions, option menus, brainstorming |
| **One** outcome | Competing expected outcomes for different actions |

If two decisions are needed, they are **two cards** (Primary / Next / Future) — never one overloaded card.

---

## 3. Card Lifecycle (sequence is law)

Every card follows **exactly** this order:

```
Diagnosis
  ↓
Reasoning
  ↓
Evidence
  ↓
Business Consequence
  ↓
Commitment
  ↓
Expected Outcome
```

### 3.1 Sequence ban

Nothing may appear **outside** this sequence as peer content on the card.

No side panels of equal weight. No “also interesting” blocks. No KPI strip interrupting the sequence.

### 3.2 Alignment

This sequence is the card-level expression of Decision Workspace Storyboard STEPs 2–6 (plus Expected Outcome). Orientation of *which* card is Primary is a Workspace concern; **inside** the card, this sequence rules.

---

## 4. The First Sentence

The first sentence must always answer:

> What is happening?

**Never** lead with:

- Review…  
- Improve…  
- Check…  
- Consider…  

**Recommendations never lead. Diagnosis always leads.**

---

## 5. Evidence Law

Evidence exists **only** to justify the diagnosis.

It must **never** become the main content.

| Allowed | Forbidden |
|---------|-----------|
| Minimum evidence that strengthens confidence in the Diagnosis | Evidence dumps, logs, timelines as the card’s job |
| Proof that supports Why / Diagnosis | Evidence that introduces a second diagnosis |
| Short, merchant-legible support | Technical IDs, scoring math, implementation detail |

If evidence crowds out Diagnosis → Reasoning → Consequence → Commitment, the card has violated this Law.

---

## 6. Commitment Law

Every card **ends** with **one** commitment.

| Required | Forbidden |
|----------|-----------|
| Exactly **one** business commitment | Multiple actions |
| Clear “what I am committing to do” | Options menu |
| Commitment after Consequence | Brainstorming / “you could also…” |

Soft openings and multi-CTA footers fail this Law.

Honest **insufficient evidence** may end with one commitment to wait / not act yet / gather what is missing — still **one** commitment, not an open idea list. (Aligns with Workspace Executive Commitment Law.)

---

## 7. No Report Law

The merchant must never feel they are **reading a report**.

The merchant must feel they are **preparing to act**.

| Report smell (fail) | Decision object (pass) |
|---------------------|------------------------|
| Dense proof without commitment | Short path to one commitment |
| “Interesting facts” | Diagnosis → act |
| Scroll-to-understand | Commit-to-act |

---

## 8. Card Completion

A card must have an **ending**. No endless cards.

Every card must eventually reach a terminal (or holding) state:

| State | Meaning |
|-------|---------|
| **Waiting** | Awaiting merchant / external condition — must not keep Primary attention forever |
| **Resolved** | Commitment completed or decision closed |
| **Superseded** | Replaced by a better / newer decision |
| **Insufficient Evidence** | Honest stop; may commit to wait/gather |
| **Archived** | Removed from active attention |

### 8.1 Endless card ban

A card that remains forever “open” without a completion path violates this Constitution (aligns with Workspace Termination / “no forever” laws).

---

## 9. Card Relationship

Cards relate in a strict hierarchy of attention:

```
Primary Card
  ↓
Next Cards
  ↓
Future Cards
```

### 9.1 Non-competition

Cards must **never** compete for attention as equals.

| Role | Attention |
|------|-----------|
| **Primary Card** | Dominates — the decision of the meeting |
| **Next Cards** | After commitment to Primary — limited queue |
| **Future Cards** | Wait — not painted as peers |

Validity of a Future Card does not entitle it to Primary space (Saturation).

---

## 10. Ownership boundaries

| Concern | Owner |
|---------|--------|
| Card constitutional shape | This Constitution |
| Which card is Primary / Next / Future | Decision Workspace Constitution (hierarchy, saturation, termination) |
| How much evidence / reading | Decision Workspace Information Budget |
| Cognitive timing of the meeting | Decision Workspace Storyboard (unchanged by this pack) |
| Diagnosis truth | Diagnostic / snapshot publication — cards **present**, do not invent |
| Ops execution after commitment | Carts / Communication / Products / Settings as linked by the one commitment |

---

## 11. Success

If the merchant reads **one** card and immediately knows:

> I know exactly what I am committing to.

The card **succeeds**.

Success is not: more information, more options, more evidence, or a prettier report.

---

## 12. Ratification checklist (pre-implementation)

Before any Decision Card UI or implementation:

- [ ] Card is an executive decision object (not an information card)  
- [ ] One card = one diagnosis, one commitment, one outcome  
- [ ] Lifecycle sequence Diagnosis → Reasoning → Evidence → Consequence → Commitment → Expected Outcome — nothing outside  
- [ ] First sentence answers “What is happening?” — no Review/Improve/Check lead  
- [ ] Evidence justifies diagnosis only — never main content  
- [ ] Exactly one business commitment — no options / brainstorming  
- [ ] No report feeling — preparing to act  
- [ ] Completion path: Waiting / Resolved / Superseded / Insufficient Evidence / Archived  
- [ ] Primary → Next → Future; no competing equals  
- [ ] Success test: merchant knows exactly what they are committing to  

---

## 13. Explicit stop

**Deliverable complete for Decision Cards Constitution V1.**

- No Storyboard changes  
- No UI  
- No implementation  

**STOP.**
