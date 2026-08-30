# Heavy-Surface DB Concurrency Verification V1

**Live SHA:** `f613ec7145a5e29c56257187159bfe366c26b3c0`  
**Date (UTC):** 2026-08-30  
**Code change:** none

## Baseline

`checked_out=0`, holders=0, IIT=0. `/ping` `/health` `/health?db=1` `/login` 200.

## Stages

All standalone heavy paths 200, then `checked_out=0`, IIT=0. `/login` and `/health?db=1` stayed 200.

| Stage | Result |
|-------|--------|
| Workspace `/api/cart-workspace/v1/projection` | 200, wall ~412ms, ROUTE_END 299ms, post `checked_out=0` |
| Messages | 200, client 2947ms, ROUTE_END 2162ms, post 0 |
| Followups | 200, 165ms / 54ms, post 0 |
| Normal-carts | 200, snapshot_mode, 788ms / 648ms, post 0 |
| Communication composition (messages+followups+summary) | all 200, peak 3, post 0 |
| Workspace + Communication | all 200, peak 3, post 0 |
| Mobile + desktop | peak 8; one desktop messages **503** (`db_pressure`, `request_ms=0.1`, no checkout); login/health 200; post 0 |

The 503 is admission: heavy work rejected before DB while other admitted messages were in flight. Not a timeout. Not a leftover.

## Hold vs wall

Individual `[DB CHECKIN] hold_ms` on messages was **0.1–7.9ms**. Messages wall was **~1.9–2.2s**. Connection lifetime tracks the DB phase, not remaining request wall. Checkin on the AnyIO worker (`j()`).

## Equilibrium

immediate / +1s / +5s / +15s / +45s: `checked_out=0`, holders=0, IIT=0. No restart. `timeout_count=0`.

## First-100 / visual

Not run. Visual remains paused.
