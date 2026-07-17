# Product Constitution Addendum V1 — Revenue First Home

**Document type:** Product Constitution (purpose only)  
**Status:** **Approved** — permanent constitutional reference for Home  
**Date (UTC):** 2026-07-17  
**Approved (UTC):** 2026-07-17  
**Revision:** Final Constitutional Completion (mission · explainability · progressive disclosure)  
**Authority:** Permanent constitutional reference for **Home**  
**Born from:** Product Review Session V1 · PIB-1 · PIB-2 · PIB-3 · constitutional completion review  

**Out of scope:** Implementation · UI redesign · architecture · Widget · WhatsApp · Knowledge code · PIB-4 · new product features  

> Home is not a dashboard.  
> Home is not a customer journey viewer.  
> Home is not a knowledge browser.  
> **Home is the merchant’s operational understanding and decision surface.**  
> Its purpose is to help the merchant quickly understand the store, identify revenue opportunities, and make better operational decisions.

**Relationship to other constitutions**

| Document | Relationship |
|----------|--------------|
| [`MERCHANT_TRUST_CONSTITUTION_V1.md`](MERCHANT_TRUST_CONSTITUTION_V1.md) | Governs *when* CartFlow may speak — this addendum governs *what Home exists to achieve* and *how merchants understand, trust, and consume* Home |
| [`PRODUCT_REVIEW_SESSION_V1.md`](PRODUCT_REVIEW_SESSION_V1.md) | Locked Home/Knowledge/Brief/Timeline speech contracts — this addendum sets the revenue-first purpose gate above them |
| PIB-1 / PIB-2 / PIB-3 reviews | Execution of truth alignment, Attention queue, Recovery Journey explainability — subordinate to this purpose |

**STOP:** PIB-4 (and further Home Product Iteration) remains closed until Merchant Product Review V2. Future Product Iteration tasks must comply with this constitution.

**Finality:** No further Product Constitution revisions should be made unless they redefine the product philosophy itself. This document is the constitutional reference for all future Home evolution.

---

## Mission

Define the permanent purpose of Home — not only what Home shows, but how merchants **understand**, **trust**, and **consume** information.

Home is the merchant’s **operational understanding and decision surface**.

Its purpose is to help the merchant quickly understand the store, identify revenue opportunities, and make better operational decisions.

Home exists so a merchant can operate the store toward recovered revenue with clear understanding first, then clear decisions — not so CartFlow can display systems, journeys, or knowledge for their own sake.

### Understanding before decision

Home is responsible for both:

1. **Operational understanding**  
2. **Operational decision making**

**Operational understanding always comes before operational decisions.**

A merchant who cannot understand the store cannot make a trustworthy decision — even if an action button is present.

---

## Revenue First Principle

**Revenue is the product objective.**

| Exists | Only because it… |
|--------|------------------|
| Knowledge | Improves recovered revenue and merchant decisions |
| Recovery Journey | Explains blockers and actions that affect recovered revenue |
| Widget | Captures contact / reasons that enable recovery revenue |
| WhatsApp | Delivers recovery that converts carts into revenue |
| Attention | Queues decisions that protect or unlock recovered revenue |
| Metrics | Change decisions that affect recovered revenue |

Knowledge is not the objective.  
Recovery Journey is not the objective.  
Widget is not the objective.  
WhatsApp is not the objective.

They are instruments. Recovered revenue, store understanding, and decision quality are the ends.

---

## Home Purpose

Home exists to help the merchant:

1. **Recover more revenue.**  
2. **Understand the store.**  
3. **Make better operational decisions.**

Every Home element must directly support one or more of these goals.

### What Home is

| Home is | Home is not |
|---------|-------------|
| Operational **understanding and** decision surface | A dashboard of systems health |
| Place where the store becomes understandable in seconds | A customer journey viewer |
| Shortest truthful path to “what is happening” and “what now?” | A Knowledge browser |
| Summarizer of Knowledge into understanding and decisions | A notification feed or activity stream |
| Ordered Attention queue for action or justified calm | A dump of evidence, timelines, or diagnostics |

---

## Home Questions

Home must answer **only** these questions:

1. **Where is my biggest revenue opportunity today?**  
2. **What is preventing that opportunity from becoming revenue?**  
3. **What is CartFlow currently doing?**  
4. **Do I need to act?**  
5. **If I act now, how does that improve the outcome?**

