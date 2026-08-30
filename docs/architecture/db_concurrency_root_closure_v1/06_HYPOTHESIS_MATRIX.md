# Phase 5 — Hypothesis matrix

| ID | Hypothesis | Class | Evidence |
|----|------------|-------|----------|
| H1 | Request-scoped session remains open until response completion | **SUPPORTED** (pre-fix); **mitigated** by `j()` + identity-phase release + `finally` | First-100 audit; middleware order; `j()` now releases clean sessions |
| H2 | External HTTP while DB checked out | **SUPPORTED** on VIP poll / some Meta helpers (pre-fix); WhatsApp/Zid/email already released on `c453d336` | `vip_operational_truth_v1` now calls `release_before_external_wait`; static audit |
| H3 | Serialization retains ORM and therefore connection | **PARTIAL** | Dict APIs now release in `j()`; HTML dashboard may still hold until `finally` if ORM attached |
| H4 | Exceptions skip cleanup | **FALSIFIED** for middleware `finally`; **PARTIAL** for nested begin stacks | `db_scoped_session_cleanup` / `short_db_phase` finally; failure-injection tests |
| H5 | Admission-rejected requests leak or retain resources | **SUPPORTED** before this pack (auth DB first); **mitigated** | Pre-DB admit + cookie-less 401; slot released in `finish_request` |
| H6 | Nested helpers open independent sessions | **PARTIAL** | `isolated_db_session` unused on hot path; recovery nested `scoped_db_session_begin` still overlapping |
| H7 | Long-running SQL is the actual holder | **UNPROVEN** as primary; Settings/dashboard incidents were fan-out + hold, not one slow query | No production `pg_stat_activity` this freeze |
| H8 | Idle-in-transaction accumulates | **UNPROVEN** | `pool_reset_on_return=rollback`; PG not sampled |
| H9 | Multiple normal tabs saturate 5+5 even with correct lifecycle | **PARTIAL** | Math: 2 tabs × (auth + 2–3 heavy) can still approach 10 if holds stay long; short phases + admission make this the remaining capacity question |
| H10 | Instrumentation falsely reports retained connections | **PARTIAL** | `status()`-only snapshot was a defect (fixed); real 503s still occurred |

## What this pack addresses

H1, H2 (VIP), H3 (JSON), H5, H10 (numeric pool). H6 recovery nesting and H7/H8 production PG remain open items, not claimed closed.
