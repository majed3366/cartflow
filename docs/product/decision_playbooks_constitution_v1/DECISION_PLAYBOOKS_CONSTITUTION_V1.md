# Decision Playbooks Constitution V1

**Status:** Constitutional product foundation — architecture of decision generation only.  
**Date (UTC):** 2026-07-28  
**Object:** Decision Playbook (the executable business task CartFlow may publish as a Decision)  
**Non-goals of this pack:** No UI. No production copy. No Workspace redesign. No implementation.

**Authority:** Binding law for **how every CartFlow decision is generated**.  
**Related (superior / peer):**  
- Product Constitution V1 · Principle 0 · Principle 7  
- [`Decision Workspace Constitution V1`](../decision_workspace_constitution_v1/DECISION_WORKSPACE_CONSTITUTION_V1.md)  
- [`Decision Cards Constitution V1`](../decision_cards_constitution_v1/DECISION_CARDS_CONSTITUTION_V1.md)  
- [`Execution Methodology V1`](../execution_methodology_v1/EXECUTION_METHODOLOGY_V1.md) (**EM-001** · Types A/B/C · **EM-002**)  
- Diagnostic Reasoning Foundation V1 · Home Constitution V2  

A Decision that violates this Constitution is **unconstitutional**, even if it is well-written, data-rich, or visually polished.

Companion packs in this folder:

| Document | Role |
|----------|------|
| [`DECISION_PLAYBOOK_CATALOG_V1.md`](./DECISION_PLAYBOOK_CATALOG_V1.md) | Canonical families |
| [`DECISION_FAMILY_MATRIX_V1.md`](./DECISION_FAMILY_MATRIX_V1.md) | Cross-family matrix |
| [`PLAYBOOK_QUALITY_RULES_V1.md`](./PLAYBOOK_QUALITY_RULES_V1.md) | Publish / reject rules |
| [`PLAYBOOK_PUBLICATION_METADATA_V1.md`](./PLAYBOOK_PUBLICATION_METADATA_V1.md) | **PBL-002** family publication metadata (internal engine only) |

**Constitutional amendments in this pack:** **PBL-001** Playbook Confidence Law · **PBL-002** Playbook Publication Metadata.

---

## 1. Mission

CartFlow does **not** generate recommendations.

CartFlow generates **executable business playbooks**.

Every decision shown to a merchant must be:

| Property | Meaning |
|----------|---------|
| **Actionable** | Names a concrete business task |
| **Specific** | Identifies object, cohort, stage, or surface |
| **Evidence-backed** | Traceable to a diagnosis with sufficient evidence |
| **Measurable** | Declares how CartFlow will know it worked |

The merchant must immediately know:

1. **What** to do  
2. **Why**  
3. **Where**  
4. **Whether to act now**  

---

## 2. Executive Principle

| A Decision is | A Decision is not |
|---------------|-------------------|
| A **business task** supported by evidence | Information |
| An executable playbook instance | Advice |
| Commitment material | Analysis / a report |

If the merchant leaves with “interesting insight” and no task, CartFlow failed.

---

## 3. Relationship to other constitutions

| Layer | Owns | Does not own |
|-------|------|--------------|
| **Diagnostic Reasoning** | Observation → evidence → diagnosis → confidence | The merchant task |
| **Decision Playbook** (this pack) | Generation of the executable task from diagnosis + evidence | UI layout |
| **Decision Card / Workspace** | Presentation / commitment / saturation | Inventing a different recommendation language |
| **Execution Methodology** | How readiness, domain, six answers, and EM-002 loop operate after a playbook is eligible | Generating abstract advice |

**Hard rule:** Surfaces (Home, Workspace, Knowledge, Briefs, Future AI) **consume** Decision Playbooks.  
No page invents its own recommendation language.

---

## 4. Decision Quality Law

**No decision may be published until it answers all of the following.**

### 4.1 What exactly should the merchant do?

Must be a **business task**, not a theme.

Fails if the merchant still asks: *What exactly should I do?*

### 4.2 Why is this action recommended?

Must name **which diagnosis** produced it.

Fails if reason is generic (“to improve conversion”) without diagnostic lineage.

### 4.3 Where is the action performed?

Exactly one primary execution location:

| Location | Aligns with EM Type |
|----------|---------------------|
| **CartFlow** | Type A — Internal |
| **Commerce Platform** | Type B — External platform (Zid / Salla / Shopify / future) |
| **Business Operation** | Type C — Merchant ops outside CartFlow control |

Fails if location is ambiguous or “everywhere.”

### 4.4 Is the decision executable NOW?

Exactly one readiness state (**EM-001**):

| State | Playbook publication |
|-------|----------------------|
| **READY** | Full playbook may publish |
| **NEEDS_MORE_EVIDENCE** | Playbook **must not** publish as executable; diagnosis (or wait posture) only |
| **BLOCKED** | Playbook must not pretend action is available; explain block |
| **EXTERNAL_DEPENDENCY** | Playbook may describe external work with explicit dependency — never as CartFlow-controlled execution |

