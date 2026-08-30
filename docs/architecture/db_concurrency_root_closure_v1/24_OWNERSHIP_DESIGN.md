# Ownership design — Request-Scoped DB Ownership Root Fix V1

## Options

| Option | Verdict |
|--------|---------|
| A Explicit SessionLocal held only in application variables | Correct, but every `db.session` access would need a new accessor; higher migration risk. |
| B Logical request `scopefunc` (ContextVar request id) | **Selected.** Same `db.session` API. Proven ContextVar copy onto AnyIO workers. Cleanup `remove()` on MainThread closes the session the worker used. |
| C FastAPI Depends(Session) | Would require route-by-route adoption — violates INV-OWN-08. |

## Why B

- Correct ownership: scope key is `("req", request_id)`, not thread id.
- Deterministic cleanup in existing middleware `finally`.
- No `/dashboard` or route-list patches.
- Scheduler / isolated sessions unchanged (`("thr", ident)` fallback).
- Testable: set scope on MainThread, use session on worker, `remove()` on MainThread, `checked_out==0`.

B is Option A’s contract (explicit UoW begin/end) implemented as the scope of `scoped_session`, not a second Session API.

## Contract

Request ID → UoW id `uow:{request_id}` → scoped Session for `("req", request_id)` → QueuePool checkout(s).

Who closes: `finish_request` → `release_before_response` → `remove()` while the logical scope is still set.
