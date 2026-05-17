# DB foundation stabilization (CartFlow backend)

Date: 2026-05-17 (UTC)

## Problem observed

Production and load-style runs showed:

```text
SQLAlchemy QueuePool exhausted: QueuePool limit of size 5 overflow 12 reached, connection timed out
```

That blocked `/api/cart-event`, delayed recovery/WhatsApp work, and made dashboard reads unreliable.

## Root causes found

1. **Connections held across `asyncio.sleep`**
   Recovery dispatch and sequence tasks queried the DB, then slept for minutes while the request-scoped SQLAlchemy session could still hold a pooled connection on the event-loop thread.

2. **Background work without session teardown**
   `asyncio.create_task` recovery entry points did not call `scoped_session.remove()` at task start/end. Deferred FastAPI `BackgroundTasks` sometimes inherited the HTTP request’s scoped session.

3. **Same thread, one scoped session**
   FastAPI + recovery tasks on one worker share a thread-local `scoped_session`. Without explicit `remove()`, sessions and connections stack under concurrent cart events and delayed recoveries.

4. **Detached ORM rows via `contextvars`**
   `asyncio.create_task` copies the parent `cart_event_request_scope` cache. After `scoped_session.remove()`, cached `CartRecoveryReason` instances raised `not bound to a Session`. Fixed by `clear_request_scoped_orm_caches()` before async waits and at background task entry.

4. **Schema warm on hot path (first request only)**
   `_ensure_cartflow_api_db_warmed()` runs `create_all` + DDL helpers once per process; repeated calls were cheap but still invoked on every non–`cart_state_sync` add event until the warm flag was set. Warm is now startup-first and cart-event skips re-warm when already done.

5. **Pool return hygiene (Postgres)**
   Not a size-only fix: `pool_reset_on_return="rollback"` was added so returned connections are rolled back before re-entering the pool.

## What was fixed

| Area | Change |
|------|--------|
| `services/db_session_lifecycle.py` | `release_scoped_db_session()`, `scoped_db_session_begin()`, `isolated_db_session()`, `run_sync_background_db_task()`, `release_db_before_async_wait()` |
| Recovery asyncio tasks | Wrap `_run_recovery_sequence_after_cart_abandoned` and `_run_recovery_dispatch_cart_abandoned` with begin/finally release |
| Delay / poll waits | `release_db_before_async_wait()` immediately before `asyncio.sleep` in recovery sequence and dispatch poll loop |
| Deferred cart-event work | Commercial return, VIP merchant alert, rejection reset use `run_sync_background_db_task` |
| Widget config refresh | Background job begins/ends with scoped cleanup; DB reads use `isolated_db_session()` |
| `extensions.py` | `pool_reset_on_return="rollback"` for non-SQLite engines |
| `/api/cart-event` | Skip `_ensure_cartflow_api_db_warmed()` when already warmed; `[CART-EVENT] start/end` logs (no phone numbers) |
| Tests | `tests/test_db_session_lifecycle.py` |

## Remaining risks

- **Many concurrent delayed recoveries** on a single worker can still contend for the pool (5 + 12 overflow). Mitigation is operational (workers, DB pooler) until a dedicated queue/worker owns recovery sends.
- **Long synchronous DB inside request handlers** (dashboard, admin) was not refactored in this pass; only cart-event hot path and recovery/defer paths.
- **SQLite local dev** uses `NullPool`; pool exhaustion is mainly a Postgres/production concern.

## What should move to Queue/Worker later

- Delayed recovery sequence after `cart_abandoned` (currently `asyncio.create_task` + sleep in-process).
- Reason polling loop in `_run_recovery_dispatch_cart_abandoned_impl`.
- WhatsApp send retries (partially queued already via `services/whatsapp_queue.py`).
- Widget config cache refresh (already offloaded; could use a shared worker).

## Dashboard templates

**Check dashboard template loading after this foundation fix.** Template save/load APIs and UI were intentionally out of scope. If templates still fail, investigate store resolution and dashboard routes separately; pool exhaustion should no longer masquerade as template bugs.

## Verification

```bash
python -m pytest tests/test_db_session_lifecycle.py tests/test_recovery_store_from_context.py tests/test_recovery_isolation.py -q
```

Manual: repeat demo cart flow 5×; logs should not show `QueuePool limit` or `connection timed out`.
