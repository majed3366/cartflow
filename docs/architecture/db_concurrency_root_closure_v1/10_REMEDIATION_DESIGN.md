# Phase 7 — Remediation design

Reusable rules. **Not** `main.py` business logic. **Not** pool enlargement.

| Pattern | Implementation |
|---------|----------------|
| A. Explicit UoW | `short_db_phase`, `close_request_uow_if_clean`, request `finally` |
| B. Short DB phase | Auth resolve → materialize slug → close; `j()` closes clean session before encode |
| C. Detached reads | Callers must put primitives in the JSON dict (existing API style) |
| D. Providers do not keep sessions | `release_before_external_wait` at send/HTTP/poll |
| E. Heavy admission before DB | `maybe_reject_heavy_before_db` in outer middleware |
| F. Unskippable cleanup | middleware `finally` + `short_db_phase` finally |
| G. Nested sessions | Reuse scoped session or explicit begin/release; no new hidden `sessionmaker` on hot path |
| H. Bounded history | First-100 `query_bounds_v1` preserved |

`main.py` only: bind request, admit-before-DB, identity-phase close, request-id header.
