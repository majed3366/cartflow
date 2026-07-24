# Home Stabilization Sprint V1

**Status:** Implemented — awaiting CEO / production review before Product Intelligence V1  
**Date (UTC):** 2026-07-24  
**Flag:** `CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1` (default ON)

## Mission

Freeze new Home feature development. Stabilize Home as a deterministic **Executive Summary** before Product Intelligence V1.

## Acceptance

| Criterion | Implementation |
|-----------|----------------|
| Deterministic Home | Same production inputs → same `home_executive_summary_v1` sections; no demo slug fallback; no approved-mass on Home; no MEIF lab→demo BFL swap when HES on |
| Fast initial load | Home paints summaries only; stage spans: `home_stage_meif_attach`, `home_stage_adaptive_cognition`, `home_stage_orv_attach`, `home_stage_hes_attach`, `home_stage_commerce_pulse` |
| Executive Summary only | Five teasers: health / decisions / observations / carts / communication — each: summary + status + count + View Details |
| Observation integrity | Real product name required; else «لا توجد أدلة كافية لإصدار ملاحظة مرتبطة بمنتج محدد.»; «هذا المنتج» banned as display name |
| Rendering governance | Single owner `home_executive_summary_v1`; single data source `finalize_dashboard_summary_payload`; single paint path `maApplyHomeExecutiveSummaryV1` when `home_surface_mode=executive_summary_v1` |

## Ownership

| Surface | Owns |
|---------|------|
| Home | Executive Summary |
| Decision Workspace (`#workspace`) | Decisions |
| Product Intelligence | Product findings (**not started**) |
| Carts (`#carts`) | Cart operations |
| Communication (`#communication`) | Communication |
| Settings | Configuration |

## STOP

**Do not begin Product Intelligence V1** until CEO review approves this sprint.

Related: `docs/product/HOME_EXECUTIVE_SUMMARY_V1.md`
