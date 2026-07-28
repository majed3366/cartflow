# Playbook Quality Rules V1

**Status:** Constitutional publish / reject gate.  
**Date (UTC):** 2026-07-28  
**Authority:** Binding quality rules under [`DECISION_PLAYBOOKS_CONSTITUTION_V1.md`](./DECISION_PLAYBOOKS_CONSTITUTION_V1.md) (**DP-001…DP-005** · **PBL-001** · **PBL-002**).  
**Non-goals:** No UI. No production copy. No scoring product. No implementation.

A playbook instance that fails any **Reject** rule **must not publish**.  
Diagnosis may still show when evidence is insufficient (**DP-004**) or when **PBL-001** validation fails.

**Preference (PBL-001):** rather **no playbook** than a **weak playbook**.

---

## 0. PBL-001 Playbook Validation (all must be YES)

Runs after Diagnosis → Evidence → Execution Readiness. Failure → **Diagnosis only**; playbook suppressed.

| # | Question | Maps to |
|---|----------|---------|
| **1** | Is the business task specific? | Q-05 / S-rules |
| **2** | Can the merchant execute it immediately? *(when readiness = READY)* | Q-07 / E-rules |
| **3** | Does the merchant know exactly where execution happens? | Q-06 / E-01 |
| **4** | Is the playbook supported by sufficient evidence? | Q-04 / D-rules / PBL-002 Minimum Evidence |
| **5** | Can CartFlow verify the outcome? | Q-08 / V-rules |
| **6** | Is the expected business result measurable? | Q-08 / V-01 |
| **7** | Would two different experts likely recommend the same action from the same evidence? (**Consistency Test**) | **C-01** below |

---

## 1. Publish prerequisites (all must pass)

| # | Rule | Fail condition |
|---|------|----------------|
| **Q-01** | **Quality Law** — answers What / Why (diagnosis) / Where / Whether now | Any of the four missing |
| **Q-02** | **Structure** — Task → Reason → Location → Readiness → Expected Result | Extra peer layers replacing the five; reordered core |
| **Q-03** | **Family membership** — exactly one Catalog family | Ad-hoc or multi-family mashup |
| **Q-04** | **Evidence minimum** — family bar + PBL-002 Minimum Evidence | Below bar → no playbook |
| **Q-05** | **Specificity** — applicable object / cohort / stage / platform named | Generic advice |
| **Q-06** | **Execution clarity** — merchant need not ask what / where / which screen | Ambiguous task or locus |
| **Q-07** | **Readiness honesty** — exactly one EM-001 state; meets PBL-002 Minimum Readiness when publishing full playbook | Fake READY; methodology when not allowed |
| **Q-08** | **Validation** — expected result + reality validation metric | No measurable success condition |
| **Q-09** | **Reusability** — same playbook identity for all surfaces | Page-local rewrite into abstract advice |
| **Q-10** | **Reading budget** — ≤15 seconds to grasp What / Why / Where / Whether / Verify | Essay, report, or BI dump |
| **Q-11** | **PBL-001** — all seven validation questions YES | Any NO → suppress playbook |
| **Q-12** | **PBL-002** — complete internal publication metadata for the family | Incomplete metadata → family cannot emit |
| **Q-13** | **Minimum Confidence** — instance confidence ≥ family Minimum Confidence | Below floor → suppress playbook |

---

## 2. Language rules

### 2.1 Reject — abstract / filler (non-exhaustive)

Reject if the **Business Task** is only:

- Review conversion.  
- Improve checkout.  
- Optimize product.  
- Investigate customers.  
- Check shipping.  
- Review funnel.  
- Improve experience.  
- Look into performance.  
- Consider optimizing…  
- Monitor the situation.  

Reject verbs without a named object: *review / improve / optimize / investigate / check / consider* alone.

### 2.2 Require — diagnostic task shape

Accept only when task language (instance-level, not this doc’s copy) includes:

| Required | Example pattern (illustrative — not production copy) |
|----------|------------------------------------------------------|
| **Action verb + object** | Open [named settings / message / product] |
| **Causal because** | …because [diagnosis fact] |
| **Bounded scope** | …for [cohort / threshold / stage / product] |

### 2.3 Reject — analysis masquerading as task

- Long cause lists without one task  
- “Insights” or “findings” as the commitment  
- KPI commentary as the Business Task  
- Asking the merchant to collect evidence or diagnose  

CartFlow owns observation, evidence, diagnosis, confidence, readiness, validation.  
Merchant owns commercial judgement and execution.

---

## 3. Specificity rules

