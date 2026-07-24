# CartFlow Product Constitution V1

**Document type:** Permanent product constitution (merchant-facing page ownership)  
**Date (UTC):** 2026-07-24  
**Status:** **Draft — awaiting CEO approval**  
**Amendment:** Constitutional Principle — *Every Surface Must Lead to a Decision* (2026-07-24)  
**Authority (upon approval):** Binding for all future merchant-surface development  
**Supersedes (upon approval), on ownership conflicts:** page-ownership claims in `PRODUCT_CONSTITUTION_ADDENDUM_V1.md`, MEIF question wording where it diverges, and any feature that places Product Intelligence or decision explanation outside Decision Workspace  

**Related (subordinate after approval):**

| Document | Role after this constitution is approved |
|----------|------------------------------------------|
| [`HOME_EXECUTIVE_CONSTITUTION_V1.md`](../../HOME_EXECUTIVE_CONSTITUTION_V1.md) | Home executive altitude & disclosure — must not contradict page ownership here |
| [`PRODUCT_CONSTITUTION_ADDENDUM_V1.md`](../../PRODUCT_CONSTITUTION_ADDENDUM_V1.md) | Home purpose / explainability — amended: Home **summarizes and routes**; Decision Workspace **owns decisions & Product Intelligence** |
| [`docs/architecture/CARTFLOW_ARCHITECTURE_SURFACE_ALIGNMENT_AUDIT_V1.md`](../architecture/CARTFLOW_ARCHITECTURE_SURFACE_ALIGNMENT_AUDIT_V1.md) | Evidence of current misalignment vs this law |
| [`docs/product/PRODUCT_CONSTITUTION_COMPLIANCE_V1.md`](PRODUCT_CONSTITUTION_COMPLIANCE_V1.md) | Compliance matrix + P1–P7 work packages to reach 100% constitutional compliance |
| [`docs/product/CONSTITUTIONAL_MIGRATION_PLAN_V1.md`](CONSTITUTIONAL_MIGRATION_PLAN_V1.md) | Mandatory Execution Gates G1–G7 (no overlap; CEO closure; PI only after Gate 7) |
| [`docs/product/HOME_STABILIZATION_SPRINT_V1.md`](HOME_STABILIZATION_SPRINT_V1.md) | Painted Home teasers — must stay within Home Allowed Sections |

**Out of scope for this document:** Implementing Product Intelligence · UI redesign · new merchant features · code changes required for compliance (tracked separately after CEO approval)

---

## 1. Mission

Establish the **permanent constitutional ownership** of every merchant-facing page.

No page may gain responsibilities outside its constitutional ownership.

If a feature answers another page’s question, it belongs to that other page.

---

## 2. Philosophy — CartFlow exists for decisions

CartFlow is **not** a reporting platform.  
CartFlow is **not** a dashboard platform.  
CartFlow is **not** a CRM.

**CartFlow exists to help merchants make better decisions.**

Therefore every merchant-facing surface must ultimately help the merchant decide what to do next.

If a surface presents information without helping the merchant understand the next action, it is not fulfilling its constitutional purpose.

---

## 3. Constitutional principles

### Principle 0 — Every Surface Must Lead to a Decision

**Mandatory for all current and future merchant-facing surfaces.**

| Surface type of decision | Meaning |
|--------------------------|---------|
| **Business decision** | Owned only by Decision Workspace (includes Product Intelligence) |
| **Operational decision** | Owned by Carts or Communication (next operational step) |
| **Configuration decision** | Owned by Settings |
| **Executive routing decision** | Owned by Home (what to open next via View Details →) |

Information without direction is **constitutionally incomplete**.

### Principle 1 — One Page, One Question

Every page must answer **exactly one** merchant question.

The page must **fully** answer that question.

If a feature answers another question, it belongs to another page.

### Principle 2 — Every Answer Must End With Action

Every page must naturally guide the merchant toward an **operational** or **business** decision (per Principle 0).

