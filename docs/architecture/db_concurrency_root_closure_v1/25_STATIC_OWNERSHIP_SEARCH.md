# Static ownership search after logical-request scope

## Request path (must follow INV-OWN)

| Location | Classification |
|----------|----------------|
| `extensions.init_database` | **FIXED.** `scoped_session(..., scopefunc=logical_request_scopefunc)` |
| `http_bind.bind_request` / `finish_request` | **FIXED.** Begin/end logical scope; `remove()` while scope is set |
| `db_session_lifecycle.release_scoped_db_session` | Common rollback+remove — now removes the **logical** session |
| `unit_of_work` / `j()` | Same accessor; no route list |
| `routes/merchant_pages.py` | **No** `remove()` / route-specific cleanup |

## Remaining thread-key fallback (intentional non-request owners)

| Location | Owner class | Action |
|----------|-------------|--------|
| Scheduler process | Process/thread job | Unchanged. No HTTP bind. Fallback `("thr", ident)` is correct. |
| `isolated_db_session()` | Explicit isolated Session | Unchanged. Own close(). |
| `run_sync_background_db_task` | Background task on its thread | Unchanged. begin/release on same thread after request scope ends. |
| Admin load-test helpers | Test/admin harness | Own `remove()` on the worker they use. Not HTTP request owners. |
| CLI / pytest thread | Thread fallback | Not a request. |

## Legacy proof kept

`tests/test_db_residual_checkout_owner_v1.py` still constructs **default** thread-local `scoped_session` to prove the old defect remains if logical scope is omitted.
