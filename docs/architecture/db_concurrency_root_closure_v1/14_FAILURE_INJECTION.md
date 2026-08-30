# Phase 12 — Failure injection

| Case | How tested | Session / checkin |
|------|------------|-------------------|
| DB query exception | `short_db_phase` raises; QueuePool `connect`+`SELECT` then raise | `finally` release; `checked_out` == baseline |
| External HTTP timeout | contract: `release_before_external_wait` at VIP/WhatsApp/Zid | no hold across wait |
| App exception after DB read | QueuePool test | checkin in `with` / `finally` |
| HTTPException / early return | `j()` + middleware `finally`; QueuePool early-return test | checkin |
| Client disconnect | middleware `finally` (CancelledError) | designed; not live-injected |
| Admission rejection | unauthenticated heavy GET → 401, `global_in_use=0` | no checkout |
| Transaction rollback | `release_scoped_db_session` rolls back; `pool_reset_on_return=rollback` | no leftover xact locally |

Harness: `tests/test_db_concurrency_root_closure_v1.py` (**QueuePool**, not NullPool).  
Companion: `tests/test_db_lifecycle_failure_injection_v1.py` (UoW exception, admission reject, `/ping` `/health` finally).
