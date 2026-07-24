# Home Executive Summary Refactoring V1

**Status:** Superseded in scope by Home Stabilization Sprint V1 — awaiting CEO review  
**Date (UTC):** 2026-07-24  
**Flag:** `CARTFLOW_HOME_EXECUTIVE_SUMMARY_V1` (default ON)

## Mission

Home answers only:

> ماذا يجب أن يعرف التاجر الآن؟

Home is **not** Product Intelligence, Observation page, Decision Workspace, operational dashboard, or analytics.

## Ownership

| Surface | Owns |
|---------|------|
| Home | Executive Summary |
| Decision Workspace (`#workspace`) | Decisions |
| Product Intelligence | Product findings (not started) |
| Carts | Cart operations |
| Communication | Communication |
| Settings | Configuration |

## Home payload

`home_executive_summary_v1` sections (summary + status + count + View Details):

1. صحة العمل  
2. قرارات اليوم → `#workspace`  
3. ملاحظات المنتجات → in-place details (entity-bound preview only)  
4. السلال → `#carts`  
5. التواصل → `#communication`

ORV on Home is slimmed: no `evidence_details` / diagnostics in the summary transport.

## Observation rule

Every observation finding must include:

1. Product name (real, resolved)  
2. Business finding  
3. Confidence  
4. Recommended action  

If no real product can be identified:

> لا توجد أدلة كافية لإصدار ملاحظة مرتبطة بمنتج محدد.

No placeholders. No «هذا المنتج». No demo wording. No approved-mass injection on Home (`CARTFLOW_ORV_APPROVED_MASS_V1` default OFF). No demo store fallback.

## STOP

Do not begin Product Intelligence V1 until **Home Stabilization Sprint V1** is CEO-approved.

See: `docs/product/HOME_STABILIZATION_SPRINT_V1.md`
