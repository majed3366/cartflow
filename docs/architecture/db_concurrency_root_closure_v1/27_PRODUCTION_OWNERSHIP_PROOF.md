# Logical Request DB Ownership Production Proof V1

**Date (UTC):** 2026-08-30  
**Status:** Authorized exact-SHA verification. Request-scoped thread-local class **closed**. Startup unowned hold remains (separate owner).

## Identity

| Field | Value |
|-------|--------|
| BASE LIVE SHA | `5e03be7bec8cad754199571628c8acff3f7a6fb1` |
| CANDIDATE / LIVE SHA | `76c0d4111afe5fedeb8e3f4fc24b7ede7915f9ab` |
| DIRECT PARENT | `5e03be7bec8cad754199571628c8acff3f7a6fb1` |
| DEPLOYMENT ID | `dea0640c-fb0e-4de7-b28e-b61820967134` |
| DEPLOYMENT STATUS | SUCCESS |
| DEPLOYMENT TIMESTAMP | `2026-08-30T18:46:15.675Z` |
| LIVE SHA PROVEN | YES — `X-CartFlow-Git-Sha` on `GET /` |
| Autodeploy | OFF |
| Scheduler | `2b1e5665` / `f91e799d` unchanged |
| Suite | 78 passed / 1 skipped |

## Exact historical dashboard cycle

Request `fe6e05caaff54df7` `GET /dashboard` 200:

```
[DB CHECKOUT] request_id=fe6e05caaff54df7 uow=uow:fe6e05caaff54df7 ... thread=MainThread
[DB CHECKIN]  request_id=fe6e05caaff54df7 ... hold_ms=10.8 finally_thread=MainThread
[DB CHECKOUT] request_id=fe6e05caaff54df7 uow=uow:fe6e05caaff54df7 ... thread=AnyIO worker
[DB CHECKIN]  request_id=fe6e05caaff54df7 ... hold_ms=26.0 checkout_thread=<worker> finally_thread=MainThread
[DB REQUEST FINALLY] ... holders_after=1 residual_threads=MainThread  # startup unowned, not worker
```

Same logical UoW on MainThread and worker. Middleware `remove()` checked in the worker connection.

## Equilibrium after that request

| Time | checked_out | request-owned holders | request-owned IIT |
|------|-------------|----------------------|-------------------|
| t0 (immediate) | 2 | 1 in-flight `/api/recovery-settings` | transient |
| +1s | 1 | 0 | 0 |
| +5s | 1 | 0 | 0 |
| +15s | 1 | 0 | 0 |
| +45s | 1 | 0 | 0 |

The remaining checkout is **startup unowned** (`request_id=unowned`, MainThread `Task-2`, `pg:22616`, last query `SELECT stores.id...`). It predates dashboard activity (checkout at `18:46:50` during application startup). Classified separately. Not restarted.

## Repeats and stages

20 sequential authenticated dashboards: after +1s each, `request_holders=0`, no extra IIT, `checked_out` stayed 1 (startup). No accumulation. Peak `checked_out=5`. Timeout 0.

Mobile PASS. Desktop PASS. Concurrent mobile+desktop PASS. `/login` 200. `/health` 200 and numeric. No QueuePool timeout.

## Verdict

Request-scoped thread-local ownership defect: **CLOSED in production**.  
Startup unowned hold: **still present** (not this task).  
First-100 and visual: still paused. Heavy-surface may proceed. No 10–100 merchant soak in this task.
