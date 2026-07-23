# Home Executive Constitution V1

**Document type:** Foundational Product Constitution  
**Status:** **Approved / Locked — Ratified**  
**Date (UTC):** 2026-07-19  
**Ratified (UTC):** 2026-07-19  
**Authority:** Permanent constitutional foundation for every present and future CartFlow **Home** implementation  

**Ratification act:** Home Product Vision V2 is hereby promoted from product-vision candidate to **official constitutional reference**.

**Out of scope (hard STOP):**

- Full Home redesign · E2–E6 until their sprints open  
- Commercial Knowledge Expansion V1  

**Implementation note:** Executive Home Implementation V1 **Sprint 1 (E1)** is authorized and tracked in [`EXECUTIVE_HOME_E1_SPRINT1.md`](EXECUTIVE_HOME_E1_SPRINT1.md).

---

## 1. Ratification

The following documents are **constitutional** and binding:

| Document | Constitutional role |
|----------|---------------------|
| [`HOME_PRODUCT_VISION_V2.md`](HOME_PRODUCT_VISION_V2.md) | Executive purpose, IA bands E1–E6, hierarchy, disclosure, ownership, remove/merge/introduce |
| [`HOME_EXECUTIVE_QUESTION_REGISTRY_V2.md`](HOME_EXECUTIVE_QUESTION_REGISTRY_V2.md) | Permanent EQ-* merchant questions for Home |
| [`HOME_PRODUCT_VISION_V2_TRANSITION.md`](HOME_PRODUCT_VISION_V2_TRANSITION.md) | Lawful transition that preserves existing governed capabilities |

**Rule:** No future Home feature, section, card, insight, or composition path may contradict this constitution or the ratified pack above.  
Conflicts require **governance review first** — never silent code override.

---

## 2. Product registration — Home is an Executive Workspace

### 2.1 Official registration

| Field | Value |
|-------|-------|
| **Surface** | Home |
| **Product class** | **Executive Workspace** |
| **Purpose** | Help merchants understand their business and make better daily decisions |
| **Altitude** | Executive — merchant daily understanding |
| **Cognitive budget** | ~30 seconds to the six executive outcomes |

### 2.2 Home is not

| Forbidden class | Why |
|-----------------|-----|
| **Operational dashboard** | Metrics walls and widget grids are not executive understanding |
| **Engineering dashboard** | Pipelines, loaders, field names, and diagnostics are not merchant language |
| **Recovery monitoring page** | Recovery execution and case work belong on Carts / Decision Workspace / Communication |

### 2.3 Home still does not execute

Home **names** the decision of the day and **routes** work.  
Home does **not** replace Carts, Decision Workspace, Communication, or Settings.

Aligned with Merchant Trust: evidence before speech; silence is legal; no fake intelligence.

---

## 3. Permanent mission

Home exists to answer:

> **If a merchant opens CartFlow for 30 seconds every morning, what should they understand before doing anything else?**

Everything on Home exists only because it helps answer that question.

---

## 4. Permanent Information Architecture — executive question ownership

Home **permanently owns** these primary executive questions.  
**No other primary merchant surface may duplicate ownership** of these questions as its homepage job.

| Band | Name | Owns |
|------|------|------|
| **E1** | Business Health | Is my business healthy today? |
| **E2** | Decision of the Day | What decision should I make today? + highest-value action |
| **E3** | Biggest Opportunity | What opportunity am I about to miss? |
| **E4** | Business Understanding | What does CartFlow understand about my business today? |
| **E5** | Confidence | Is confidence sufficient to act? |
| **E6** | What's Changed | What changed since yesterday? (brief, not a feed) |

**Reading order (constitutional):** E1 → E2 → E3 → E4 → E5 → E6 → optional disclosure.  
Adaptive Cognition may reorder **admitted bands** only — it may not invent new primary band jobs.

**EQ registry** ([`HOME_EXECUTIVE_QUESTION_REGISTRY_V2.md`](HOME_EXECUTIVE_QUESTION_REGISTRY_V2.md)) is the Home question authority.  
**CQ registry** remains platform commercial-question inventory and **fuel** — not automatic Home sections.

---

## 5. Surface governance — section admission checklist

Every Home section (present or future) **must** satisfy all six:

| # | Requirement | Meaning |
|---|-------------|---------|
| 1 | **Merchant question** | Answers exactly one EQ-* (or disclosure under one) |
| 2 | **Executive purpose** | Serves the 30-second morning understanding mission |
| 3 | **Evidence source** | Governed platform truth / findings — never invented on Home |
| 4 | **Confidence source** | Explicit sufficiency stance (including “not enough yet”) |
| 5 | **Surface owner** | Named E1–E6 (or D* under a parent band) — one owner per fact |
| 6 | **Progressive disclosure eligibility** | L0 claim vs L1 why vs L2 how-we-know declared; L3 engineering never on Home |

