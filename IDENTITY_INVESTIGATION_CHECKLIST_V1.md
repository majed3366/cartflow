# Identity Investigation Checklist V1

**Status:** Proposed — companion to Identity Foundation Architecture V1  
**Date (UTC):** 2026-07-19  
**Authority:** [`IDENTITY_FOUNDATION_ARCHITECTURE_V1.md`](IDENTITY_FOUNDATION_ARCHITECTURE_V1.md)  
**Use:** Mandatory before Identity Foundation for any knowledge domain

---

## Purpose

Every new (or newly knowledge-bound) domain must answer these questions **with evidence** before Knowledge Layer or Commercial Intelligence work begins.

Answers must cite: schema/models, services, projections, sample records, simulator/fixture paths, and merchant surfaces.  
**Do not assume. Prove.**

---

## The twelve questions

| # | Question | What “answered” means |
|---|----------|------------------------|
| **1** | What is the canonical identity? | Grain, stable key scheme, tiers/confidence if any |
| **2** | Where is it created? | Exact ingress (widget, webhook, admin, simulator, …) |
| **3** | Where is it normalized? | Module + rules; provider → canonical mapping |
| **4** | Where is it persisted? | Table/columns; mutable vs immutable |
| **5** | Where is it snapshotted? | Historical freeze points; content hash / insert-only rules |
| **6** | Where is it projected? | Read models, slim allowlists, API shapes |
| **7** | Where is it consumed? | Knowledge, Commercial Intel, merchant UI, recovery copy |
| **8** | Can identity silently disappear? | Paths that drop fields without error / honest empty |
| **9** | Can identity silently change? | Updates that rewrite history or swap keys without audit |
| **10** | Can placeholders appear? | Fixture labels, “Product X”, synthetic production names |
| **11** | Can historical data lose identity? | Pre-foundation rows; missing capture cohorts |
| **12** | Can simulation corrupt identity? | Sim/demo writing keys, placeholders, or skipping snapshots |

---

## Required evidence per question

For each question, the investigation must record:

| Field | Required |
|-------|----------|
| Verdict | Yes / No / Conditional |
| Evidence | File path + field/query + sample |
| Failure mode | How it breaks |
| Merchant impact | What the merchant would see |
| Gate implication | Blocks Foundation / blocks Knowledge / OK |

---

## Investigation output template

```markdown
# Identity Investigation — <Domain> V1

**Domain:** …
**Date (UTC):** …
**Investigator:** …
**Status:** Complete | Blocked

## Canonical identity (Q1)
…

## Creation (Q2)
…

## Normalization (Q3)
…

## Persistence (Q4)
…

## Snapshots (Q5)
…

## Projection (Q6)
…

## Consumption (Q7)
…

## Silent disappearance (Q8)
…

## Silent change (Q9)
…

## Placeholders (Q10)
…

## Historical loss (Q11)
…

## Simulation corruption (Q12)
…

## Classification summary
| Class | Present? | Notes |
|-------|----------|-------|
| Exists; UI-only gap | | |
| Exists; missing from projections | | |
| Lost in provider normalization | | |
| Not persisted in snapshots | | |
| Disconnected from related truth | | |
| Knowledge does not consume | | |
| Fixture/placeholder labels | | |
| Historical pre-foundation gaps | | |

## Recommendation
- Foundation may proceed: Yes / No
- Knowledge blocked until: …
```

---

## Exit criteria for Investigation stage

Investigation is **complete** only when:

1. All twelve questions have evidence-backed answers  
2. Placeholder / fixture contamination paths are named  
3. Silent degrade paths are named  
4. Simulator compatibility is assessed  
5. A Foundation map draft can be filled without guessing  

Investigation is **not** permission to build Knowledge.  
Next stage: Identity Foundation artefacts + Readiness Checklist.

---

## First completed investigation

**Product Identity** — [`PRODUCT_IDENTITY_AVAILABILITY_INVESTIGATION_V1.md`](PRODUCT_IDENTITY_AVAILABILITY_INVESTIGATION_V1.md)  
Mapped into Foundation: [`PRODUCT_IDENTITY_FOUNDATION_MAP_V1.md`](PRODUCT_IDENTITY_FOUNDATION_MAP_V1.md)
