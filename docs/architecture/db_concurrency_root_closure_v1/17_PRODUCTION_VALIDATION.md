# Phase 16 — Production validation

**Date (UTC):** 2026-08-30  
**Status:** Superseded for the dashboard thread-local class by [27_PRODUCTION_OWNERSHIP_PROOF.md](27_PRODUCTION_OWNERSHIP_PROOF.md) on live `76c0d411`. This file remains the Stage 1 FAIL record for `b728856f`.

## Identity

| Field | Value |
|-------|--------|
| BASE SHA | `c453d33680d4c70f9e52098cb7e6f8bf39cc5a1c` |
| CANDIDATE SHA | `b728856fa26e34811f4973b26a4392b89655e54f` |
| DIRECT PARENT | `c453d33680d4c70f9e52098cb7e6f8bf39cc5a1c` |
| DEPLOYMENT ID | `26e5c277-3dee-4c60-b3ec-0e14c7135b84` |
| DEPLOYMENT STATUS | SUCCESS |
| DEPLOYMENT TIMESTAMP | `2026-08-30T17:45:58.877Z` |
| LIVE SHA | `b728856fa26e34811f4973b26a4392b89655e54f` via `X-CartFlow-Git-Sha` on `GET /` |
| LIVE SHA PROVEN | YES |
| Scheduler latest | `2b1e5665-ae6e-4e5b-9e8a-aa1b205fedf9` / `f91e799d` unchanged |
| Autodeploy API / Scheduler | OFF / OFF |
| Pool env overrides | none (code defaults 5 / 5 / 5s) |
| Suite | 44 passed (lifecycle + session + pool-health files) |

## Stage 0 idle — PASS

Before merchant activity, `GET /health` pool:

- `pool_impl=QueuePool`
- `checked_out=0`, `checked_in=1`, `overflow=-4`
- `configured_pool_size=5`, `configured_max_overflow=5`, `max_connections=10`
- `peak_checked_out=1`, `timeout_count=0`
- `/ping` `/health` `/health?db=1` `/login` all HTTP 200
- Health truthful (numeric pool object, not status string only)

Postgres `pg_stat_activity`: **not captured** (Postgres service has no public URL from this workstation; internal `DATABASE_URL` only).

## Stage 1 mobile — FAIL — STOP

Living Store review session issued (`POST /dev/living-store-home-review-session` 200, cookie set, `store_slug=demo`).

Authenticated `GET /dashboard`:

```
REQUEST_ENTER checked_out_connections=0
ROUTE_START   pre_route_ms=14.4 checked_out_connections=0
ROUTE_END     elapsed_ms=63.2 route_ms=63.2 checked_out_connections=1
```

After the HTML request finished, subsequent static and `/api/dashboard/summary` still saw `checked_out_connections=1`. `/health` remained `checked_out=1` for more than 45s of explicit wait, and again on a later poll minutes afterward. Peak `checked_out` observed: **3**. `timeout_count`: **0**. `/login` and `/health?db=1` stayed HTTP 200.

`[DB CHECKOUT]` / `[DB CHECKIN]` / `[DB LONG HOLD]` lines were **not present** in Railway deploy logs (request-timing `checked_out_connections` was the usable signal). Holder therefore **not fully attributed** (no connection id / Postgres PID).

Stages 2–5 were **not run** (stop law).

## Contrast: living-store session did release

```
REQUEST_ENTER .../living-store-home-review-session checked_out_connections=0
ROUTE_END     elapsed_ms=110.0 checked_out_connections=0
```

That path did DB work (~110ms) and returned to 0 at route end. The dashboard HTML path did not.

## Root-cause claim

**BEFORE lifecycle still observed on `GET /dashboard`:** checkout during the request, request ends, connection remains checked out (not returned for remaining process lifetime / later requests).

**AFTER lifecycle (checkout → required DB → checkin → non-DB remainder) is NOT_PROVEN for the merchant dashboard surface.** It is consistent with the living-store session route only.

No QueuePool timeout in this window. Critical routes stayed up. Equilibrium after Stage 1 **did not** return without restart.

## Verdict

**ROOT FAILURE CLASS CLOSED IN PRODUCTION: NO**  
**FIRST-100 DB RESOURCE SAFETY: NOT_CLOSED**  
**SAFE TO START FIRST-100 VALIDATION: NO**  
**SAFE TO RESUME VISUAL WORK: NO**
