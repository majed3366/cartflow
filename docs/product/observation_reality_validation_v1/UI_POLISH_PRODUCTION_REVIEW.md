# Observation Reality Validation V1 — Final UI Polish

**Status:** Deployed — **awaiting production review approval** (do not close ORV V1 until approved)  
**Date (UTC):** 2026-07-24  
**Production URL:** https://smartreplyai.net/dashboard#home

## Merchant surface (Home)

Each observation card shows only:

1. Business statement  
2. Recommended action (`الخطوة المقترحة`)  
3. Confidence badge (`مرتفع` / `متوسط` / `منخفض`) from Evidence Confidence thresholds  

Technical fields (`cart_add`, `purchase`, `return`, `shipping`, `price`, `evidence_refs`, product IDs) are **not** rendered on Home. They remain under `evidence_details` / `diagnostics` for Evidence Details / Developer View.

## Screenshots

| Viewport | File |
|----------|------|
| Desktop | `03_desktop_orv_ui_polish.png` |
| Mobile | `04_mobile_orv_ui_polish.png` |

Verification JSON: `ui_polish_verification.json`

## Confirmations

- Technical fields hidden on Home: **Yes**  
- Every observation has statement + action + confidence: **Yes**  
- Product Intelligence V1: **not started**

## STOP

Do not close Observation Reality Validation V1 until these production screenshots are reviewed and approved.
