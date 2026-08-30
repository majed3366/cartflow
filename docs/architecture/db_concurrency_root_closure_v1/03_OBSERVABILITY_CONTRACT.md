# Observability contract

Implemented **before** claiming remediation. No SQL parameters, tokens, phones, or customer payloads.

## Always-on (production-safe)

| Field | Source |
|-------|--------|
| request_id | `X-CartFlow-Request-Id` / generated hex16 |
| route, method | request owner context |
| merchant slug | bound after auth resolve (identifier only) |
| session id | `id(db.session)` when first checkout |
| connection identity | `pg:<backend_pid>` or `rec:<id>` |
| checkout / checkin timestamps | pool listeners |
| hold_ms | checkin − checkout |
| request start/end | owner `t0` / `request_ms` |
| current / peak checked_out | `pool.checkedout()` numeric |
| overflow | `pool.overflow()` |
| timeout_count | `handle_error` QueuePool / timed out |
| admission | `n/a` / `admitted` / `rejected` / `skip_unauthenticated` |
| outcome | HTTP status or `exception` |

## Long hold

Structured warning at **≥ 1000 ms** hold: `[DB LONG HOLD] request_id= route= method= conn= hold_ms= merchant=`

## Health (INV-DB-12)

`GET /health` (no `db=1`) attaches in-process `pool` numbers **without a checkout**.  
`GET /health?db=1` remains an honest probe or honest `pool_pressure` 503.

## Not done

- Per-query global SQL logging
- Admin UI
- Transaction start/end timestamps (SQLAlchemy 1.4/2.0 events not wired; classify via pg_stat_activity when Postgres is available)
