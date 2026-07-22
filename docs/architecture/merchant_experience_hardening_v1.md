# CartFlow Merchant Experience Hardening V1 (MEH)

**Status:** Hardening / readiness phase (architecture + runtime)  
**Date (UTC):** 2026-07-22  
**Baseline:** Reality Validation V2 readiness **72 / 100**  
**Target:** Highest achievable readiness under current architecture (~85–90)  
**Explicitly out of scope:** Redesign, features, new layers, Knowledge rewrite, Guidance engines, SCF input expansion, Truth/CIS changes, AI, cosmetic score inflation

> **Law:** Every remaining issue is Category A (fix with existing capabilities) or Category B (Capability Gap).  
> No guessing. No hidden feature work. No unresolved issue left unclassified.

---

## 0. Mission

Maximize merchant experience quality using the architecture that already exists.

```text
Truth → Evidence → CIS → Knowledge → Guidance → Surface Composition → MEIF → Pages
```

Do not insert new architectural layers.

---

## 1. Phase 1 — Findings classification

Canonical registry: `FINDINGS_CLASSIFICATION_V1` in `merchant_experience_hardening_v1.py`.

| Category | Meaning | Action |
|----------|---------|--------|
| A | Solvable with existing stack | Must fix now |
| B | Requires new platform capability | Document Capability Gap only |

Capability Gap Register: [`merchant_experience_capability_gap_register.md`](merchant_experience_capability_gap_register.md)

---

## 2. Category A hardening (what MEH does)

| Hardening | Layer |
|-----------|-------|
| Trust class on every visible item (`fact` / `observation` / `interpretation` / `recommendation` / `uncertainty`) | MEIF presentation |
| Ops fact cards from Merchant Operational State when SCF attention empty | MEIF bridge |
| Map presentation-bearing items into Guidance highlights | MEIF presentation |
| Demote `monitor_*` guidance to observation (not recommendation) | MEIF presentation filter |
| Dedupe knowledge highlights by type/family | MEIF presentation |
| Suppress setup theatre when durable carts exist | Pages + MEIF flag |
| Chronology cue (`as_of` + assembly window) without redesigning Time Authority | MEIF presentation |
| Carts attention answered by ops facts; forbid false please-wait | MEIF Carts |
| Communication ready package; not Settings loading | MEIF Communication |
| Legacy home/setup composers gated when MEIF ok | Page consumers |

---

## 3. Category B (not implemented)

See Capability Gap Register CG-MEH-01…06:

- Time Authority consumer binding  
- Operational Truth as SCF input  
- Cart list projection  
- Communication follow-up projection  
- Guidance product policy / eligibility  
- Setup lifecycle ownership rewrite  

---

## 4. Runtime

| Concern | Contract |
|---------|----------|
| Flag | `CARTFLOW_MERCHANT_EXPERIENCE_HARDENING_V1` (default **on**) |
| Applied by | `apply_hardening_to_meif_report_v1` inside MEIF generate |
| Probe | `GET /dev/merchant-experience?store=demo` |
| New probe fields | `readiness_score`, `unresolved_findings`, `capability_gaps`, `trust_warnings`, `legacy_leakage_count`, `hardening_status`, `chapter_outcome` |

---

## 5. Exit gate

| Outcome | Condition |
|---------|-----------|
| **Chapter Closed** | Readiness ~85–90; remaining issues exclusively Capability Gaps |
| **Chapter Reopened** | Further Category A improvements still possible without new capabilities |

---

## 6. STOP / Final principle

This phase is not about making the score look better. It is about proving the current architecture has reached its natural limit. Only after that proof exists should CartFlow move to its next architectural chapter.
