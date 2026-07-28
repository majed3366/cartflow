# Execution Methodology V1

**Status:** Product foundation — architecture and methodology only.  
**Date (UTC):** 2026-07-28  
**Non-goals of this pack:** No UI. No buttons. No deep-link implementation. No provider integrations. No Workspace visual changes.

**Authority:** Normative execution philosophy for every merchant Decision after commitment.  
**Related (subordinate / peer):** Product Constitution V1 · Principle 0 · Decision Workspace Constitution V1 (Executive Commitment Law · Decision Termination / Saturation) · Decision Cards Constitution V1 · Diagnostic Reasoning Foundation V1 · Home Constitution V2 · Principle 7 (Executive Editorial Exclusivity).

This document defines **how CartFlow helps the merchant execute** — not how CartFlow becomes an operations console. Implementation must conform after approval. Improvisation beyond this methodology is forbidden.

**Constitutional amendments in this pack:** **EM-001** Execution Readiness · **EM-002** Action Evidence & Decision Update Loop.

---

## 1. Mission

CartFlow is **not** responsible for executing merchant operations.

CartFlow **is** responsible for helping the merchant **execute the correct business decision**.

Execution may occur:

| Locus | Meaning |
|-------|---------|
| **Inside CartFlow** | CartFlow owns the tool surface (e.g. carts queue, conversation follow-up) |
| **Inside the commerce platform** | Zid / Salla / Shopify (or future) owns the control |
| **Inside merchant operations** | People, contracts, creative, policy — outside software CartFlow controls |

The methodology must be **provider-agnostic**: the same philosophy works across Zid, Salla, Shopify, and future integrations. Provider-specific *steps* may vary; the *answers* CartFlow must give do not.

---

## 2. Core Principle — Never Send Blind

**Never send the merchant somewhere without explaining:**

| Must explain | Question answered |
|--------------|-------------------|
| **Why** | Why this action, why now |
| **Where** | Which locus / surface / system |
| **How** | What to do there (enough to act) |
| **What success looks like** | How the merchant and CartFlow know it worked |

A link, button, or destination without these four explanations is a methodology failure — even if the destination is correct.

---

## 3. Separation of Concerns (Hard Rule)

CartFlow must **never pretend** it controls systems it does not control.

Every Decision presentation must keep three layers distinct:

| Layer | Job | Forbidden confusion |
|-------|-----|---------------------|
| **Diagnosis** | What is happening and why we believe it | Not an action; not a claim of control |
| **Execution** | What the merchant should do, where, and how | Not a claim that CartFlow performed the platform change |
| **Verification** | How CartFlow will observe whether it worked | Not automatic “Done” without evidence |

Recommendations that collapse diagnosis into a fake “Fix in CartFlow” when the work lives in Zid/Salla/Shopify/ops are forbidden.

---

## 4. EM-001 — Execution Readiness

**A diagnosis does not automatically become executable.**

Before any Execution Methodology (six answers, destinations, how-to) is presented, CartFlow **must** determine **execution readiness**.

Every Decision **must** have **exactly one** readiness state.

### 4.1 Readiness states

| State | Meaning | Merchant posture |
|-------|---------|------------------|
| **READY** | Evidence is sufficient. Merchant action is justified. | Execution Methodology **may** be presented |
| **NEEDS_MORE_EVIDENCE** | Evidence is not yet sufficient. CartFlow continues collecting evidence. | Merchant **should not act yet**. No full Execution Methodology as if action were justified |
| **BLOCKED** | Execution cannot proceed because a prerequisite is missing (e.g. missing platform capability, missing merchant configuration, missing required evidence). | Explain the block; do not pretend the action is available |
| **EXTERNAL_DEPENDENCY** | Execution depends on an external platform, provider, or business operation. | CartFlow **explains the dependency**; methodology may instruct but must not claim CartFlow will perform the external work |

### 4.2 Presentation rule (binding)

**Execution Methodology may only be presented when the readiness state allows it.**

| State | Methodology presentation |
|-------|--------------------------|
| **READY** | Full six answers permitted (subject to Type A/B/C) |
| **NEEDS_MORE_EVIDENCE** | Commitment may be to wait / allow evidence collection — **not** a fake “go execute now” methodology |
| **BLOCKED** | Explain prerequisite; methodology for the blocked action is withheld until unblocked |
| **EXTERNAL_DEPENDENCY** | Methodology may describe merchant/platform/ops action with explicit dependency — never as internal CartFlow control |

