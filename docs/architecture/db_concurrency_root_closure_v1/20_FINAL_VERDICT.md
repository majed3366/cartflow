# Final verdict

**Program status:** request-scoped thread-local class **CLOSED in production**. Absolute idle `checked_out=0` is **not** met (startup unowned hold remains).  
**First-100 / visual:** still paused.

| Gate | Result |
|------|--------|
| ROOT CAUSE | **PROVEN** (thread-local scoped_session vs ASGI request) |
| LOGICAL SESSION OWNER | **EXPLICIT** (`uow:{request_id}`) |
| THREAD-LOCAL REQUEST OWNERSHIP | **REMOVED** for HTTP requests |
| REQUEST EXIT CLEANUP | **PASS** on production `GET /dashboard` (worker checkin on MainThread finally) |
| REQUEST-OWNED IDLE_IN_TRANSACTION | **0** after settle |
| STARTUP UNOWNED HOLD | **1** (`pg:22616`, MainThread, not request-owned) |
| 20 DASHBOARD REPEATS | **PASS** (no accumulation) |
| MOBILE / DESKTOP / BOTH | **PASS** |
| QUEUEPOOL TIMEOUT | **NO** |
| FIRST-100 | **NOT_CLOSED** (paused) |
| SAFE TO RESUME VISUAL WORK | **NO** |

## Deployed candidate

| | |
|--|--|
| BASE SHA | `5e03be7bec8cad754199571628c8acff3f7a6fb1` |
| CANDIDATE / LIVE SHA | `76c0d4111afe5fedeb8e3f4fc24b7ede7915f9ab` |
| DIRECT PARENT | `5e03be7bec8cad754199571628c8acff3f7a6fb1` |
| DEPLOYMENT ID | `dea0640c-fb0e-4de7-b28e-b61820967134` |

**STOP.** Do not start First-100. Do not resume visual work. Do not run 10–100 merchant soak in this task.