- Home ends with **View Details →** to the owning surface.  
- Decision Workspace ends with a **recommended action**.  
- Carts ends with the **next operational step**.  
- Communication ends with **follow-up / wait / done / needs attention**.  
- Settings ends with a **configuration choice** (or confirmation of current config).

### Principle 3 — Executive Before Detail

Home is an **executive** surface.

- It summarizes.
- It never becomes an operational page.
- It never becomes an analytics page.
- It never becomes a reporting page.

### Principle 4 — Details Live With Their Owner

Every detail belongs only to its owning surface.

- Home **links**.
- Owner pages **explain**.

### Principle 5 — Single Technical Ownership

Every feature must declare exactly one of each:

| Declaration | Meaning |
|-------------|---------|
| Owning page | Merchant hash / surface |
| Owning service | Backend module |
| Owning query | Database / assemble path |
| Owning API | HTTP contract |
| Owning data source | Truth / package / store |

**Shared ownership is prohibited.**

Consumers may **read** another owner’s published summary contract. They may not **re-own**, re-calculate, or re-explain it.

### Principle 6 — Product Intelligence Boundary

**Product Intelligence belongs exclusively to Decision Workspace.**

No Product Intelligence may appear on Home, Carts, Communication, or Settings.

Home may show a **Product Observations executive teaser** (summary + status + count + View Details → Decision Workspace). That teaser is not Product Intelligence.

**All Product Intelligence V1 (and later) work is governed by Principle 0 and Principle 6.** PI may only ship on Decision Workspace and must end with a recommended action.

---

## 4. Permanent page constitution

*Every page below is bound by Principle 0 — Every Surface Must Lead to a Decision.*

### 4.1 Home — `#home`

| Field | Law |
|-------|-----|
| **Merchant question** | What should I know about my store right now? |
| **Purpose** | Executive guidance |
| **Decision type (P0)** | Executive routing — every section ends with a clear path to the appropriate detail page |
| **Arabic anchor** | ماذا يجب أن تعرف الآن؟ |

**Allowed sections only:**

1. Store Status  
2. Today's Decisions  
3. Product Observations  
4. Communication Summary  
5. Cart Summary  

**Every section must end with:** View Details →  

Home summarizes. Home never performs deep analysis.

**Forbidden on Home:**

- Tables  
- Timelines  
- Operational management  
- Deep analysis  
- Full Product Intelligence  
- Full Observation evidence  
- Full Cart timelines  
- Full Communication history  
- KPI / reporting walls  
- Setup theatre as primary content  

**Home may request only** lightweight executive summaries.

---

### 4.2 Decision Workspace — `#workspace`

| Field | Law |
|-------|-----|
| **Merchant question** | What decision should I make, and why? |
| **Purpose** | Decision engine — the **only** surface that owns business reasoning |
| **Decision type (P0)** | Business decision + Product Intelligence |
| **Owns** | **Product Intelligence** (exclusive) |

**Every recommendation must explain:**

- Why this matters  
- Evidence  
- Confidence  
- Business impact  
- Recommended action  

**Also owned here (when available):** related products · historical context  

**Forbidden:**

- Raw operational cart tables as the page’s job  
- Communication logs as primary content  
- Configuration  

**No other page may explain business decisions.**

---

### 4.3 Carts — `#carts`

| Field | Law |
|-------|-----|
| **Merchant question** | What is happening to each cart? |
| **Purpose** | Operational execution |
| **Decision type (P0)** | Operational — next step must be immediately obvious |

**Contains:**

- Product  
- Customer  
- Value  
- Status  
- Timeline  
- Current step  
- Next **operational** action  

**Examples of operational next step:** Wait · Contact customer · Recovery scheduled · Purchased · Closed  

**Forbidden:**

- Business recommendations  
- Intelligence  
- Merchant guidance (business)  

Operational “next step” is required. Business “you should discount because…” is not.

---

### 4.4 Communication — `#communication`

| Field | Law |
|-------|-----|
| **Merchant question** | What happened during customer communication? |
| **Purpose** | Communication execution / history |
| **Decision type (P0)** | Operational — merchant must immediately understand follow-up vs wait vs done vs needs attention |

