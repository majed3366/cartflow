# CartFlow Merchant Evidence Registry Normalization V1

**Date (UTC):** 2026-07-04  
**Status:** Implemented — presentation architecture  
**Governance:** Merchant Evidence Registry Foundation; Proof of Value PG-3, PG-8

---

## Architectural principle

> **One evidence_id → one evidence origin → one merchant meaning.**

Registry entries are semantically atomic. No entry may combine multiple evidence sources or business meanings (no «أو», no fallback wording).

---

## Normalization applied (v1)

| Before | After | Label |
|--------|-------|-------|
| `customer_response` | `hesitation_reason` | سبب التردد |
| *(split)* | `customer_reply` | رد العميل |

**Tier-0 mapping:** `reason_capture` → `hesitation_reason` (widget hesitation capture).

**Claim mapping:** KL hesitation insights → `hesitation_reason`.

**Proof Surface:** reason-tag «why we know» line → `hesitation_reason` label from registry.

**`store_activity` description** normalized to a single meaning (removed multi-source list in maintainer description).

---

## Registry contract (unchanged shape)

Each entry defines:

- stable `evidence_id`
- merchant `label_ar`
- `evidence_origin` (`store` | `platform`)
- `description_ar` (maintainer)
- `eligible_domains`
- optional `tier0_keys`

---

## Presentation

All surfaces resolve labels through `merchant_evidence_registry_v1.py` only. No merged meanings in UI.

---

## Regression

No changes to proof logic, KL generation, confidence, Purchase/Lifecycle/Provider Truth, or dashboard behavior.

Tests: `tests/test_merchant_evidence_registry_v1.py` (atomic label gate), existing claim/proof suites.
