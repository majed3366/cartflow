# Final verdict

**Program status: NOT CLOSED.**  
**Production verification V1: STOP after Stage 1.**  
**Local ownership-root candidate:** ready for authorized production verification only. Not deployed.

| Gate | Result |
|------|--------|
| ROOT CAUSE | **PROVEN** locally (request-owned session hold). Production dashboard HTML still left a checkout after `ROUTE_END`. |
| SESSION OWNERSHIP | **EXPLICIT** in `db_lifecycle_v1` |
| TRANSACTION OWNERSHIP | **EXPLICIT** (short phase + persist-site commit) |
| DB HELD ACROSS EXTERNAL I/O | **0 unapproved** on merchant send/Zid/email/VIP-poll entries |
| REQUEST EXIT CLEANUP | **PASS** locally; **FAIL** on production `GET /dashboard` (ended `checked_out=1`, residual held minutes) |
| IDLE_IN_TRANSACTION | **UNKNOWN** (PG not sampled; no public URL) |
| ABNORMAL LONG HOLDERS | **1 unexplained residual** after Stage 1 (`checked_out=1`; no `[DB CHECKOUT]` line in Railway logs) |
| INACTIVE SURFACE WORK | **0** (preserved) |
| HEAVY ROUTE ADMISSION | **PASS** locally; **NOT_PROVEN** in production (Stage 5 not run) |
| QUERY BOUNDS | **PASS** (First-100 caps kept) |
| FAILURE INJECTION | **PASS** locally (QueuePool) |
| PRODUCTION QUEUEPOOL | **VERIFIED live** (`QueuePool` 5+5, `timeout_count=0`) |
| POSTGRES RECONCILIATION | **NOT RUN** (no public DB URL) |
| SINGLE-MERCHANT EQUILIBRIUM | **FAIL** production Stage 1 (did not return to idle `checked_out=0`) |
| MULTI-TAB EQUILIBRIUM | **NOT_RUN** (stop after Stage 1) |
| 10 / 25 / 50 / 100 MERCHANT | **NOT_RUN** (paused) |
| QUEUEPOOL TIMEOUT | **NO** in this production window |
| AUTH / DASHBOARD AVAILABILITY | `/login` `/health?db=1` `/ping` 200 under residual checkout |
| RETURNS TO EQUILIBRIUM | **NO** without restart after Stage 1 |
| NEW INFRASTRUCTURE | **NOT REQUIRED** |
| FIRST-100 DB RESOURCE SAFETY | **NOT_CLOSED** |
| SAFE TO RESUME VISUAL WORK | **NO** |

## Deployed candidate

| | |
|--|--|
| BASE SHA | `c453d33680d4c70f9e52098cb7e6f8bf39cc5a1c` |
| CANDIDATE / LIVE SHA | `b728856fa26e34811f4973b26a4392b89655e54f` |
| DIRECT PARENT | `c453d33680d4c70f9e52098cb7e6f8bf39cc5a1c` |
| DEPLOYMENT ID | `26e5c277-3dee-4c60-b3ec-0e14c7135b84` |

**STOP.** Do not start First-100 soak. Do not resume visual work. Residual `checked_out=1` remained on the live API after Stage 1; no further merchant stages.