**Sections failing these rules must not be implemented.**

---

## 6. Permanent executive principles

| # | Principle |
|---|-----------|
| EP-1 | **Merchant understanding before explanation** |
| EP-2 | **Decision before evidence** |
| EP-3 | **Evidence available on demand** |
| EP-4 | **Internal diagnostics hidden** |
| EP-5 | **Engineering terminology forbidden** on the merchant executive surface |
| EP-6 | **Executive simplicity** — density serves understanding, not completeness |
| EP-7 | **Progressive disclosure** — “How did we reach this?” collapsed by default; merchant-readable only |
| EP-8 | **One question → one owner** |

### Forbidden on Home (constitutional)

- Internal counters as merchant copy (e.g. `hesitation_total=0`, `returns=0`)  
- Evidence pipeline / loader / snapshot diagnostics  
- Canonical field names, finding type IDs, engine stage labels  
- Default-visible engine thinking  
- Implementation terminology  

---

## 7. Knowledge Routing — Home as executive consumer

Knowledge Routing **must** treat Home (`merchant_home`) as an **executive consumer**:

| Rule | Meaning |
|------|---------|
| **Target EQ bands** | Route toward E1–E6 / EQ-* jobs — not toward legacy Brief card keys as authority |
| **No card-first routing** | Existing UI section names are not the routing destination vocabulary |
| **Consumer only** | Home never becomes SoT for knowledge selection |
| **No diagnostics** | `admin_visibility` / diagnostic pipes never paint Home L0–L2 |
| **Budget** | Attention budget applies to executive bands; surfaces truncate, never re-rank platform priority |

Foundation amendment recorded in [`docs/knowledge_routing_foundation_v1.md`](docs/knowledge_routing_foundation_v1.md) §5.1 `merchant_home`.

---

## 8. Relationship to prior Home governance

| Document | Status after this ratification |
|----------|--------------------------------|
| [`HOME_CONSTITUTION_V2.md`](HOME_CONSTITUTION_V2.md) | **Superseded for purpose / primary questions / executive altitude** by this Constitution. Retained principles that remain binding unless they contradict: Home does not execute; VIP manual; governed consumer; Trust. |
| [`HOME_INFORMATION_ARCHITECTURE_V1.md`](HOME_INFORMATION_ARCHITECTURE_V1.md) | **Superseded for layer jobs / order** by E1–E6. Cognitive-layer *spirit* (one question per layer) continues under Vision IA. |
| [`HOME_SURFACE_CONTRACT_V1.md`](HOME_SURFACE_CONTRACT_V1.md) | **Amended in spirit:** Home remains governed consumer; admission now requires §5 checklist + EQ ownership. Formal Surface Contract revision may follow Implementation kickoff — **this Constitution already binds**. |
| [`HOME_INFORMATION_INVENTORY_V1.md`](HOME_INFORMATION_INVENTORY_V1.md) | Categories must map into E1–E6; timeline-as-primary is retired per Vision. |
| [`HOME_UX_BLUEPRINT_V1.md`](HOME_UX_BLUEPRINT_V1.md) | Journey intent maps to E1→E6 reading order; visual design still out of scope until Implementation. |
| [`HOME_PRODUCT_RATIFICATION_V1.md`](HOME_PRODUCT_RATIFICATION_V1.md) | Historical ratification of the 2026-07-18 suite. **This document is the new Home purpose ratification.** |
| [`PRODUCT_CONSTITUTION_ADDENDUM_V1.md`](PRODUCT_CONSTITUTION_ADDENDUM_V1.md) | Updated to register Home as **Executive Workspace** under this Constitution. |
| [`MERCHANT_TRUST_CONSTITUTION_V1.md`](MERCHANT_TRUST_CONSTITUTION_V1.md) | **Unchanged** — still binds speech. |

---

## 9. Next phase (authorized only after kickoff)

**Next:** Executive Home Implementation V1  

**Single implementation reference:** this Constitution + the three ratified Vision pack documents.  

Implementation must not begin until Product explicitly opens that phase.  
Commercial Knowledge Expansion remains separately gated.

---

## 10. STOP

- No implementation  
- No UI · no CSS · no components  
- No Commercial Knowledge Expansion  

**Await approval / kickoff before Executive Home Implementation V1.**

---

## Sign-off

| Field | Value |
|-------|-------|
| Ratification | **APPROVED / LOCKED** |
| Milestone | Home Executive Constitution V1 |
| Baseline for all future Home discussion | This document + ratified Vision pack |
