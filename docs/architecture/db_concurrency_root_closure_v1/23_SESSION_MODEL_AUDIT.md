# Current session model (before root fix)

| Piece | Fact |
|-------|------|
| Factory | `sessionmaker(autocommit=False, autoflush=False, bind=_engine)` in `extensions.init_database` |
| Scope | `scoped_session(factory)` — **default `scopefunc` is `threading.get_ident`** |
| Access | `db.session` → `_get_scoped()` → thread-local Session |
| Checkout | First use of that Session (`execute` / query / lazy load) |
| Commit | Explicit `db.session.commit()` on write paths; `j()` does not commit |
| Rollback | `release_scoped_db_session()` always rollback then `remove()`; `close_request_uow_if_clean` skips if dirty |
| Close/remove | `scoped_session.remove()` for **current scopefunc key only** |
| HTTP bind | Async middleware `bind_request` / `finish_request` on **MainThread** |
| Sync routes | FastAPI/AnyIO `to_thread.run_sync` — **AnyIO worker thread** |
| Auth | Async middleware: checkout + `close_request_uow_if_clean` on MainThread |
| Isolated | `isolated_db_session()` — own Session, same Engine; not request-scoped |
| Scheduler/CLI | No HTTP bind; thread-local fallback is correct for those owners |

Proven defect: handler Session key = worker thread id; cleanup key = MainThread id.

ContextVar **does** copy into AnyIO workers (`anyio.to_thread.run_sync`). That makes a logical-request `scopefunc` valid (tested).
