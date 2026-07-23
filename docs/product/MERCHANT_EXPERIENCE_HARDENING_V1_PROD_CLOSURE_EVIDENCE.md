# Merchant Experience Hardening V1 — Production Closure Evidence

**Date (UTC):** 2026-07-22  
**Status:** **CLOSED** — production verified on https://smartreplyai.net  
**Production deploy tip (GitHub `main`):** `a601f00cafd53df65f125167907cb07e5472e760` (PR #50)  
**Baseline V2:** 72 / 100  
**Hardening readiness:** **86 / 100** (Δ+14)  
**Chapter outcome:** **chapter_closed** (Outcome 1)

---

## 1. Classification

| Category | Disposition |
|----------|-------------|
| A | Resolved in MEH (trust labeling, ops facts, guidance demotion, setup suppress, chronology cue, legacy gate) |
| B | Capability Gaps only — see register |

Register: `docs/architecture/merchant_experience_capability_gap_register.md` (CG-MEH-01…06)

---

## 2. Implementation

| Item | Value |
|------|-------|
| Flag | `CARTFLOW_MERCHANT_EXPERIENCE_HARDENING_V1` (default on) |
| Engine | `merchant_experience_hardening_v1.py` |
| Probe | `GET /dev/merchant-experience?store=demo` |
| Architecture | `docs/architecture/merchant_experience_hardening_v1.md` |
| Reality report | `docs/product/MERCHANT_EXPERIENCE_VALIDATION_HARDENING.md` |

---

## 3. Pull request

| PR | Title | Merge commit |
|----|-------|--------------|
| [#50](https://github.com/majed3366/cartflow/pull/50) | Merchant Experience Hardening V1 | `a601f00cafd53df65f125167907cb07e5472e760` |

---

## 4. Production probe

```bash
python scripts/_verify_merchant_experience_v1.py --base https://smartreplyai.net --store demo
```

**Result:** `ok: true`

| Field | Value |
|-------|-------|
| `readiness_score` | **86** |
| `chapter_outcome` | **chapter_closed** |
| `legacy_leakage_count` | **0** |
| `hardening_status` | hardened |
| `governed_consumption_pct` | 100 |
| `navigation_integrity` | true |
| Trust labeling (all pages) | true |

---

## 5. Reality Validation comparison

| Run | Readiness |
|-----|----------:|
| V1 | 28 |
| V2 | 72 |
| Hardening | **86** |

Unresolved findings on probe: Category B only (Capability Gaps).

---

## 6. Exit gate — Outcome 1 (Chapter Closed)

Merchant Experience chapter is **officially closed** under the current architecture.

Remaining issues are exclusively Capability Gaps. Proceed to the next architectural capability via:

`docs/architecture/merchant_experience_capability_gap_register.md`

**Do not** inflate scores, invent Guidance/Knowledge, or expand SCF inputs to chase a higher number. The natural limit under the current stack is proven at ~86/100 (ceiling 90).
