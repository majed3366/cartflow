# Migration Lineage Integrity V1.1 — Report

**Date (UTC):** 2026-09-11  
**Status:** AUTHORIZED DSE VERIFICATION + MINIMAL AUTHORITY CORRECTION  
**Empty-DB replay:** FAIL  
**Production create_all authority:** DISABLED  
**Migration lineage integrity:** NOT CLOSED  

## VERDICT

Empty `alembic upgrade heads` cannot build the current schema. Historical revisions ALTER `stores` / index `abandoned_carts` / `recovery_schedules` that Alembic never created. Inventing that foundation was refused.

Production `create_all()` can no longer silently materialize missing tables. Required-schema miss is visible on startup warm and `/health?db=1`.

Production was not upgraded, unstamped, or mutated.

## PHASE 1 — EMPTY REPLAY

| Item | Result |
|------|--------|
| Isolated empty DB | YES (disposable SQLite) |
| `create_all` before upgrade | NO |
| `alembic upgrade heads` | FAIL |
| Failing revision | `n2o3p4q5r6s7` |
| Root cause | `ALTER TABLE stores` — table does not exist |
| Applied before fail | `m1n2o3p4q5r6` (no-op bridge) |
| Parallel root same defect | `a3ff333f6d46` |
| Stub-foundation probe (not shipped) | next fail `o1p2q3r4s5t6` (`abandoned_carts.store_id` missing) |

## PHASE 2–3 — INVENTORY / DIFF

Fresh Alembic schema does not exist (Phase 1 FAIL). Classification is static: Alembic `create_table` set vs live production `cartflow_restore_20260827`.

| Item | Value |
|------|--------|
| Production table count | 57 |
| Fresh Alembic table count | N/A (replay failed) |
| Alembic `create_table` objects in production | ALL PRESENT |
| Alembic-only missing in production | 0 |
| Production stamp | `k1l2m3n4o5p6q7`, `k2l3m4n5o6p7` |
| Purchase Truth rows | 1114 (unchanged) |
| OEF rows | 0 (unchanged) |

### Classification

| Class | Meaning |
|------|--------|
| MATCH | Alembic-created table exists in production (OEF, product mappings, CI tables, dashboard snapshots, …) |
| EXPECTED_DRIFT | Production/create_all owned; no Alembic `CREATE TABLE` (`purchase_truth_records`, `store_identity_aliases`, `stores` base, `abandoned_carts` base, `movement_snapshots`, merchant/recovery/CDC helpers, …) |
| UNEXPLAINED_DRIFT | 0 Alembic-created tables missing in production |

`commercial_decision_commitments` is production-only: no current model, no Alembic file. Owner: retired `create_all` leftover (paid-order contract forbids using it as a ledger). Classed EXPECTED_DRIFT, not unexplained.

### Focus tables

| Table | Class | Note |
|------|--------|------|
| `order_economic_facts` | MATCH | Grain `uq_order_economic_fact_grain` present |
| `purchase_truth_records` | EXPECTED_DRIFT vs Alembic / MATCH vs model | create_all owned; no money columns |
| `store_identity_aliases` | EXPECTED_DRIFT vs Alembic / MATCH vs model | create_all owned |
| `stores` | EXPECTED_DRIFT | Alembic ALTER-only + create_all columns |
| Product persistence | MATCH | catalog / hesitation / purchase / signals / metrics / trends |
| CI persistence | MATCH | syntheses / guidance / findings |
| CDC / movement | EXPECTED_DRIFT | `movement_snapshots` is the lost `p2q3` body |

## PHASE 4–7 — CREATE_ALL

| Site class | Examples |
|------|--------|
| PRODUCTION_STARTUP | `extensions.db.create_all`, `_ensure_cartflow_api_db_warmed` |
| LEGACY | `schema_*.py`, request helpers, `main.py` call sites |
| DEV_BOOTSTRAP | `/admin/init-db`, `/dev/*`, scripts |
| TEST_ONLY | `tests/*` |

| Gate | Before | After |
|------|--------|--------|
| Production `create_all` | ENABLED (silent create) | DISABLED (no-op + log) |
| Missing required table | table appears | startup error + `/health?db=1` 503 |
| Tests / `ENV=development` | create | create |

Phase 7: isolated engine + `CARTFLOW_REFUSE_CREATE_ALL=1` → `create_all` does not create `stores`; `inspect_required_schema` fails visible.

## PHASE 6 — FUTURE PARENT RULE

`future_revision_parent_rule(parent)` requires a real revision already in the walkable map. Empty / unknown parent refused.

## PHASE 8 — PRODUCTION SAFETY

| Action | Done |
|------|--------|
| Historical upgrade on production | NO |
| Unstamp | NO |
| Drop / recreate | NO |
| Data mutation | NO |

## CLOSURE

| Required | Result |
|------|--------|
| EMPTY DB → ALEMBIC HEADS | FAIL |
| FRESH VS PRODUCTION unexplained | 0 Alembic-missing (fresh schema N/A) |
| Production create_all | DISABLED |
| `alembic_version` | PRESENT |
| Graph | WALKABLE |
| Future parent rule | PROVEN |
| Data loss | 0 |
| Lineage integrity closed | NO — empty replay still blocked |

Closing empty replay requires an authorized **pre-Alembic foundation** (real `CREATE TABLE` for `stores`, `abandoned_carts`, `recovery_schedules` as they existed before the first ALTER) — not a stub, not `create_all`.
