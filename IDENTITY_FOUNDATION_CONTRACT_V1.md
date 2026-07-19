# Identity Foundation Contract V1

**Status:** Proposed — companion to Identity Foundation Architecture V1  
**Date (UTC):** 2026-07-19  
**Authority:** [`IDENTITY_FOUNDATION_ARCHITECTURE_V1.md`](IDENTITY_FOUNDATION_ARCHITECTURE_V1.md)  
**Authenticity:** [`IDENTITY_AUTHENTICITY_RULES_V1.md`](IDENTITY_AUTHENTICITY_RULES_V1.md)

---

## Purpose

Binding contracts that every domain Identity Foundation must satisfy.  
Future Knowledge and Commercial Intelligence **implement** these contracts; they do not redefine them.

---

## IF principles (permanent)

| # | Principle | It is failing when… |
|---|-----------|---------------------|
| **IF-P1** | **Identity Before Knowledge** | Knowledge/Commercial Intel ships for a domain without Foundation READY |
| **IF-P2** | **One Canonical Identity Per Grain** | Two modules invent competing keys for the same entity |
| **IF-P3** | **Source of Truth Is Named** | Identity “comes from JSON somewhere” with no owner |
| **IF-P4** | **History Is Snapshotted** | Past facts are mutated when current catalog changes |
| **IF-P5** | **Projection Is Explicit** | Surfaces omit identity without an honest unresolved state |
| **IF-P6** | **Failure Is Visible** | Loaders catch exceptions and return empty/fake without observability |
| **IF-P7** | **Simulation Obeys Production Identity Rules** | Sim writes keys/placeholders merchants would never accept as real |
| **IF-P8** | **Authenticity Before Coverage** | Fake identity preferred over “unavailable” to fill a card |

---

## IF contracts (testable)

### IF-1 — Canonical identity declared

| Field | Rule |
|-------|------|
| **Requirement** | Domain publishes canonical grain + stable identity key scheme |
| **Owner** | Domain Foundation map |
| **Verification** | Map § Canonical identity reviewed; key scheme documented |
| **Risk if violated** | Duplicate entities; unjoinable knowledge |

### IF-2 — Creation path owned

| Field | Rule |
|-------|------|
| **Requirement** | Every creation ingress listed (widget, webhook, admin, sim) |
| **Owner** | Domain engineering owner |
| **Verification** | Investigation Q2 complete with file paths |
| **Risk if violated** | Identity appears from nowhere / never appears |

### IF-3 — Normalization owned

| Field | Rule |
|-------|------|
| **Requirement** | Single normalizer module (or explicit chain) maps provider → canonical |
| **Owner** | Domain engineering owner |
| **Verification** | Investigation Q3; provider matrix present |
| **Risk if violated** | Same product/customer splits across keys |

### IF-4 — Persistence owned

| Field | Rule |
|-------|------|
| **Requirement** | Durable table(s)/columns named; mutable vs immutable classified |
| **Owner** | Schema + domain service |
| **Verification** | Model + migration + write path tests |
| **Risk if violated** | Identity only in ephemeral payload |

### IF-5 — Snapshot strategy owned

| Field | Rule |
|-------|------|
| **Requirement** | Historical identity freeze defined (when, what fields, insert-only rules) |
| **Owner** | Snapshot service |
| **Verification** | Investigation Q5; immutability tests |
| **Risk if violated** | Past merchant facts rewrite silently |

### IF-6 — Projection strategy owned

| Field | Rule |
|-------|------|
| **Requirement** | Read models / allowlists include identity fields **or** explicit unresolved marker |
| **Owner** | Projection / dashboard read-model owner |
| **Verification** | Investigation Q6; surface contract lists fields |
| **Risk if violated** | Truth exists; merchant never sees it (Carts-class defect) |

### IF-7 — Consumption contract owned

| Field | Rule |
|-------|------|
| **Requirement** | Every consumer (KL, findings, Home, Carts, recovery) listed; each must refuse fabricated identity |
| **Owner** | Consumer module owners |
| **Verification** | Investigation Q7 + authenticity tests |
| **Risk if violated** | Fixture/placeholder contamination |

### IF-8 — No silent disappearance

| Field | Rule |
|-------|------|
| **Requirement** | Missing identity surfaces as observable failure or honest unresolved — not empty success with fake fill |
| **Owner** | Loader + surface admission |
| **Verification** | Investigation Q8; negative-path tests |
| **Risk if violated** | Broken column names → `{}` → fixture fallback |

### IF-9 — No silent identity change

| Field | Rule |
|-------|------|
| **Requirement** | Key changes are versioned/merged under rules; history rows not rewritten |
| **Owner** | Catalog/snapshot services |
| **Verification** | Investigation Q9; merge policy tests |
| **Risk if violated** | Metrics attach to wrong entity |

### IF-10 — No merchant placeholders

| Field | Rule |
|-------|------|
| **Requirement** | Merchant-eligible paths never emit placeholder identities (see Authenticity Rules) |
| **Owner** | Findings / Commercial Intel / surfaces |
| **Verification** | Forbidden-string + fixture-isolation tests |
| **Risk if violated** | «منتج X» authenticity breach |

### IF-11 — Historical honesty

| Field | Rule |
|-------|------|
| **Requirement** | Pre-foundation / capture-gap cohorts documented; no invented backfill |
| **Owner** | Domain Foundation map |
| **Verification** | Investigation Q11; backfill policy |
| **Risk if violated** | Fake reconstruction of old carts |

### IF-12 — Simulator compatibility

| Field | Rule |
|-------|------|
| **Requirement** | Simulator/demo must emit canonical display identity (or mark unresolved) via the same snapshot path production uses |
| **Owner** | Simulator + demo catalog |
| **Verification** | Investigation Q12; sim golden fixtures |
| **Risk if violated** | Knowledge trained on corrupted identity |

### IF-13 — Knowledge admission gate

| Field | Rule |
|-------|------|
| **Requirement** | Knowledge Layer / Commercial Intelligence for the domain requires Readiness = **READY** (approved) |
| **Owner** | Architecture + Product |
| **Verification** | [`IDENTITY_READINESS_CHECKLIST_V1.md`](IDENTITY_READINESS_CHECKLIST_V1.md) |
| **Risk if violated** | Repeat of Product Identity → Commercial Knowledge failure |

### IF-14 — Fixture isolation

| Field | Rule |
|-------|------|
| **Requirement** | Demo/review fixtures may exist only on explicit `/dev` or `source=fixture` paths; never default for merchant production composition |
| **Owner** | Findings engine + Home composition |
| **Verification** | `load_db=True` never returns fixture `loaded_from`; merchant package rejects fixture admission |
| **Risk if violated** | Engine default to `demo_rich_fixture_v1` |

---

## Domain Foundation map minimum fields

Every domain map (see Product Identity map) must include:

1. Canonical identity  
2. Source of truth table  
3. Immutable identifiers  
4. Human-readable identity  
5. Provider mapping matrix  
6. Snapshot strategy  
7. Projection strategy  
8. Historical consistency notes  
9. Simulator compatibility status  
10. Failure modes  
11. Fallback policy  
12. Authenticity guarantees (IF + AR refs)  
13. Investigation crosswalk (Q1–Q12)  
14. Readiness status  

---

## Precedence

If this contract conflicts with a convenience shortcut for shipping Knowledge:

**Identity Foundation wins.**  
Unknown / unresolved wins over fabricated identity.
