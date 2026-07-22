# Merchant Experience Hardening V1 — Production Closure Evidence

**Date (UTC):** 2026-07-22  
**Status:** PENDING live probe after deploy (local hardening complete)  
**Baseline V2:** 72 / 100  
**Hardening local readiness:** **86 / 100** (Δ+14)  
**Chapter outcome (local):** **chapter_closed**

---

## 1. Classification

| Category | Count | Disposition |
|----------|------:|-------------|
| A | all solvable findings in `FINDINGS_CLASSIFICATION_V1` | Resolved in MEH |
| B | H03, D02, C01, C02, M02, K03, G01 (+ lifecycle/policy portions) | Capability Gaps CG-MEH-01…06 |

Register: `docs/architecture/merchant_experience_capability_gap_register.md`

---

## 2. Implementation

| Item | Value |
|------|-------|
| Flag | `CARTFLOW_MERCHANT_EXPERIENCE_HARDENING_V1` (default on) |
| Engine | `merchant_experience_hardening_v1.py` |
| Probe | `GET /dev/merchant-experience?store=demo` (+ readiness / gaps / leakage) |
| Architecture | `docs/architecture/merchant_experience_hardening_v1.md` |
| Reality report | `docs/product/MERCHANT_EXPERIENCE_VALIDATION_HARDENING.md` |

---

## 3. Local Reality Validation (Hardening)

| Run | Readiness |
|-----|----------:|
| V1 | 28 |
| V2 | 72 |
| Hardening | **86** |

- `legacy_leakage_count`: 0  
- `chapter_outcome`: chapter_closed  
- Unresolved findings: Category B only  

---

## 4. Production verification (fill after deploy)

```bash
python scripts/_verify_merchant_experience_v1.py --base https://smartreplyai.net --store demo
python scripts/merchant_experience_validation_hardening.py --prod-only
```

| Field | Expected | Actual |
|-------|----------|--------|
| `ok` | true | _pending_ |
| `readiness_score` | ≥ 85 | _pending_ |
| `legacy_leakage_count` | 0 | _pending_ |
| `hardening_status` | hardened* | _pending_ |
| `chapter_outcome` | chapter_closed | _pending_ |

**Merge tip:** _pending_

---

## 5. Exit gate — Outcome 1 (Chapter Closed)

Merchant Experience chapter is closed under the current architecture when production probe confirms the local result. Remaining work proceeds only via Capability Gaps (next architectural chapter).