### 4.3 Classification vs readiness

- **Execution Type (A/B/C)** answers *where* work happens.  
- **Readiness** answers *whether* CartFlow may present executable methodology now.  
- Both are required. Type B/C often correlates with **EXTERNAL_DEPENDENCY**, but readiness is evaluated separately (a Type A Decision can still be **BLOCKED** or **NEEDS_MORE_EVIDENCE**).

---

## 5. Decision Classification — Execution Types

Every Decision **must** belong to **exactly one** primary execution type.

### TYPE A — Internal Execution

Action can be completed **inside CartFlow**.

Examples:

- Review abandoned carts  
- Contact customers (via CartFlow communication paths)  
- Review conversations  
- Monitor recoveries  

**CartFlow may own the destination.** Still must explain why / where / how / success. Readiness must still be **READY** (or an honest wait commitment if not).

### TYPE B — External Platform Execution

Action happens **inside the commerce platform** (Zid / Salla / Shopify / future).

Examples:

- Shipping settings  
- Payment methods  
- Product page edits  
- Pricing  
- Delivery configuration  

**CartFlow does not control the platform.** It may deep-link or instruct; it must not claim completion until verification evidence exists. Copy and destinations must be provider-aware without changing the methodology.

### TYPE C — Business Execution

Action happens **inside the merchant business** (ops, creative, commercial negotiation).

Examples:

- Negotiate shipping contracts  
- Photograph products  
- Improve packaging  
- Create promotions  
- Operational policy changes  

**CartFlow does not execute these.** It commits the merchant to a business action and verifies later via evidence and outcomes.

### Classification rules

1. Choose the type by **where the decisive work happens**, not by where CartFlow shows the card.  
2. If work spans types, assign the **primary** type to the commitment; secondary steps may be noted under How, not as competing commitments.  
3. Type must be explicit in Decision architecture (contract field) before any UI paints destinations.  
4. Misclassification (e.g. shipping contract as Type A) is a product defect.

---

## 6. Execution Methodology — Six Mandatory Answers

When readiness **allows** presentation (EM-001), every Decision that asks for commitment **must** answer all six:

| # | Question | Purpose |
|---|----------|---------|
| 1 | **What should I do?** | One clear commitment (aligns with Executive Commitment Law) |
| 2 | **Why now?** | Urgency / cost of delay — not generic advice |
| 3 | **Where do I perform it?** | Type A / B / C locus + concrete place (CartFlow surface, platform area, or business activity) |
| 4 | **How should I perform it?** | Enough steps or criteria to act without guessing “what do I click?” |
| 5 | **What should I avoid doing?** | Anti-patterns that waste time or worsen the diagnosis |
| 6 | **How will CartFlow verify whether the decision worked?** | Verification plan (EM-002) — never empty |

If any answer is missing, the Decision is **not execution-ready**. Honest insufficient evidence maps to readiness **NEEDS_MORE_EVIDENCE** (or a wait commitment) — not a fabricated six-answer execute-now path.

---

## 7. EM-002 — Action Evidence & Decision Update Loop

**Merchant execution does not close a Decision.**

Execution **must** be followed by observation.

### 7.1 Action Evidence

CartFlow **never assumes** execution succeeded.

Instead it observes **business evidence**, for example:

- Conversion improvement  
- Abandonment reduction  
- Purchase increase  
- Confidence increase  
- Diagnostic change  
- Merchant outcome (where observable)

Action Evidence is input to Reality Validation — not a merchant “I did it” checkbox alone.

### 7.2 Reality Validation (before → after)

Reality Validation compares:

**Before execution** → **After execution**

and determines whether the **expected business outcome** actually occurred.

As applicable to the Decision:

| Check | Intent |
|-------|--------|
| Did the **evidence** improve? | Gaps closed; stronger observables |
| Did **conversion** improve? | Outcome movement where relevant |
| Did **abandonment** decrease? | Funnel / recovery pressure relieved |
| Did the **diagnosis** become stronger or resolve? | Confidence up, conflict down, or lifecycle advance |
| Did the expected **merchant outcome** appear? | What success was promised in the methodology |

### 7.3 Decision Update (mandatory)

After Reality Validation, **every Decision must change state**.

Allowed outcomes (at least one must apply — Decision must leave permanent Active):

