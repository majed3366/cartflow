# Migration Lineage Integrity V1.1

**Status:** AUTHORIZED DSE VERIFICATION + MINIMAL AUTHORITY CORRECTION  
**Date (UTC):** 2026-09-11  
**General release:** NO  
**Level 3:** NO  
**Production historical upgrade:** NOT RUN  

Parent: [README.md](README.md) (V1 stamp-heads repair)

## Objective

1. Build current schema from an empty database with Alembic alone.
2. Compare that schema to production.
3. Stop `create_all()` from silently repairing a missing production migration.

## Phase 1 result

`alembic upgrade heads` on an isolated empty SQLite database **fails**.

| Item | Value |
|------|--------|
| First failing revision | `n2o3p4q5r6s7` |
| Error | `ALTER TABLE stores ADD COLUMN zid_authorization_token` — `no such table: stores` |
| Same class | `a3ff333f6d46` (`ADD COLUMN` on `stores`) |
| Next class (if `stores` stubbed) | `o1p2q3r4s5t6` indexes `abandoned_carts(store_id, status, last_seen_at)` and `recovery_schedules` — columns Alembic never created |

Historical roots **alter** pre-Alembic tables. Those tables were created by `create_all()`, never by a `CREATE TABLE` revision. A stub foundation was **not** shipped: inventing the full pre-Alembic column set would rewrite history and still fail the next index.

## Authority correction (shipped)

Production `db.create_all()` is a no-op. Startup warm verifies required tables instead of creating them. `/health?db=1` returns **503** when required tables are missing.

Required tables: `alembic_version`, `stores`, `purchase_truth_records`, `order_economic_facts`, `store_identity_aliases`.

`create_all()` remains for `ENV=development`, pytest, and `CARTFLOW_ALLOW_CREATE_ALL=1`.

## Future revision parent rule

Every new additive revision must have a real parent that already exists in the walkable map. Proven by `inspect_lineage()` + `future_revision_parent_rule()`.

## Tests

- `tests/test_migration_lineage_integrity_v1.py`
- `tests/test_migration_lineage_integrity_v1_1.py`
