# Residual Dashboard Checkout Owner Identification V1

**Status:** INSTRUMENTATION DEPLOYED FOR OWNER PROOF — no application lifecycle fix.  
**Live base:** `b728856fa26e34811f4973b26a4392b89655e54f`  
**Date (UTC):** 2026-08-30

## Instrumentation gap (Step 1)

`[REQUEST_ENTER]` / `[ROUTE_END]` appear in Railway because `request_timing_audit_v1` **prints to stdout**.

`[DB CHECKOUT]` / `[DB CHECKIN]` / `[DB LONG HOLD]` used only `logging.getLogger("cartflow").info`. The API process does not configure a stdout handler for that logger, so PoolEvents could fire and still be invisible.

Fix (diagnostic only): `holder_diag_v1.emit` prints the same way as request timing. Listeners attach in `init_database` on the sole runtime `create_engine`.

Runtime `create_engine` paths in the API process: **one** — `extensions.init_database`. Alembic is not imported. `isolated_db_session` binds the same `db.engine`.

## Leading mechanism (static + local proof)

FastAPI runs sync `def` routes in a threadpool. `scoped_session` is thread-local.

- Auth middleware is async: checkout + `close_request_uow_if_clean` on the event-loop thread. Production `ROUTE_START checked_out=0` matches this (H1 falsified).
- `GET /dashboard` is sync: `_merchant_dashboard_db_ready` + store row + shell fields checkout on a **worker thread**. It returns `TemplateResponse` without releasing that thread's session.
- Middleware `finally` / `finish_request` run on the **event-loop thread** and `remove()` a different thread-local session.

Local test: `test_remove_on_other_thread_does_not_checkin`.

`POST /dev/living-store-home-review-session` ends `checked_out=0` because `j()` releases **on the worker thread**.

## Production proof (deploy `5beb6c09` / SHA `5e03be7b`)

Idle `checked_out=0`. One authenticated `GET /dashboard` (`71c1b85122b241c0`):

```
[DB CHECKOUT] .../dashboard conn=pg:22451 thread=MainThread     # auth
[DB CHECKIN]  .../dashboard conn=pg:22451 hold_ms=28.1          # auth release
[DB CHECKOUT] .../dashboard conn=pg:22451 thread=AnyIO worker   # handler
[DB REQUEST FINALLY] ... finally_thread=MainThread holders_after=1 residual_threads=<worker>
```

Registry + `pg_stat_activity` (isolated NullPool): pid 22451, **idle in transaction**, last query `SELECT stores.id ...`. Request already finished. Peak checked_out=3.

Owner class: **REQUEST_TEARDOWN_DEFECT** (sync worker `scoped_session` not closed by async `finally`). Also **FRAMEWORK_CONTEXT_LIFETIME** + **IDLE_IN_TRANSACTION**. No application fix in this SHA.

## What this change does not do

No dashboard/auth/UoW behavior change. No pool size change. No Scheduler change.
