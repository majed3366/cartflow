# Observation Reality Validation V1

**Status:** Completed & Released  
**Date (UTC):** 2026-07-24  
**Production URL:** https://smartreplyai.net/dashboard#home  
**Release:** `docs/product/observation_reality_validation_v1/RELEASE_CONFIRMATION.md`  
**Tag:** `observation-reality-validation-v1-released` — *Observation Reality Validation V1 — Released*

## Merchant surface (Home)

Temporary section «ماذا نلاحظ في منتجاتك الآن؟» paints evidence-backed observations only:

1. اهتمام مرتفع وتحويل منخفض  
2. أدلة الشحن أقوى من السعر  
3. عودة متكررة بلا شراء  
4. لا دليل على مشكلة جودة  

Each card includes:

- Business statement  
- Recommended action  
- Confidence (`مرتفع` / `متوسط` / `منخفض`) from the evidence engine  

Technical counters and product IDs are confined to `evidence_details` / diagnostics — never on Home.

## Proof

| Item | Ref |
|------|-----|
| Lab | `docs/product/observation_reality_validation_v1/` |
| Desktop | `05_production_desktop_orv_ui_polish.png` |
| Mobile | `06_production_mobile_orv_ui_polish.png` |
| Flags | `CARTFLOW_OBSERVATION_FOUNDATION_V1`, `CARTFLOW_OBSERVATION_REALITY_VALIDATION_V1` (default on) |

## Gate

Product Intelligence V1 is **not** opened by this release. Start PI only under a separate authorized work package.