If Home cannot answer these questions, it is incomplete.

No other primary questions may displace these five on Home.

---

## Content Rules

Every Home card must satisfy **at least one**:

| Rule ID | Rule |
|---------|------|
| **HC-1** | Increases recovered revenue (directly or by unlocking blocked recovery) |
| **HC-2** | Improves merchant understanding of the store (with evidence) |
| **HC-3** | Improves merchant decision quality (clearer action, priority, or justified non-action) |

Otherwise, the card **does not belong on Home**.

### Forbidden Home content (purpose violations)

- Numbers that do not change a decision  
- Journey detail that does not explain opportunity, blocker, action, or platform behavior  
- Knowledge pedagogy that does not support Home understanding or a Home decision  
- Activity / completion theatre that frames limits as wins  
- Conclusions without explainability (see Explainability Rule)  
- Detail that belongs on depth surfaces but increases Home cognitive load (see Progressive Disclosure Rule)  

---

## Explainability Rule

**Every conclusion shown on Home must be explainable.**

The merchant should always understand:

1. **Why this appears**  
2. **What evidence supports it**  
3. **Why it matters**  
4. **What happens next**

Home must never present conclusions without explainability.

**Explainability is mandatory for merchant trust.**

| Rule ID | Rule |
|---------|------|
| **HE-1** | No Home conclusion without a merchant-readable why |
| **HE-2** | No Home conclusion without supporting evidence (counts, cases, or governed Knowledge message) |
| **HE-3** | No Home conclusion without stated relevance (why it matters to revenue, understanding, or action) |
| **HE-4** | No Home conclusion without a next step — action, wait, or justified calm |

### Product principle

> CartFlow never asks the merchant to trust hidden logic.  
> Every meaningful conclusion must be supported by understandable evidence.

This rule aligns with Merchant Trust Constitution principles (evidence before speech; explainability before authority) and binds Home specifically: speech on Home that cannot be explained is a constitutional violation — not a UX polish gap.

---

## Progressive Disclosure Rule

**Home answers first. Details come later.**

The merchant should understand the store within seconds.

Evidence depth, timelines, diagnostics, and investigation remain available through dedicated product surfaces **without** increasing Home cognitive load.

| Layer | Role |
|-------|------|
| **Home** | Summarizes — answers the five Home questions quickly |
| **Other surfaces** | Expand — Knowledge, Timeline, Cart Detail, diagnostics |

| Rule ID | Rule |
|---------|------|
| **HP-1** | Home surfaces the understanding and the decision — not the full investigation |
| **HP-2** | Deeper evidence may exist elsewhere; Home must not require it to answer the five questions |
| **HP-3** | Adding depth to Home is forbidden when it raises cognitive load without improving a Home question answer |
| **HP-4** | Progressive disclosure never hides required explainability (HE-1…HE-4); it hides *investigation*, not *why* |

### Product principle

> Never overload Home.  
> Surface the decision.  
> Allow deeper investigation elsewhere.

Home summarizes.  
Other product surfaces expand.

---

## Journey Rules

Customer Journey is **explanatory. Never primary.**

Journey information appears on Home **only** when it explains:

- a revenue opportunity, or  
- a recovery blocker, or  
- a merchant action, or  
- platform behavior relevant to a decision  

| Allowed | Forbidden |
|---------|-----------|
| Journey chapter on an Attention decision that unlocks recovery revenue | Journey visibility for its own sake |
| Stage / channel / blocker that answers Home questions 2–5 | Full journey browser on Home |
| “CartFlow is waiting because…” tied to a decision | Timeline dump as Home’s main story |

Journey visibility must never exist for its own sake.  
Journey detail beyond decision explainability belongs on progressive-disclosure surfaces — not as Home primary content.

---

## Knowledge Rules

| Rule ID | Rule |
|---------|------|
| **HK-1** | Knowledge explains. |
| **HK-2** | Knowledge does not compete with Home. |
| **HK-3** | Knowledge supplies evidence. |
| **HK-4** | Home summarizes understanding and decisions. |

Home inherits counts, messages, and confidence honesty from Knowledge when they support Home understanding or a Home decision.  
Home must never contradict Knowledge.  
Home must never replace Knowledge as the depth surface (Progressive Disclosure).

---

