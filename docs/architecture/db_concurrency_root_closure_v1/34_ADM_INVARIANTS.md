# INV-ADM — Connection-demand admission invariants

**Status:** Binding. Written before the messages read-model change.  
**Parent:** [33_100_CONCURRENCY_SATURATION_RCA.md](33_100_CONCURRENCY_SATURATION_RCA.md)  
**Date (UTC):** 2026-08-30

These laws close the proven mismatch: admission counted HTTP requests while the scarce resource is QueuePool **connection demand**.

| ID | Invariant | Test | Production proof |
|----|-----------|------|------------------|
| **INV-ADM-01** | Admission models bounded DB resource demand, not only HTTP request count. | After demand reduction, remaining messages demand is documented (one scoped-session checkout for the bounded DB phase). Extra weights are forbidden without a new checkout-count measurement. | Messages `checkout_count` on FINALLY is the demand unit, not “1 GET”. |
| **INV-ADM-02** | One merchant action that fans out into multiple DB-consuming requests must not consume the entire shared pool. | Communication still admits messages/followups under HEAVY 4/2; summary remains uncapped but is not the proven 60-checkout path. | Peak `checked_out` under Communication composition stays below 10/10 at the last proven-safe stage (50). |
| **INV-ADM-03** | Critical merchant control paths retain usable capacity under heavy optional work. | `/ping`, `/health` (no `db=1`), `/login` take no heavy slot. HEAVY_GLOBAL_LIMIT=4 leaves 6 of 10. | Critical 200s while messages is admitted or rejected. |
| **INV-ADM-04** | Heavy work degrades before critical work starves. | Rejected heavy GET returns 503 `db_pressure` before checkout. | Controlled 503, not QueuePool timeout, on overflow. |
| **INV-ADM-05** | A heavy request must not hold a DB connection while performing long application/lifecycle work unrelated to active SQL. | `compose_messages_after_db_phase` calls `close_request_uow_if_clean` before last_send/JSON assembly. | Messages `last_hold_ms` ≈ last SQL, not `request_ms`. |
| **INV-ADM-06** | Repeated history/timeline reads have explicit bounds and must not reacquire DB dozens of times when one bounded materialization can serve the request. | `ensure_timeline_table_ready` skips `inspect.has_table` after `_schema_once`. Enrich uses one log IN + `bulk_timeline_status_sets` + one schedule IN. Caps: messages 40/80, schedule 2000. | Per-request `checkout_count` materially below the proven ~60. |
| **INV-ADM-07** | Admission rejection occurs before DB checkout. | `maybe_reject_heavy_before_db` + handler `admit_heavy_route`. | Rejected request ledger checkouts = 0. |
| **INV-ADM-08** | No fix may change business truth or silently omit required merchant data. | Existing messages/carts/resolve e2e; compose copies materialized rows without dropping fields. | Merchant-visible lifecycle/history unchanged. |
| **INV-ADM-09** | No pool-size increase may be used to satisfy this closure. | `API_DEFAULT_SIZE=5`, `API_DEFAULT_OVERFLOW=5`, timeout 5s. | QueuePool config unchanged on deploy. |

## Non-invariants

- Enlarging the pool, adding Redis/PgBouncer/replicas
- Changing Scheduler pool or due-scanner enablement
- First-100 rerun before local + exact-SHA production proof
- Visual assimilation