| Outcome | Meaning |
|---------|---------|
| **Resolved** | Expected outcome observed; Decision complete |
| **Continue Monitoring** | Action taken or in flight; evidence not yet conclusive — observe further (not permanent Active attention) |
| **Escalated** | Outcome worse / blocked / needs higher priority treatment |
| **Superseded** | Replaced by a stronger or newer Decision |
| **Reopened** | Prior close was wrong; evidence demands return to attention (then readiness re-evaluated) |
| **Withdrawn** | No longer justified; removed from queue |

### 7.4 Permanence rule (binding)

**A Decision may never remain permanently Active.**

Every Decision **must eventually transition** to another state.

This aligns with Workspace Decision Termination / Saturation: executive task queue, not endless report.

### 7.5 Verification principles

1. Verification is **observation of reality**, not assumed success.  
2. Type B/C verification must not invent “settings saved” without evidence CartFlow can see.  
3. Failed or inconclusive validation stays honest — then update state (e.g. Continue Monitoring / Escalated / Withdrawn), never silent fake Resolved.  
4. Update loop must not reopen endless report mode or infinite Primary competition without readiness re-check (EM-001).

---

## 8. Closed Loop — Success Shape

Execution is a **measurable closed loop**:

```
Diagnosis
    ↓
Execution Readiness (EM-001)
    ↓
Execution Methodology (six answers, when allowed)
    ↓
Merchant Action
    ↓
Action Evidence
    ↓
Reality Validation (before → after)
    ↓
Decision Update (EM-002)
    ↓
Resolved / Continue Monitoring / Escalated / …
```

Skipping readiness, methodology-without-readiness, or action-without-update is a methodology failure.

---

## 9. Provider Neutrality

| Allowed | Forbidden |
|---------|-----------|
| Same readiness + six answers + update loop for every store | Methodology that only works for one platform |
| Provider-specific *how/where* details as adaptation | Hard-coding one platform’s UI as the product law |
| Deep-links when safe and known | Pretending CartFlow changed Zid/Salla/Shopify state |
| Future integrations under the same types A/B/C and readiness states | New vendor-only readiness invented without amending this methodology |

---

## 10. Relationship to Existing Law

| Existing law | How this methodology fits |
|--------------|---------------------------|
| **Principle 0** — Every surface leads to a Decision | Execution is after Decision + readiness, not instead of diagnosis |
| **Workspace Constitution** — one commitment · Termination | Six answers serve one commitment; EM-002 forbids permanent Active |
| **Decision Cards** — Commitment Law | Commitment = answer #1 only when readiness allows execute-now |
| **Home / Principle 7** | Home introduces; Workspace explains; execution destinations do not steal editorial ownership |
| **Carts / Communication / Settings** | Type A destinations — they do not own diagnosis or skip readiness |
| **Diagnostic Reasoning** | Diagnosis owned by diagnostics; readiness gates execution presentation |

---

## 11. Success Definition

The merchant never wonders:

> What do I click?

Instead the merchant understands:

> What should I do next?

and

> How will CartFlow know whether it worked?

Success is the **closed loop** (§8): correct readiness → correct next action → honest Action Evidence → Reality Validation → Decision Update — not more buttons, not fake control, not silent “Done,” not permanent Active Decisions.

---

## 12. Explicit Non-Goals (This Pack)

- No UI, wireframes, or button designs  
- No deep-link registry implementation  
- No provider API writes for Type B  
- No automation that “fixes” Type C business work  
- No change to Decision ordering, publication, or Gate 0 performance contracts  
- No collector / evidence-pipeline implementation in this pack  

---

## 13. Approval Checklist (Before Any Implementation)

- [ ] Mission accepted: CartFlow helps execute Decisions; does not run the merchant’s business  
- [ ] Core Principle (why / where / how / success) binding  
- [ ] **EM-001** — every Decision has one readiness state; methodology only when allowed  
- [ ] Types A / B / C required on every Decision  
- [ ] Six answers mandatory when readiness allows execute presentation  
- [ ] Diagnosis ≠ Execution ≠ Verification enforced  
- [ ] **EM-002** — Action Evidence → Reality Validation → Decision Update; no permanent Active  
- [ ] Closed loop (§8) affirmed as success shape  
- [ ] Provider-neutral methodology affirmed  
- [ ] No UI / no implementation until this methodology (including EM-001 / EM-002) is approved  

---

## STOP

Architecture and methodology only.  
**Await approval before any execution UI, deep-links, or automation.**
