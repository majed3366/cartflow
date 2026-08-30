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

## What this change does not do

No dashboard/auth/UoW behavior change. No pool size change. No Scheduler change.
