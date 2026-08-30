# ADR — DB resource model

**Status:** Binding for future CartFlow work.  
**Date:** 2026-08-30

## Decision

CartFlow keeps a **single process-wide QueuePool** (API 5+5+5s) and a **request unit-of-work**:

1. **Session ownership:** request lifecycle module; lazy `db.session`; no `get_db` dependency required.
2. **Transaction ownership:** short phase only; writes `commit()` at the persist site; release always `rollback` leftover.
3. **External I/O rule:** release before HTTP/sleep/provider wait.
4. **Query-bound rule:** named caps on history/bulk hot paths; no unbounded `.all()` on those paths.
5. **Heavy-route concurrency:** global 4 / per-route 2; admit before auth DB for always-heavy GETs.
6. **Observability:** request_id + route + connection identity + numeric pool counters + long-hold warn.
7. **Equilibrium:** after traffic, `checked_out` returns to idle without restart.
8. **Acceptable pool behavior:** brief checkout up to 10; timeouts are incidents, not capacity planning.
9. **New infrastructure** (replicas, Redis, larger pool) is justified only after short-hold + admission still saturate **with** both-sides PG reconciliation.

## Consequences

- Do not add route-local pool workarounds.
- Do not enlarge the pool to hide hold time.
- `main.py` stays composition/wiring.