**Contains:**

- Sent  
- Delivered  
- Failed  
- Replied  
- Waiting  
- No Phone  
- Returned  

The merchant should immediately understand whether:

- Follow-up is required  
- Waiting is acceptable  
- Communication has completed  
- A customer needs attention  

**Forbidden:**

- Decision logic (business)  
- Product Intelligence  
- Business recommendations / business intelligence  

`#messages` (if retained) is a **presentation alias** of Communication — not a second owner.

---

### 4.5 Settings — `#settings` (+ config siblings)

| Field | Law |
|-------|-----|
| **Merchant question** | How do I configure CartFlow? |
| **Purpose** | Configuration only |
| **Decision type (P0)** | Configuration choice — no operational guidance |

**Owns:** store connection, WhatsApp/widget/plans configuration, notification toggles, operating mode, diagnostics tools  

**Forbidden:** operational guidance · cart ops queues · Product Intelligence · executive Home content · business decisions  

---

## 5. Constitutional validation rule (mandatory pre-implementation)

Every new feature, widget, card, section, or page must pass this review **before implementation**. If any answer is unclear, the feature **must not** be implemented.

| # | Checklist question |
|---|--------------------|
| V-1 | Which merchant question does it answer? |
| V-2 | Which page constitution owns that question? |
| V-3 | Does it help the merchant reach a decision? (Principle 0) |
| V-4 | Would removing it reduce decision quality? |
| V-5 | Is another page already responsible for this decision? |

**Product Intelligence features** must additionally pass:

| # | PI checklist |
|---|--------------|
| PI-1 | Owning page is Decision Workspace only |
| PI-2 | Recommendation includes why / evidence / confidence / impact / action |
| PI-3 | No PI content on Home, Carts, Communication, or Settings |
| PI-4 | Home may only teaser + View Details → Decision Workspace |

---

## 6. Ownership declaration template

Every new or changed feature **must** include this block in its product/architecture note before merge:

```text
Owning page:        <home | decision_workspace | carts | communication | settings>
Owning service:     <python module path>
Owning query:       <query / assemble function>
Owning API:         <route>
Owning data source: <truth table / package / store>
Merchant question:  <must match owning page>
Decision type:      <executive_routing | business | operational | configuration>
Leads to decision:  <one sentence — next action the merchant can take>
Validation:         V-1…V-5 passed (and PI-1…PI-4 if Product Intelligence)
```

Pull requests that omit this declaration for merchant-visible behavior are **constitutionally incomplete**.

---

## 7. Home performance constitution

| Rule | Law |
|------|-----|
| **HP-1** | Home may request only lightweight executive summaries |
| **HP-2** | Heavy computation executes only inside the owning page’s API / load path |
| **HP-3** | Home must never load full Product Intelligence |
| **HP-4** | Home must never load full Observation evidence packages |
| **HP-5** | Home must never load full Cart timelines / cart list payloads |
| **HP-6** | Home must never load full Communication history |
| **HP-7** | Home View Details → navigates to the owning page (or expands only a constitutionally allowed teaser preview that is not analysis) |

Violation of HP-1…HP-7 is a **blocking defect**, not a performance tweak.

---

## 8. Product Intelligence boundary

| May show PI / decision explanation | Must not |
|------------------------------------|----------|
| Decision Workspace (`#workspace`) | Home |
| | Carts |
| | Communication |
| | Settings |

**Definition (constitutional):** Product Intelligence = merchant-facing product-bound business findings and decision explanation (why it matters, evidence, confidence, business impact, recommended action, related products, historical context).

**Home Product Observations teaser** = short summary + status + count + View Details → Decision Workspace. Not PI.

**Governance:** Future Product Intelligence work is explicitly governed by Principle 0, Principle 6, Section 5 (PI-1…PI-4), and this section. Shipping PI elsewhere is a constitutional violation.

---

## 9. Current feature → page map (compliance baseline)

