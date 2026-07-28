# Collector Contract Template V1

**Authority:** Collector Constitution V1 — Article III.  
**Instruction:** Copy this file per Collector proposal. Incomplete contracts fail Constitution Validation.  
**Status of this file:** Blank constitutional template — not a Collector proposal.

---

## 1. Collector Name

- **id:** `(canonical_snake_case)`
- **title:** `(Human Title)`

---

## 2. Business Purpose

`(One clear purpose: why merchants / diagnosis need this.)`

---

## 3. Observable

- **canonical_key:** `(must match Evidence Expansion catalog or approved successor)`
- **definition:** `(Exactly what is being observed — one canonical definition)`
- **separates_causes:** `(list)`
- **diagnosis_families:** `(list)`

---

## 4. Observation Trigger

`(When collection begins.)`

---

## 5. Observation End

`(When collection stops.)`

---

## 6. Evidence Produced

`(Exactly which evidence becomes available to diagnosis.)`

---

## 7. Evidence Gap Closed

- **gap_id / registry ref:** `(registered Evidence Gap)`
- **how reduced:** `(what changes in the gap)`

---

## 8. Diagnosis Improved

- **family / diagnosis:** `(named)`
- **accuracy improvement:** `(what becomes distinguishable that was not)`

---

## 9. Recommendations Enabled

| Recommendation | Today (without evidence) | After (with evidence) |
|----------------|--------------------------|------------------------|
| `(name)` | suppressed / unsafe | safer when… |

---

## 10. Provider Capability

| Provider | Status | Notes |
|----------|--------|-------|
| Zid | Supported / Generic / Unsupported | |
| Salla | Supported / Generic / Unsupported | |
| Shopify | Supported / Generic / Unsupported | |
| Generic | Yes / No | e.g. widget-only |
| Unsupported cases | `(list)` | degrade honestly — never guess |

---

## 11. Performance Cost

| Dimension | Bound / estimate | Notes |
|-----------|------------------|-------|
| CPU | | |
| Database | | |
| Network | | |
| Storage | | |

**Merchant request path:** Forbidden (must be None / N/A).  
**Execution plane:** Background only.

---

## 12. Retention

- **TTL / retention window:**
- **Aggregation / anonymization:**
- **Deletion rules:**

---

## 13. Privacy

- **Customer information collected:**
- **Minimization:**
- **PII / identifiers:**

---

## 14. Failure Behaviour

| Failure mode | Behaviour |
|--------------|-----------|
| Collection fails | |
| Partial / late events | |
| Provider unsupported | degrade honestly — never emulate |

Must not invent observations. Must not block merchant UI.

---

## 15. Reality Validation

- **Method:**
- **Fixtures / Living Store / provider truth:**
- **Pass criteria:**

---

## Evidence ROI (Constitution Article IV)

| Metric | Baseline | Target | Measurement method |
|--------|----------|--------|--------------------|
| Diagnosis improvement | | | |
| Reduction of `insufficient_evidence` | | | |
| Reduction of `conflicting_evidence` | | | N/A if justified |
| Increase in supported diagnoses | | | |
| Recommendation accuracy | | | |
| Merchant usefulness | | | |

**ROI measurable?** Yes / No — if No, **do not approve**.

---

## Lifecycle attestation

| Stage | Owner | Date | Pass |
|-------|-------|------|------|
| Need | | | ☐ |
| Evidence Gap | | | ☐ |
| Collector Proposal | | | ☐ |
| Architecture Review | | | ☐ |
| Collector Constitution Validation | | | ☐ |
| Implementation | | | ☐ *(after Validation)* |
| Reality Validation | | | ☐ |
| Diagnostic Impact Measurement | | | ☐ |
| Production | | | ☐ |

---

## Required tests (plan)

| Category | Coverage plan | Status |
|----------|---------------|--------|
| Contract tests | | ☐ |
| Provider tests | | ☐ |
| Identity tests | | ☐ |
| Performance tests | | ☐ |
| Failure tests | | ☐ |
| Reality Validation tests | | ☐ |

---

## Success statement

`(This Collector is successful only when it measurably improves diagnosis quality without materially degrading platform performance.)`

---

## Explicit non-goals

- Not random collection  
- Not “may need later”  
- Not merchant-path execution  
- Not provider field coupling in diagnosis  