## Attention Rules

Attention is the merchant’s **decision queue**.

| Attention is | Attention is not |
|--------------|------------------|
| Ordered decisions by merchant priority | A notification feed |
| Blocked revenue work first | An activity stream |
| Action or justified calm — each item explainable | A list of observations without ask |

Every Attention item must lead to either:

1. **Merchant action**, or  
2. **Merchant confidence that no action is required.**

If an item does neither, it does not belong in Attention.  
If an item cannot satisfy the Explainability Rule, it does not belong in Attention.

---

## Metric Rules

Metrics exist on Home **only when they change decisions** or materially improve store understanding that leads to a decision.

| Allowed | Forbidden |
|---------|-----------|
| A count that proves the top revenue opportunity or blocker | KPI walls |
| A number that justifies act vs wait | Vanity totals with no next step |
| Evidence digits inside an explainable decision card | Metric grids that outrank Attention |

Numbers without decisions (or without explainable understanding that serves a decision) do not belong on Home.

---

## Future Feature Gate

Before adding any future Home feature, ask:

> Does this help the merchant:  
> • recover more revenue?  
> • understand the store?  
> • make a better decision?

And additionally:

> Can the merchant see why it appears, what evidence supports it, why it matters, and what happens next?  
> Does it keep Home as the summary — with deeper investigation elsewhere?

| Answer | Disposition |
|--------|-------------|
| **Yes** to purpose + explainability + progressive disclosure, and the feature answers one of the five Home questions | May proceed through Product Iteration (after this constitution is approved) |
| **No** to purpose questions | Feature belongs elsewhere — not Home |
| Yes to purpose, but fails explainability | Forbidden on Home until explainable |
| Yes to purpose, but overloads Home with investigation detail | Belongs on Knowledge / Timeline / Cart Detail — not Home primary |

No PIB-4 or later Home Product Iteration may open without passing this gate.

---

## Acceptance Criteria

This constitution is **product-complete** when Product Review can affirm:

| ID | Criterion |
|----|-----------|
| **CA-1** | Home purpose is defined as operational **understanding and** decision surface — not dashboard / journey viewer / knowledge browser |
| **CA-2** | Operational understanding is recognized as coming before operational decisions |
| **CA-3** | Revenue First Principle is binding: instruments serve recovered revenue, understanding, and decisions |
| **CA-4** | The five Home questions are the only primary questions Home must answer |
| **CA-5** | Content rules HC-1…HC-3 are the membership test for every Home card |
| **CA-6** | Explainability Rule (HE-1…HE-4) is mandatory for every Home conclusion |
| **CA-7** | Progressive Disclosure Rule (HP-1…HP-4) is binding: Home summarizes; other surfaces expand |
| **CA-8** | Journey is explanatory-never-primary; Knowledge explains; Attention is a decision queue; metrics require decision value |
| **CA-9** | Future Feature Gate includes purpose, explainability, and progressive disclosure |
| **CA-10** | This document is **Approved** as the permanent Home constitutional reference; PIB-4+ still awaits Merchant Product Review V2 |

**Does not mean:** Home UI is redesigned, PIB-4 is implemented, or product READY (C01–C15) is claimed.

---

## Compliance for future PIBs

After approval, every Home-facing Product Iteration Backlog item must:

1. Name which Home question(s) it improves.  
2. Name which of HC-1 / HC-2 / HC-3 it satisfies.  
3. Show how HE-1…HE-4 (explainability) are satisfied.  
4. Show how HP-1…HP-4 (progressive disclosure) are respected.  
5. Pass the Future Feature Gate explicitly in its review.  
6. Refuse scope that turns Home into a journey browser, metric wall, Knowledge clone, or unexplained conclusion surface.

---

## Final Recommendation

| Field | Value |
|-------|--------|
| **Decision** | **APPROVED** — Product Constitution Addendum V1 — Revenue First Home (Final Constitutional Completion) |
| **Authorizes** | Home Product Iteration under this purpose gate **after** Merchant Product Review V2 |
| **Does not authorize** | PIB-4 before merchant review · UI redesign from theory · further constitution edits without philosophy change |

---

## Appendix — One-sentence law

> **Home exists so the merchant can quickly understand the store and turn that understanding into recovered revenue through clear, explainable decisions — everything else on Home is either evidence for those decisions or it does not belong.**
