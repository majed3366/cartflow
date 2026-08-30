# Final verdict

**Program status:** request-scoped class **CLOSED**. Startup unowned class **CLOSED** on live `f613ec71` (`checked_out=0`, IIT=0).  
**Connection-demand / messages read-model:** local A+B candidate (not deployed). Production 50→60→80→100 **NOT_RUN**.  
**First-100 / visual:** First-100 **NOT_CLOSED** (highest proven **50**). Visual paused.

| Gate | Result |
|------|--------|
| ROOT CAUSE | **PROVEN** (thread-local scoped_session vs ASGI request) |
| LOGICAL SESSION OWNER | **EXPLICIT** (`uow:{request_id}`) |
| THREAD-LOCAL REQUEST OWNERSHIP | **REMOVED** for HTTP requests |
| REQUEST EXIT CLEANUP | **PASS** on production `GET /dashboard` (worker checkin on MainThread finally) |
| REQUEST-OWNED IDLE_IN_TRANSACTION | **0** after settle |
| STARTUP UNOWNED HOLD | **0** on `f613ec71` (was 1 on `76c0d411`) |
| 20 DASHBOARD REPEATS | **PASS** (no accumulation) |
| MOBILE / DESKTOP / BOTH | **PASS** |
| QUEUEPOOL TIMEOUT | **NO** |
| FIRST-100 | **NOT_CLOSED** (10/25/50 PASS, 100 FAIL, live `f613ec71`) |
| SAFE TO RESUME VISUAL WORK | **NO** |

## Deployed candidate

| | |
|--|--|
| BASE SHA | `5e03be7bec8cad754199571628c8acff3f7a6fb1` |
| CANDIDATE / LIVE SHA | `76c0d4111afe5fedeb8e3f4fc24b7ede7915f9ab` |
| DIRECT PARENT | `5e03be7bec8cad754199571628c8acff3f7a6fb1` |
| DEPLOYMENT ID | `dea0640c-fb0e-4de7-b28e-b61820967134` |

**STOP.** First-100 not closed. Do not resume visual work. Do not add infrastructure in this program. A separate root-cause task may follow the 100-session pool-saturation fail.