**If any answer is missing, the decision is not ready.**

---

## 5. Playbook Structure (mandatory sequence)

Every Decision Playbook follows **exactly**:

```
BUSINESS TASK
  ↓
REASON
  ↓
EXECUTION LOCATION
  ↓
READINESS
  ↓
EXPECTED BUSINESS RESULT
```

**Nothing else** is a peer structural layer of the playbook.

Supporting methodology detail (how / avoid / verify steps) is subordinate to this structure and governed by Execution Methodology V1 — it may not replace or reorder the five layers.

---

## 6. No Abstract Language

### Forbidden (non-exhaustive)

- Review conversion.  
- Improve checkout.  
- Optimize product.  
- Investigate customers.  
- Check shipping.  
- Review funnel.  

### Directionally allowed (illustrative — not production copy)

- Open shipping settings and review shipping costs for orders below a stated threshold because customers leave after shipping is shown.  
- Review the first recovery message because customers open it but rarely return to complete checkout.  
- Review the product page because customers repeatedly view the product but leave before checkout.  

Abstract verbs without object, cohort, stage, or cause are **unconstitutional**.

Full reject rules: [`PLAYBOOK_QUALITY_RULES_V1.md`](./PLAYBOOK_QUALITY_RULES_V1.md).

---

## 7. Specificity Law

Every playbook must identify the applicable specifics among:

| Dimension | Question |
|-----------|----------|
| **Object** | What object is acted on? |
| **Customers** | Which customers / cohort? |
| **Product** | Which product (when product-bound)? |
| **Message** | Which message / template (when message-bound)? |
| **Checkout stage** | Which stage (when funnel-bound)? |
| **Platform** | Which commerce platform locus (when Type B)? |

**Generic advice is forbidden.**

Missing specificity → playbook fails Specificity Law → must not publish.

---

## 8. Execution Law

The merchant must never need to ask:

- What exactly should I do?  
- Where should I start?  
- Which screen / surface?  

If those questions remain after reading the playbook, **the playbook fails**.

CartFlow owns clarity of task and location.  
The merchant owns commercial judgement and whether to commit.

---

## 9. Data Dependency Law

Every playbook family **must declare** minimum evidence requirements (see Catalog).

| Evidence state | Publication |
|----------------|-------------|
| Evidence **meets** family minimum | Playbook **may** generate (subject to Quality Law + readiness) |
| Evidence **insufficient** | Playbook **is not generated** — **only the diagnosis** (or honest insufficiency) is shown |

CartFlow must never invent a task to fill a blank card when evidence does not support one.

---

## 10. Reality Validation Law

Every playbook **must** declare how success will be measured after merchant action.

Validation is observation of business reality (**EM-002**), not a checkbox that the merchant clicked.

Illustrative validation classes (not metrics UI):

- Higher conversion  
- Lower abandonment  
- Higher return-to-checkout rate  
- Higher recovery rate  
- Higher purchase completion  

A playbook without a validation class is incomplete.

---

## 11. Reusability Law

The **same** Decision Playbooks feed:

| Consumer |
|----------|
| Workspace |
| Home |
| Knowledge Layer |
| Daily Brief |
| Weekly Brief |
| Monthly Summary |
| Future AI |

**No page creates its own recommendation language.**

Editorial altitude may differ (teaser vs full playbook), but the underlying playbook identity, task, location, readiness, and validation class must be shared.

---

## 12. Reading Success

A merchant should finish a playbook in **less than 15 seconds** and know:

| Question | Answered by |
|----------|-------------|
| What to do? | Business Task |
| Why? | Reason (diagnosis lineage) |
| Where? | Execution Location |
| Whether now? | Readiness |
| How CartFlow knows it worked? | Expected Business Result + Reality Validation |

---

## 13. Generation vs presentation

| Phase | Rule |
|-------|------|
| **Generate candidate** | Playbook engine (future) may draft a family instance from diagnosis + evidence |
| **Gate** | Publication pipeline (**PBL-001**) + Quality Rules + family metadata (**PBL-002**) |
| **Present** | Cards / Home / Briefs render the same playbook without rewriting the task into abstract advice |
| **Execute** | Execution Methodology answers how / avoid / verify when readiness allows |
| **Close** | EM-002 Action Evidence → Reality Validation → Decision Update |

---

## 14. PBL-001 — Playbook Confidence Law

**A valid diagnosis does NOT automatically produce a Decision Playbook.**

Before publication, every playbook must pass **its own quality validation** (Playbook Validation below), in addition to family evidence minima (**DP-004**) and EM-001 readiness.

### 14.1 Publication pipeline (binding)

```
Diagnosis
  ↓
Evidence
  ↓
Execution Readiness
  ↓
Playbook Validation
  ↓
Playbook Publication
```

