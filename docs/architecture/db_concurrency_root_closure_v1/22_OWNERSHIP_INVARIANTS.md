# INV-OWN — Request-scoped DB ownership

Binding before the root fix. These do not enlarge the pool or change Scheduler.

| ID | Invariant |
|----|-----------|
| INV-OWN-01 | A request-owned DB session must not be identified or cleaned up solely by OS/Python thread identity. |
| INV-OWN-02 | Every DB checkout created during a request has an explicit logical owner (request id → UoW id → session). |
| INV-OWN-03 | Request completion closes every request-owned session whether work ran on MainThread, an AnyIO worker, or another legitimate request context. |
| INV-OWN-04 | A completed request must not leave a checked-out connection, open transaction, or idle-in-transaction backend unless a separate non-request owner is explicit. |
| INV-OWN-05 | Middleware cleanup closes the session that belongs to the logical request, not whichever `scoped_session` exists on the cleanup thread. |
| INV-OWN-06 | Session ownership and transaction ownership are explicit and testable. |
| INV-OWN-07 | Normal completion, HTTPException, application exception, early return, serialization failure, and cancellation reach deterministic cleanup. |
| INV-OWN-08 | Correctness must not depend on adding cleanup to individual routes. |
