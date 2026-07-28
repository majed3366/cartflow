# Storytelling Quality Rules V1

**Status:** Constitution companion — publish / reject gate.  
**Date (UTC):** 2026-07-28  
**Authority:** Under [`DECISION_STORYTELLING_CONSTITUTION_V1.md`](./DECISION_STORYTELLING_CONSTITUTION_V1.md) (**DS-001…DS-009**).  
**Non-goals:** No UI. No implementation. No production copy.

A story unit that fails any **Reject** rule **must not** publish as merchant narrative.

---

## 1. Order gate (DS-001)

| # | Rule | Reject if |
|---|------|-----------|
| **O-01** | Priority before action | Story opens with instruction / CTA |
| **O-02** | Observation is observable only | Diagnosis or recommendation in Observation |
| **O-03** | Meaning ≠ Observation | Meaning repeats Observation or names engines |
| **O-04** | Decision is one sentence / one action | Multi-action or brainstorming |
| **O-05** | Execution only when executable | Button / destination when not READY |
| **O-06** | Sequence intact | Peer blocks outside Story Order |

---

## 2. Completion gate (DS-002)

| # | Rule | Reject if |
|---|------|-----------|
| **C-01** | What happens next | Close is only “العودة للملخص” / “انتهى” |
| **C-02** | Forward posture | No path after wait or after action |

---

## 3. Ranking gate (DS-003)

| # | Rule | Reject if |
|---|------|-----------|
| **R-01** | Workload order | Sorted by type/category/domain label |
| **R-02** | Single Priority 1 | Multiple equal “do first” stories |
| **R-03** | Monitor honesty | Monitor presented as actionable Priority 1 |

---

## 4. Continuity & identity (DS-004 / DS-005)

| # | Rule | Reject if |
|---|------|-----------|
| **I-01** | Same decision | Home / Workspace / Execution fork wording into a different task |
| **I-02** | Recognizable | Merchant would not know it is the same decision |
| **I-03** | No restart | Page re-introduces as a brand-new unrelated story |

---

## 5. Language & engine isolation (DS-006 / DS-007)

| # | Rule | Reject if |
|---|------|-----------|
| **L-01** | Ops director voice | Engineer / system / BI report voice |
| **L-02** | Forbidden labels | Opportunity / Execution / Observation / Diagnostic / Situation / Signal / Operational Meaning / Knowledge (as merchant chrome) |
| **L-03** | Engine leak | ORV, `cs:`, diagnostic IDs, pipeline names, confidence math, collectors, PBL metadata |

---

## 6. Cognitive load (DS-008)

| # | Rule | Reject if |
|---|------|-----------|
| **Q-01** | ≤5 seconds | Decision unit requires effortful reading |
| **Q-02** | Load-bearing lines only | Decorative / repeated sentences |

---

## 6b. Story truth (DS-009)

| # | Rule | Reject if |
|---|------|-----------|
| **T-01** | Reality-sourced | Story is template / scenario / fixed page-order driven |
| **T-02** | Truth before story | Presentation chooses priority independent of evidence |
| **T-03** | No artificial action | Fake Decision/Execution when truth says wait / observe |
| **T-04** | Evolve with truth | Story stays frozen after operational truth changed — or churns without truth change |
| **T-05** | Change explained | Priority shifted vs prior day with no natural “why different today” |

---

## 7. Fast reject checklist

1. Does it open with **why now** (not what to do)?  
2. Is Observation free of diagnosis/recommendation?  
3. Is Meaning impact-only and distinct?  
4. Is Decision exactly one action (or honest wait)?  
5. Is Execution absent when not ready?  
6. Does the story say **what happens next**?  
7. Would the merchant recognize this on every surface?  
8. Any engine / forbidden label visible?  
9. Clear in ≤5 seconds?  
10. Is today’s story driven by **current operational truth** — not a predetermined template (**DS-009**)?

If all pass → eligible for surface altitude (teaser / explain / continue / close).

---

## 8. STOP

**No UI. No implementation.**

Await approval with the Constitution pack.
