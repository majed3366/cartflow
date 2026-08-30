# Binding invariants (INV-DB-01 … INV-DB-12)

Documented **before** implementation. These are testable laws, not aspirations.

| ID | Invariant | Test | Production proof |
|----|-----------|------|------------------|
| **INV-DB-01** | Every request-scoped DB session is closed on every exit path (return, HTTPException, unhandled error, early 401/302, admission 503). | Failure-injection: after each case, scoped session is removed and QueuePool `checked_out` returns to baseline. | After a request ends, ledger `open_holds=0` for that `request_id`. |
| **INV-DB-02** | A DB connection is not held across external HTTP/network waits. | Choke-point contract + VIP poll must call `release_before_external_wait` before provider I/O; ledger `network_while_held` must be 0 on approved paths. | `[DB HOLD] network=True` is a violation. |
| **INV-DB-03** | A DB transaction is not held across expensive non-DB computation (JSON render, template generation, sleeps). | `j()` releases the scoped session before encode; auth identity is materialized then released before `call_next`. | Hold ms ≈ last SQL, not response wall time. |
| **INV-DB-04** | Inactive Merchant surfaces perform zero startup product work. | Preserved from `58a82f3` lazy-init; no new surface init on this line. | Inactive-surface request count = 0 on dashboard first paint. |
| **INV-DB-05** | Same-surface initialization is idempotent and does not create duplicate in-flight work. | Existing same-page cache / lazy init contracts remain. | Duplicate identical GET during one paint = 0. |
| **INV-DB-06** | High-frequency reads are explicitly bounded. | Named caps in `query_bounds_v1`; no new unbounded `.all()` on hot paths. | Messages / carts / followups honor caps. |
| **INV-DB-07** | Heavy routes have bounded concurrent execution. | Global 4 / per-route 2; middleware admits **before** auth DB. | Admission `rejected` increments without extra checkout. |
| **INV-DB-08** | Admission rejection itself does not acquire/retain a DB connection. | Rejected heavy GET never calls `resolve_authenticated_store_slug` / route DB. | Rejected request: ledger checkouts = 0. |
| **INV-DB-09** | Authentication and critical health cannot be starved by optional heavy product reads under expected traffic. | `/ping` and `/health` (no `db=1`) take no checkout; `/login` is not a heavy class; heavy admission reserves slots. | Under Communication/Workspace load, `/ping` stays 200 and `/login` stays off the 5s pool-timeout path. |
| **INV-DB-10** | After traffic stops, DB checkout count returns to idle equilibrium without restart. | Equilibrium harness: BASELINE → ACTIVITY → QUIESCENCE → `checked_out` == baseline. | Idle Stage 0: no leftover checkouts, no idle-in-transaction. |
| **INV-DB-11** | Every abnormal long DB hold is attributable to a request/route owner. | Ledger row has `request_id`, `route`, `method`, `connection_id`. | Long-hold warning includes those fields (no secrets). |
| **INV-DB-12** | Production health reflects real QueuePool and real DB probe state, not a `status()` string without numeric checkout. | `/health` includes in-process pool numbers without a checkout; `/health?db=1` is an honest probe or honest `pool_pressure`. | Health JSON `pool.checked_out` matches SQLAlchemy `pool.checkedout()`. |

## Non-invariants (explicitly out of scope)

- Enlarging `pool_size` / `max_overflow` / `pool_timeout`
- Scheduler process or due-scanner enablement
- First-100 soak (paused until single-merchant equilibrium is proven on QueuePool + production)
- Visual assimilation
