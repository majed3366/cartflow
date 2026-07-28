# Compression Rules V1

**Status:** Architecture only — binding compression rules.  
**Date (UTC):** 2026-07-28  
**Authority:** Under [`EXECUTIVE_COMPRESSION_CONSTITUTION_V1.md`](./EXECUTIVE_COMPRESSION_CONSTITUTION_V1.md) (**EC-001…EC-005**).  
**Non-goals:** No UI. No production copy. No implementation.

---

## 1. Default posture

| Default | Rule |
|---------|------|
| **Hide** | Platform knowledge (evidence chains, gates, confidence math, collectors, validation logic, PBL metadata) |
| **Show** | Minimum for What / Why / Can I act now / Where (when applicable) |
| **Prefer silence** | Omit a sentence rather than decorate |

CartFlow would rather show a short honest decision than a complete internal tour.

---

## 2. Keep rules (merchant-visible)

Keep only if the sentence answers one of:

| Keep class | Answers |
|------------|---------|
| **K-TASK** | What should I do? (or honest: not ready / diagnosis-only) |
| **K-WHY** | Why? (one causal line from diagnosis) |
| **K-NOW** | Can I act now? (readiness in merchant language) |
| **K-WHERE** | Where? — **only when applicable** (execution location needed to act) |
| **K-VERIFY** | Optional one line: how CartFlow will know it worked — **only** when it increases commitment quality without becoming a report |

If a sentence answers “how CartFlow works,” **remove it**.

---

## 3. Hide rules (always internal)

| Hide class | Examples |
|------------|----------|
| **H-EVIDENCE** | Evidence chains, sample sizes, collector names, gap registries |
| **H-CONF** | Confidence %, floors, PBL-002 thresholds |
| **H-GATE** | Publication gates, playbook validation ledgers, consistency-test logs |
| **H-ROUTE** | Routing tables, deep-link strategy, engine path IDs |
| **H-DIAG-TRACE** | Competing causes list, reasoning graphs, ORV internals |
| **H-META** | Family IDs, review cadence, supported-platform matrices as UI |
| **H-SYSTEM** | “We ran…”, “Our model…”, “Pipeline step…” |

---

## 4. Altitude rules

| Altitude | Use | Allowed merchant content |
|----------|-----|--------------------------|
| **Teaser** | Home, Notifications, Brief headlines | What + Why (shortest) + Whether now; Where only if one word locus helps |
| **Commit** | Workspace Primary, actionable Brief body | Full Compression Law answers; Expected result if load-bearing |
| **Reference** | Knowledge (when decision-bound) | Same language; no expansion into evidence museum |
| **Summary** | Weekly / Monthly | Aggregated decisions still obey Compression Law — not analytics essays |

Altitude may **shorten**. It may not **mutate** the task into abstract advice or invent a playbook.

---

## 5. Honesty under compression

| Situation | Compressed output |
|-----------|-------------------|
| Playbook suppressed (**PBL-001**) | Diagnosis + “not ready to act” / wait posture — **no fake task** |
| NEEDS_MORE_EVIDENCE | Why CartFlow is waiting — not a methodology dump |
| BLOCKED | The block in one line + what is blocked — not prerequisite encyclopedia |
| EXTERNAL_DEPENDENCY | Where external work lives — not provider lecture |
| No decision | Honest empty / no action — not filler insight |

---

## 6. Over-explain reject rules

Reject (re-compress) if:

| # | Symptom |
|---|---------|
| **R-01** | Requires scrolling to understand the decision |
| **R-02** | Exceeds ~15 seconds to grasp What / Why / Whether / Where |
| **R-03** | Opens with system explanation |
| **R-04** | Lists multiple competing actions |
| **R-05** | Pastes evidence as main content |
| **R-06** | Repeats the same Why in different words |
| **R-07** | Shows confidence math or gate language |
| **R-08** | Generic abstracts (“improve conversion”) — Playbook Quality still applies |
| **R-09** | Any sentence can be removed without reducing decision quality |

---

## 7. Compression Quality Test (mandatory)

Before any surface publish of a decision presentation:

1. Understood in **15 seconds**? → must be **YES**  
2. Scroll required to understand? → must be **NO**  
3. Business question answered immediately? → must be **YES**  
4. Every sentence load-bearing? → must be **YES**

Fail any → **do not publish** that presentation; re-compress.

---

## 8. Pipeline position

```
Diagnosis / Evidence / Readiness / Playbook (upstream)
        ↓
Executive Compression Engine
        ↓
Surface render (Home / Workspace / Knowledge / Briefs / Notifications / Future AI)
```

Compression **never** bypasses Playbook Validation or invents tasks.

---

## 9. STOP

Rules only. **No UI. No implementation.**

Await approval with the Constitution pack.
