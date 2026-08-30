# Request-Scoped DB Ownership Root Fix V1

Local candidate. **Not deployed.** First-100 and visual remain paused.

## Design

**Option B** — logical request `scoped_session.scopefunc` (`ContextVar` request id), with Option A’s explicit UoW begin/end around the HTTP request.

ContextVar copy into AnyIO workers is **tested**, not assumed.

## What changed

- `services/db_lifecycle_v1/request_session_scope.py`
- `extensions.py` — `scopefunc=logical_request_scopefunc`
- `http_bind.py` — bind scope on request start; `remove()` before scope end
- Checkout ledger records `uow_id` / `logical_scope`
- `/static/` checkout/finally logs quieted
- Tests: `tests/test_db_request_ownership_root_fix_v1.py`

## Unchanged

Pool 5+5+5s. Scheduler. No `/dashboard` patch. No route-list `remove()`. No deploy.
