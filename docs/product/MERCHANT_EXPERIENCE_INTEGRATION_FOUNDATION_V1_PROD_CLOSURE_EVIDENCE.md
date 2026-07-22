# Merchant Experience Integration Foundation V1 — Production Closure Evidence

**Date (UTC):** 2026-07-22  
**Status:** **CLOSED** — production verified on https://smartreplyai.net  
**Production deploy tip (GitHub `main`):** `8b89fd2bc86b73b118f5d8a55ebe2c95f389f3b0` (PR #48)

---

## 1. Architecture inventory

| Concern | Finding |
|---------|---------|
| Integration Map | `imap_v1` — Home / Decision Workspace / Carts / Communication / Settings |
| Inputs | Surface Composition + Knowledge (translation only) + Merchant Operational State; Guidance via SCF lineage |
| Forbidden | New Knowledge/Guidance/Truth/CIS/SCF rules; page-owned business decisions; cosmetic redesign as substitute |
| Page consumers | `merchant_experience_integration_v1.js` + summary seam `attach_merchant_experience_to_summary_v1` |

---

## 2. Implementation decision

| Decision | Choice |
|----------|--------|
| Bridge role | Canonical Merchant Experience Integration between SCF and pages |
| Flag | `CARTFLOW_MERCHANT_EXPERIENCE_INTEGRATION_V1` (default on) |
| Probe | `GET /dev/merchant-experience?store=demo` |
| Home | Executive / Critical / Operational / Knowledge / Guidance packages from SCF + ops truth |
| Decision Workspace | Always navigable under MEIF; question: why / what to review |
| Carts | `forbid_please_wait` when durable carts exist |
| Communication | `#communication` — not Settings WhatsApp |
| Knowledge | Merchant-language presentation only; no claim strengthening |

---

## 3. Pull request merged

| PR | Title | Merge commit |
|----|-------|--------------|
| [#48](https://github.com/majed3366/cartflow/pull/48) | Merchant Experience Integration Foundation V1 | `8b89fd2bc86b73b118f5d8a55ebe2c95f389f3b0` |

**Source commit:** `6c902ac` on `feature/merchant-experience-integration-v1`  
**Feature flag:** `CARTFLOW_MERCHANT_EXPERIENCE_INTEGRATION_V1` (enabled)

---

## 4. Production probe / runtime evidence

```bash
python scripts/_verify_merchant_experience_v1.py --base https://smartreplyai.net --store demo
```

**Result:** `ok: true`

| Field | Value |
|-------|-------|
| `foundation_enabled` | true |
| `governed_consumption_pct` | **100** |
| `legacy_consumption_pct` | 0 |
| `placeholder_count` | 0 |
| `navigation_integrity` | **true** |
| `routing_integrity` | **true** |
| `integration_failures` | **[]** |
| `registries_valid` | true |
| `canonical_fingerprint` | `245084f06256d5148c421a306595e2942159c1dec7487e9c727e9260542bf4ee` |
| `non_demo_writes` | false |
| Demo ops | abandoned_carts=**46**, purchase_truth=6, hesitation_reasons=80, mock_whatsapp_sent=49 |
| Carts | `forbid_please_wait=true`, durable_cart_count=46 |

### MEV1 high/critical resolution (probe)

All true: H01, H02, D01, C01, M01, K01, G02, S01, S02, T01, L01

### Page readiness

All pages `ready=true`, `governed_consumption=true`, `placeholder_eliminated=true`.

---

## 5. Reality Validation V2 vs V1

| Metric | V1 | V2 (local sim + MEIF) |
|--------|---:|----------------------:|
| Readiness | **28** / 100 | **72** / 100 |
| Delta | — | **+44** |
| Materially improved | — | **yes** (≥ +20) |
| MEV1 integration highs | Fail (pages ignore SCF) | **Pass** (`mev1_highs_ok`) |

Evidence: `docs/architecture/merchant_experience_validation_v2/`  
Reports: `docs/product/MERCHANT_EXPERIENCE_VALIDATION_REPORT_V1.md`, `…_V2.md`

Local V2 simulation seed `20260722` (same Small Reality scenarios as V1). Production probe confirms live MEIF consumption on Demo with durable carts present.

Remaining High items that require **new** Guidance product policy, Time Authority binding, or SCF input expansion (e.g. G01/G03, H03/H04, C02, K02/K03, D02, M02) are **out of MEIF scope** — MEIF does not invent intelligence.

---

## 6. Acceptance checklist

| Criterion | Status |
|-----------|--------|
| Every merchant page consumes governed packages | Pass (probe 100%) |
| No page recreates business logic in MEIF path | Pass |
| MEV1 Critical integration findings resolved | Pass (probe checklist) |
| Home reflects ops truth (no zero theatre with durable carts) | Pass |
| Decision Workspace exists / navigable | Pass |
| Communication no longer routes as Settings WhatsApp | Pass |
| Carts no false please-wait when durable carts | Pass |
| Knowledge merchant presentation | Pass |
| Guidance via Surface Composition consumption | Pass (Home package section + SCF lineage) |
| Reality Validation V2 materially improved | Pass (72 vs 28) |

---

## 7. STOP

**Merchant Experience Integration Foundation V1 is production-closed.**

Do **not** begin visual redesign until product confirms (this closure + Reality Validation V2) that the merchant experience truthfully reflects what the platform already knows.

Next cosmetic / IA polish is a separate phase after this STOP.
