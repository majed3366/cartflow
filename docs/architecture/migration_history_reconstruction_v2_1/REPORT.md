# Migration History Reconstruction V2.1 — Report

**Date (UTC):** 2026-09-11  
**Verdict:** **A — RECONSTRUCTION_IMPLEMENTED_AND_READY_FOR_PRODUCTION_RECONCILIATION**

## Closure

| Gate | Result |
|------|--------|
| 22 B-class historical CREATEs | IMPLEMENTED |
| Historical confidence | HIGH |
| PostgreSQL replay #1 | PASS |
| PostgreSQL replay #2 | PASS |
| create_all required | NO |
| App boots on fresh Alembic DB | YES |
| Full active schema parity | PASS |
| Unresolved active drift | 0 |
| Production data mutation | 0 |
| Production historical replay | 0 |
| Production stamp change | 0 |
| New technical debt | NONE |

## Replay

Starting schema: **EMPTY** (disposable PostgreSQL, `pgembed` 17.9)

Ending heads: **`f10altparity01`**

Revision count applied: **66**

Warnings: Alembic console encoding substitution on Windows (non-fatal). No migration warnings that changed schema.

Errors: none

Replay #2 destroyed the first database and rebuilt from another empty database. Deterministic: yes.

## Parity (fresh Alembic PostgreSQL vs production `cartflow_restore_20260827`)

| Axis | Result |
|------|--------|
| Tables | MATCH (CDC production-only) |
| Columns | MATCH |
| Types | MATCH |
| Nullability | MATCH |
| Defaults | MATCH |
| PK | MATCH |
| FK | MATCH |
| Unique | MATCH |
| Indexes | MATCH |

Expected deprecated drift: `commercial_decision_commitments` (DEPRECATE)

Unresolved active drift count: **0**

Production stamp unchanged: `k1l2m3n4o5p6q7` + `k2l3m4n5o6p7`  
PT 1114 / OEF 0 (read-only inspect)

## Lineage

- Bases: `e0fnd250425a`, `p2q3r4s5t6u7`
- Head: `f10altparity01`
- Existing IDs modified (down_revision only): `a3ff333f6d46`, `m1n2o3p4q5r6`, `o1p2q3r4s5t6`
- `p2q3r4s5t6u7` remains no-op (no `movement_snapshots` DDL)
- `m1n2o3p4q5r6` remains no-op

## Follow-on ALTER revisions

`f1altreason01a` … `f9altlclose01` add later create_all-era columns without rewriting birth CREATEs.

`f10altparity01` aligns remaining physical leftovers (types, nullability, server defaults, `stores.merchant_user_id` FK, indexes) to current production.

## Runtime

Fresh Alembic PostgreSQL `cartflow_fresh_hold`:

- `CARTFLOW_REFUSE_CREATE_ALL=1`, `CARTFLOW_PROCESS_ROLE=api`
- `/ping` 200
- `/health?db=1` 200, `schema_authority.ok=true`
- Startup warm: `create_all refused`

## Production

Not mutated. Not stamped. Not replayed. Reconciliation design only: [`PRODUCTION_RECONCILIATION.md`](PRODUCTION_RECONCILIATION.md)

## Tests

`tests/test_migration_history_reconstruction_v2_1.py`  
`tests/test_migration_lineage_integrity_v1.py`  
`tests/test_migration_lineage_integrity_v1_1.py`

Authoritative replay: `scripts/migration_history_reconstruction_v2_1_postgres_replay.py`  
Fresh boot: `scripts/migration_history_reconstruction_v2_1_fresh_boot.py`

## Stop

Migration lineage integrity: **NOT CLOSED**  
General release: **NO**  
Deploy: **NO**
