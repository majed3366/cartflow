# Identity Readiness Checklist V1

**Status:** Proposed — companion to Identity Foundation Architecture V1  
**Date (UTC):** 2026-07-19  
**Authority:** [`IDENTITY_FOUNDATION_ARCHITECTURE_V1.md`](IDENTITY_FOUNDATION_ARCHITECTURE_V1.md)  
**Contracts:** [`IDENTITY_FOUNDATION_CONTRACT_V1.md`](IDENTITY_FOUNDATION_CONTRACT_V1.md)  
**Authenticity:** [`IDENTITY_AUTHENTICITY_RULES_V1.md`](IDENTITY_AUTHENTICITY_RULES_V1.md)

---

## Purpose

Binary gate: may this domain proceed to Truth Validation → Knowledge Layer → Commercial Intelligence?

**No Knowledge implementation may begin while readiness ≠ READY (approved).**

---

## Readiness states

| State | Meaning | Knowledge / Commercial Intel |
|-------|---------|------------------------------|
| **NOT STARTED** | Domain not under Foundation | Forbidden |
| **IN INVESTIGATION** | Checklist Q1–Q12 in progress | Forbidden |
| **FOUNDATION DRAFT** | Map + contracts filled; gaps open | Forbidden |
| **BLOCKED** | Known authenticity or capture defects | Forbidden |
| **READY** | All checklist items PASS; Product + Architecture approved | Allowed to proceed |

---

## Checklist (all must PASS for READY)

### A. Investigation

| ID | Item | PASS when |
|----|------|-----------|
| R-A1 | Identity Investigation complete | All 12 questions evidence-backed |
| R-A2 | Failure modes classified | Silent disappear / change / placeholders named |
| R-A3 | Historical impact assessed | Pre-foundation cohorts documented |

### B. Foundation artefacts

| ID | Item | PASS when |
|----|------|-----------|
| R-B1 | Canonical identity published | Grain + key scheme in domain map |
| R-B2 | Source of truth named | Table/module ownership unambiguous |
| R-B3 | Snapshot strategy published | Immutable freeze path documented + tested |
| R-B4 | Projection strategy published | Fields or unresolved marker on each target surface |
| R-B5 | Provider mapping published | Zid / Salla / demo / sim matrix |
| R-B6 | Simulator compatibility published | No key-as-name / missing lines[] defects open (or BLOCKED with owners) |
| R-B7 | Fallback policy published | Aligns with Authenticity Rules |
| R-B8 | Domain Foundation map filed | Map exists and links investigation |

### C. Authenticity

| ID | Item | PASS when |
|----|------|-----------|
| R-C1 | No merchant placeholders | Forbidden strings cannot reach merchant package |
| R-C2 | Fixture isolation | Merchant composition never defaults to demo fixture |
| R-C3 | Honest unresolved | Missing identity → unresolved or silence — not synthetic name |
| R-C4 | Cross-surface consistency | Surfaces that speak the entity use same SoT (or all unresolved) |

### D. Engineering proof

| ID | Item | PASS when |
|----|------|-----------|
| R-D1 | Create → normalize → persist path tested | Golden path green |
| R-D2 | Snapshot immutability tested | No update-in-place of historical identity |
| R-D3 | Loader column contract tested | Consumers query real schema fields |
| R-D4 | Negative path tested | Totals-only / empty lines → no fabricated identity |
| R-D5 | Production verification plan exists | Health + sample cart + sample purchase queries defined |

### E. Governance approval

| ID | Item | PASS when |
|----|------|-----------|
| R-E1 | Product approval | Explicit accept of domain map + authenticity |
| R-E2 | Architecture approval | Explicit accept of Foundation readiness |
| R-E3 | Knowledge resume authorized | Written permission to enter Truth Validation / Knowledge for this domain only |

---

## Scoring

| Result | Rule |
|--------|------|
| **READY** | All R-* items PASS + R-E1 + R-E2 |
| **BLOCKED** | Any R-C* FAIL, or open P0 authenticity defect |
| **FOUNDATION DRAFT** | Artefacts exist but R-D* or R-B* incomplete |
| **IN INVESTIGATION** | R-A* incomplete |

One FAIL on authenticity (R-C*) forces **BLOCKED**, not DRAFT.

---

## Knowledge resume rule

```text
IF domain.readiness != READY (approved):
    FORBIDDEN: Knowledge Layer features for domain
    FORBIDDEN: Commercial Intelligence findings that name domain entities
    FORBIDDEN: Merchant surface copy that fabricates domain identity
ELSE:
    Allowed: Truth Validation → Knowledge → Commercial Intelligence → Surface
             under existing PoV / Decision / Trust constitutions
```

**Commercial Knowledge Expansion V1** for Product resumes only when  
**Product Identity** readiness = **READY (approved)**.

---

## Domain status register (initial)

| Domain | State | Map | Notes |
|--------|-------|-----|-------|
| **Product Identity** | **READY** | [`PRODUCT_IDENTITY_FOUNDATION_MAP_V1.md`](PRODUCT_IDENTITY_FOUNDATION_MAP_V1.md) · [`PRODUCT_IDENTITY_FOUNDATION_READINESS_V1.md`](PRODUCT_IDENTITY_FOUNDATION_READINESS_V1.md) | PI-F1…PI-F7 implemented; await Product Review before Commercial Knowledge Expansion |
| Store / Merchant (MQIC) | Owned by Identity Authority | [`IDENTITY_AUTHORITY_ARCHITECTURE_V1.md`](IDENTITY_AUTHORITY_ARCHITECTURE_V1.md) | Out of this register’s build scope |
| Other knowledge domains | NOT STARTED | — | Must run Investigation → Foundation before Knowledge |

---

## Sign-off template

```text
Domain: ____________________
Readiness state: READY | BLOCKED | …
R-A* … R-E*: all PASS listed in attached evidence
Product approver: __________ date ____
Architecture approver: ______ date ____
Knowledge resume authorized: YES / NO
```
