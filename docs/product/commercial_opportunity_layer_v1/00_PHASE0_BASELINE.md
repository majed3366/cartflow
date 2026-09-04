# Commercial Opportunity Layer V1 — Phase 0 Production Baseline

**Date (UTC):** 2026-09-03  
**Mode:** Observe only (pre-implementation record)

## Live production

| Field | Value |
|--------|--------|
| LIVE API SHA | `033cdd482960c6b66f5f22c1027ce3b9ba9f485e` |
| Domain | `smartreplyai.net` |
| API service | `f3731fa1` (`smart-reply-ai`) |
| Runtime | `merchant_ui_v2` / `merchant_app_v2.html` / `CartFlowUiV2Home` |
| Home asset | `merchant_ui_v2_home.js` |
| Home question (constitution) | ماذا يجب أن أعرف الآن عن متجري؟ |
| Home data home | `GET /api/dashboard/summary` |
| Workspace | `#workspace` → `GET /api/cart-workspace/v1/projection` |
| Semantic model | `semantic-visual-model-v1` |
| Auth | merchant session cookie |
| QueuePool | healthy (`timeout_count=0` at baseline probe) |
| Scheduler | `882d9906` / deploy `2b1e5665` / SHA `f91e799d` |
| Autodeploy | OFF |

## Commercial preview (isolated)

| Field | Value |
|--------|--------|
| Route | `/preview/commercial-intelligence` |
| Flag | `CARTFLOW_COMMERCIAL_INTELLIGENCE_PREVIEW` (API only) |
| Truth | `SIMULATION_TRUTH` only |
| Payload | RRV → RIM → CDI → CDL V1.1 lab |
| Must not leak into | `/dashboard` |

## Home data packages already on summary

- `home_executive_summary_v1` (HES) — operational executive sections
- `operational_guidance_v1` (OGL) — governed guidance when evidence suffices
- `diagnostic_publication_v1` — published diagnosis families
- `merchant_reason_rows_week` / `_month` — hesitation reason counts
- Teaser KPIs — abandoned / recovered / WA (operational, not purchase attribution)

## Implementation constraint

COL V1 must be **flag-gated**, **production-truth-only**, and must **not** displace HES/OGL operational attention.
