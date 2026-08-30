# Phase 3 — Postgres + SQLAlchemy reconciliation

**Law:** Do not call a leak unless both sides support it.

## SQLAlchemy side (implemented)

`services/db_lifecycle_v1/pool_truth.py` + checkout/checkin ledger:

- `checked_out`, `checked_in`, `overflow`, `size`, `peak_checked_out`, `timeout_count`
- Open holders: request_id, route, method, connection_id, hold_ms

## Postgres side (implemented, runs only on PostgreSQL)

`services/db_lifecycle_v1/pg_reconciliation.py` reads `pg_stat_activity` **without query text**:

pid, state, xact_start, query_start, state_change, wait_event_type, wait_event, application_name, client_addr, backend_type

Classification: `ACTIVE_QUERY` | `IDLE` | `IDLE_IN_TRANSACTION` | `LOCK_WAIT` | `UNKNOWN`

Reconcile verdicts: `EQUILIBRIUM` | `IDLE_IN_TRANSACTION_PRESENT` | `SA_CHECKED_OUT_PG_NO_IIT` | `PG_UNAVAILABLE` | `SA_METRICS_UNAVAILABLE`

`leak_claimed` is **always false** unless a future operator marks both-sides evidence.

## This freeze

| Side | Result |
|------|--------|
| Local SQLite tests | QueuePool numeric truth only; `PG_UNAVAILABLE` |
| Production `pg_stat_activity` | **NOT_RUN** — Railway GraphQL unauthorized; no living `DATABASE_URL` used |
| Production idle-in-transaction | **UNKNOWN** |

Do not treat First-100 NullPool numbers as reconciliation.
