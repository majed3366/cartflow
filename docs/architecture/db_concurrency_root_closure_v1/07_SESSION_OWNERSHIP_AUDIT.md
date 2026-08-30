# Phase 6 — Session ownership

## One-sentence answers (binding after this pack)

| Question | Answer |
|----------|--------|
| Who owns the session? | The **request unit-of-work** (`db_lifecycle_v1`), not individual routes. First touch still uses `db.session` (scoped). |
| Who owns the transaction? | The **current short phase**. Implicit transaction; `commit()` only at write call sites. Middleware never commits. |
| Who closes it? | `release_scoped_db_session()` via identity-phase close, `j()`, `release_before_external_wait`, `short_db_phase`, and request `finally`. |
| Who guarantees checkin? | `scoped_session.remove()` + `pool_reset_on_return=rollback`. Ledger records checkin. |

## Before (ambiguous)

- Open: implicit on first `db.session` use
- Close: only middleware `finally`
- Commits: decentralized
- Auth held the checkout across the entire route

## After

- Auth materializes a slug string and closes the phase
- JSON responses close a *clean* session before encode
- Heavy GETs are admitted before auth DB
- `finally` remains the backstop (INV-DB-01)

## Remaining ambiguity (not claimed closed)

Recovery `dispatch` → `execute` → `_run_recovery_sequence` still nest `scoped_db_session_begin`. Scheduler is out of scope; API cart-event `create_task` can still race `remove()` if it runs in the same thread context. Documented; not patched as a route pile.