| Step | Meaning |
|------|---------|
| **Diagnosis** | What is happening (Diagnostic Reasoning) |
| **Evidence** | Sufficiency for the candidate family |
| **Execution Readiness** | Exactly one EM-001 state |
| **Playbook Validation** | All seven validation questions = YES |
| **Playbook Publication** | Only after validation passes |

**If validation fails:** CartFlow publishes the **Diagnosis only**.  
**No Playbook is generated.**

### 14.2 Playbook Validation (all must be YES)

| # | Question |
|---|----------|
| **1** | Is the business task **specific**? |
| **2** | Can the merchant execute it **immediately**? *(applies when readiness = READY; other readiness states must not fake immediate executability)* |
| **3** | Does the merchant know **exactly where** execution happens? |
| **4** | Is the playbook supported by **sufficient evidence**? |
| **5** | Can CartFlow **verify the outcome**? |
| **6** | Is the expected business result **measurable**? |
| **7** | Would two different experts likely recommend the **same action** from the same evidence? (**Consistency Test**) |

If **any** answer is **NO**:

- The Playbook **fails validation**  
- **Diagnosis remains visible**  
- **Playbook is suppressed**

### 14.3 Preference rule

CartFlow would rather publish **no playbook** than publish a **weak playbook**.

---

## 15. PBL-002 — Playbook Publication Metadata

Every Playbook Family **must** define publication requirements (internal engine metadata).

### 15.1 Mandatory fields

| Field | Purpose |
|-------|---------|
| **Playbook Family** | Catalog family identity |
| **Business Domain** | Commercial domain the family governs |
| **Execution Type** | EM Type A / B / C |
| **Minimum Evidence** | Evidence bar before a candidate may enter validation |
| **Minimum Confidence** | Confidence floor before publication |
| **Minimum Readiness State** | Lowest EM-001 state that may publish a full playbook for this family |
| **Execution Location** | CartFlow · Commerce Platform · Business Operation |
| **Reality Validation Metric** | What CartFlow observes after action |
| **Success Threshold** | When validation counts as success |
| **Failure Behaviour** | What happens when validation fails or outcome fails (e.g. return to Diagnosis; continue collecting evidence) |
| **Review Cadence** | How often the family’s metadata / outcomes are reviewed |
| **Supported Platforms** | Which commerce platforms the family’s Type B locus covers |

Full schema, Shipping example, and engine rules: [`PLAYBOOK_PUBLICATION_METADATA_V1.md`](./PLAYBOOK_PUBLICATION_METADATA_V1.md).

### 15.2 Internal-only rule

**Publication metadata is internal.**

It must **never** be exposed to the merchant.

It exists only for the **Decision Playbook Engine**.

A family without complete PBL-002 metadata **must not** emit playbooks.

---

## 16. Published playbook success properties

Every published Playbook is:

| Property | Meaning |
|----------|---------|
| **Specific** | Named object / cohort / stage / locus |
| **Evidence-backed** | Meets family minimum evidence |
| **Consistent** | Passes Consistency Test (PBL-001 Q7) |
| **Executable** | Location + readiness honest; READY only when immediate execution is real |
| **Measurable** | Expected result + reality validation metric |
| **Governed** | Passes pipeline + Quality Rules + family metadata |
| **Repeatable** | Same family + evidence shape → same action class |

---

## 17. Constitutional IDs

| ID | Title |
|----|--------|
| **DP-001** | Decision Quality Law — all four answers required before publish |
| **DP-002** | Playbook Structure — Task → Reason → Location → Readiness → Expected Result only |
| **DP-003** | Specificity Law — object / cohort / stage / platform as applicable |
| **DP-004** | Data Dependency — insufficient evidence → diagnosis only, no playbook |
| **DP-005** | Reusability — one playbook language across all surfaces |
| **PBL-001** | Playbook Confidence Law — diagnosis ≠ playbook; validation pipeline; prefer none over weak |
| **PBL-002** | Playbook Publication Metadata — mandatory family fields; internal engine only |

---

## 18. Approval checklist

- [ ] Mission accepted: playbooks, not recommendations  
- [ ] Quality Law (DP-001) accepted  
- [ ] Structure (DP-002) accepted  
- [ ] Specificity + Execution laws accepted  
- [ ] Data Dependency (DP-004) accepted  
- [ ] Catalog + Family Matrix accepted as canonical families  
- [ ] Quality Rules accepted as publish gate  
- [ ] **PBL-001** Confidence Law + seven validation questions accepted  
- [ ] **PBL-002** Publication Metadata (internal-only) accepted  
- [ ] Reusability across Home / Workspace / Knowledge / Briefs / Future AI accepted  
- [ ] **No UI / no production copy / no implementation until approved**

---

## 19. STOP

This pack defines generation law only.

**No implementation. No UI. No production copy. No Workspace redesign.**

Await constitutional approval.