Status legend: **Aligned** · **Misaligned** · **Split** · **Retire / merge**

| Feature / package (today) | Constitutional owner | Current placement | Status |
|---------------------------|----------------------|-------------------|--------|
| Home Executive Summary teasers (`home_executive_summary_v1`) | Home | Home | Aligned (paint) |
| Full MEIF Home / Decision / Carts / Comms packages on `/summary` | Per page APIs | Forced onto Home summary | Misaligned (HP-1…6) |
| Observation Reality Validation full package on summary | Decision (PI) / slim teaser Home | Home transport | Misaligned |
| Finding Decision Engine cards | Decision Workspace | MEIF Home + Decision (often unpainted) | Split |
| Cart Workspace (`#workspace`) | Decision Workspace | Decision Workspace | Aligned intent · must become sole Decision owner |
| MEIF Decision page package | Decision Workspace | Built on summary; paint gated | Split |
| Merchant Intelligence / value stories on Carts | Decision Workspace (if guidance) or retire | Carts | Misaligned |
| Normal-carts ops list / timeline / proof | Carts | Carts (+ eager boot on Home) | Misaligned boot |
| `#communication` MEIF stub | Communication | Often unpainted under HES | Split |
| `#messages` history | Communication | Separate hash + PII body | Split — merge under Communication |
| Settings / WA / Widget / Plans / Diagnostics | Settings | Settings siblings | Mostly aligned |
| Legacy Home painters (ECC, Pulse UI, PeV2, ORV sibling) | — | Still shipped; gated | Retire / merge |
| Adaptive Cognition / Pulse on summary when unused by Home | Owning page or off | Home finalize | Misaligned |
| Daily Brief / legacy `merchant_home_experience_v1` on summary | Home retired under HES | Still attached | Retire from Home path |

**Constitution is not “complete” until every row is Aligned or explicitly Retire/merge-closed.**

---

## 10. Acceptance criteria (constitution completeness)

This constitution is **complete for development use** only when **all** of the following are true:

1. Principle 0 (*Every Surface Must Lead to a Decision*) is part of Product Constitution V1.  
2. All page constitutions (Section 4) reference Principle 0 / decision type.  
3. The constitutional validation checklist (Section 5) is documented.  
4. Future Product Intelligence work is explicitly governed by Principle 0 and Principle 6.  
5. Every existing merchant-visible feature is mapped to **exactly one** page (Section 9 closed).  
6. Every duplicate responsibility is **removed**.  
7. Home requests **only** executive summaries (HP-1…HP-7 enforced).  
8. Architectural ownership matches product ownership (Section 6).  
9. This amendment is **committed, reviewed, merged**, and becomes part of the permanent CartFlow Product Constitution.  
10. **CEO has approved Product Constitution V1** before Product Intelligence V1 begins.

Until then: status remains **Draft — awaiting CEO approval** (or **Approved — compliance incomplete** after signature if P0 work remains).

---

## 11. Relationship to Architecture Surface Alignment Audit V1

The audit (`CARTFLOW_ARCHITECTURE_SURFACE_ALIGNMENT_AUDIT_V1.md`) is the **evidence pack**.  
This constitution is the **law**.

Audit P0 items are the minimum compliance program after CEO approval:

1. Slim Home transport  
2. Single Decision Workspace owner  
3. Carts ops-only boundary  
4. One Communication surface  
5. Remove dead Home painters from production boot  

---

## 12. STOP

**Do not begin Product Intelligence V1** until:

1. CEO approves **Product Constitution V1** (including Principle 0), and  
2. P0 ownership compliance is authorized (or an explicit written waiver records accepted risk).

No page may gain responsibilities outside this constitution after approval.

Product Intelligence may ship **only** on Decision Workspace and **must** lead to a recommended action.

---

## 13. Approval record

| Role | Name | Date (UTC) | Decision |
|------|------|------------|----------|
| CEO | _pending_ | _pending_ | _pending_ |

Upon approval, set **Status** to `Approved / Locked` and record the date above.
