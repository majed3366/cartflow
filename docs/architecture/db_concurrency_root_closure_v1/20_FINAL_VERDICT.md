# Final verdict

**Program status: NOT CLOSED.**

| Gate | Result |
|------|--------|
| ROOT CAUSE | **PROVEN** (request-scoped hold ≈ request lifetime + auth-before-admission). Not a leak. |
| SESSION OWNERSHIP | **EXPLICIT** in `db_lifecycle_v1` |
| TRANSACTION OWNERSHIP | **EXPLICIT** (short phase + persist-site commit) |
| DB HELD ACROSS EXTERNAL I/O | **0 unapproved** on merchant send/Zid/email/VIP-poll entries; HTML/recovery-nest residual documented |
| REQUEST EXIT CLEANUP | **PASS** locally (finally + UoW + QueuePool tests) |
| IDLE_IN_TRANSACTION | **UNKNOWN** in production (PG not sampled) |
| ABNORMAL LONG HOLDERS | **UNKNOWN** in production; local ledger exists |
| INACTIVE SURFACE WORK | **0** (preserved `58a82f3`) |
| HEAVY ROUTE ADMISSION | **PASS** locally (before DB) |
| QUERY BOUNDS | **PASS** (First-100 caps kept) |
| FAILURE INJECTION | **PASS** locally (QueuePool) |
| PRODUCTION QUEUEPOOL | **NOT VERIFIED** |
| POSTGRES RECONCILIATION | **NOT RUN** |
| SINGLE-MERCHANT EQUILIBRIUM | **PASS** local QueuePool only |
| MULTI-TAB EQUILIBRIUM | **NOT_RUN** live |
| 10 / 25 / 50 / 100 MERCHANT | **NOT_RUN** (paused) |
| QUEUEPOOL TIMEOUT | **NO** in local harness; production unknown |
| AUTH / DASHBOARD AVAILABILITY | local `/ping` `/health` PASS; production login 200 at freeze; dashboard not soaked |
| RETURNS TO EQUILIBRIUM | **PASS** local QueuePool |
| NEW INFRASTRUCTURE | **NOT REQUIRED** |
| FIRST-100 DB RESOURCE SAFETY | **NOT_CLOSED** |
| SAFE TO RESUME VISUAL WORK | **NO** |

## Candidate (do not deploy)

| | |
|--|--|
| BASE SHA | `c453d33680d4c70f9e52098cb7e6f8bf39cc5a1c` |
| NEW SHA | *uncommitted until asked* |
| DIRECT PARENT | `c453d33680d4c70f9e52098cb7e6f8bf39cc5a1c` |

**STOP.** Await authorization to commit/deploy. Do not resume visual work. Do not start First-100 soak.