| # | Rule | Reject if |
|---|------|-----------|
| **S-01** | Object | No object when the family is object-bound (product, message, setting) |
| **S-02** | Cohort | Cohort-bound families omit which customers |
| **S-03** | Stage | Funnel-bound families omit checkout / shipping / payment stage |
| **S-04** | Platform locus | Type B tasks omit which platform surface class (settings domain) |
| **S-05** | Umbrella collapse | `PF-LOW-CONV` or unbound `PF-HIGH-INTEREST` published without subordinate concrete task |

**Generic advice is always a reject.**

---

## 4. Execution & readiness rules

| # | Rule | Reject if |
|---|------|-----------|
| **E-01** | Single primary location | Location is “everywhere”, blank, or contradictory |
| **E-02** | Domain match | Task implies Platform work but location says CartFlow (or reverse) without override |
| **E-03** | EM-001 | READY while evidence below family minimum |
| **E-04** | Methodology gate | Full how-to presented under NEEDS_MORE_EVIDENCE / BLOCKED as if READY |
| **E-05** | External honesty | Type C / EXTERNAL_DEPENDENCY claimed as CartFlow-controlled execution |
| **E-06** | No investigate CTA | Commitment tells merchant to investigate / gather evidence / diagnose |

---

## 5. Data dependency rules

| # | Rule | Behaviour |
|---|------|-----------|
| **D-01** | Below evidence minimum | **Do not generate playbook** — diagnosis / insufficiency only |
| **D-02** | Conflicting evidence | Prefer honest conflict / wait — do not publish a speculative task |
| **D-03** | No filler task | Never invent a playbook to avoid an empty card |
| **D-04** | Diagnosis ≠ playbook | Valid diagnosis alone never publishes a playbook (**PBL-001**) |

---

## 5b. Consistency Test

| # | Rule | Reject if |
|---|------|-----------|
| **C-01** | **Consistency Test** — two competent experts would likely recommend the same action from the same evidence | Action is speculative, taste-driven, or could reasonably fork into incompatible tasks without further evidence |

---

## 6. Reality validation rules

| # | Rule | Reject if |
|---|------|-----------|
| **V-01** | Class present | No validation class |
| **V-02** | Linked to task | Validation unrelated to the Business Task |
| **V-03** | Observation not click | “Success” = merchant clicked a link, with no business reality check |
| **V-04** | EM-002 alignment | Decision closed permanently Active with no validation path |

Allowed validation classes (illustrative set — extend only by amendment):

- Higher conversion  
- Lower abandonment  
- Higher return-to-checkout rate  
- Higher recovery  
- Higher purchase completion  

---

## 7. Surface consumption rules

| # | Rule | Reject if |
|---|------|-----------|
| **R-01** | Shared identity | Home / Workspace / Knowledge / Brief / Future AI invent divergent tasks for the same decision |
| **R-02** | Altitude only | Teaser omits so much that What / Where / Whether are unknowable **and** the full playbook is never available on an executive surface |
| **R-03** | No page-local copy engine | A surface generates recommendation language outside the playbook instance |

Editorial altitude may shorten; it may not mutate the task into abstract advice.

---

## 8. Fast reject checklist (reviewer)

Use in order — first fail wins:

1. Is there a **Business Task** (not insight)?  
2. Is **Why** tied to a named diagnosis?  
3. Is **Where** exactly one location?  
4. Is **Readiness** honest (EM-001) and ≥ family Minimum Readiness for full playbook?  
5. Is **evidence** ≥ family minimum?  
6. Is **confidence** ≥ family Minimum Confidence?  
7. Is **specificity** present for this family?  
8. Would the merchant still ask *what / where / which screen*?  
9. Is **validation** defined and measurable?  
10. Does the **Consistency Test** pass?  
11. Is language free of forbidden abstracts?  
12. Is family **PBL-002** metadata complete (internal)?  
13. Is the same playbook reusable across surfaces?

If all pass → eligible to publish (subject to saturation / Primary selection elsewhere).

---

## 9. Relationship to Execution Methodology

| Concern | Owner |
|---------|--------|
| Whether a playbook may exist | This pack (Quality + Catalog + DP-004 + **PBL-001** + **PBL-002**) |
| Six answers (what/why/where/how/avoid/verify) when READY | Execution Methodology V1 |
| After-action loop | EM-002 |
| Card / Workspace presentation | Decision Cards / Workspace Constitutions — **consume**, do not rewrite |
| Publication metadata | **PBL-002** — engine only; never merchant-facing |

---

## 10. STOP

Quality Rules are the publish gate only.

**No implementation. No UI. No production copy.**

Await constitutional approval with the rest of this pack.
