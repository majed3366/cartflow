# Migration Lineage Integrity V1

**Status:** AUTHORIZED PRODUCTION SCHEMA AUTHORITY REPAIR  
**Date (UTC):** 2026-09-11  
**Deploy:** exact-SHA required to make Alembic CLI walkable on the API image  
**General release:** NO  
**Level 3:** NO  
**`upgrade head`:** FORBIDDEN in this task

## Problem

Production schema authority had split:

1. **Declared:** Alembic revisions under `alembic/versions/`
2. **Actual:** SQLAlchemy `Base.metadata.create_all()` from `schema_*.py` helpers
3. **Tracking:** live DB `cartflow_restore_20260827` has **no** `alembic_version` table

The revision map itself could not load:

| Missing parent | Referenced by | Intended meaning |
|---|---|---|
| `m1n2o3p4q5r6` | `n2o3p4q5r6s7` (Zid Authorization column) | File never existed in the repo |
| `p2q3r4s5t6u7` | `s1t2u3v4w5x6` merge (Store Reality Simulator Phase 2) | Lost `movement_snapshots` head |

`alembic upgrade k2l3m4n5o6p7` therefore raised `KeyError` before any DDL. Order Economic Fact V1 still landed via `create_all()`.

## Repair (this V1)

1. Reconstruct the two missing graph nodes as **no-op lineage bridges**. No invented historical DDL.
2. Prove the revision map walks. Heads stay `k1l2m3n4o5p6q7` and `k2l3m4n5o6p7`.
3. Stamp **heads only**. Never `upgrade head` (that would replay years of already-applied `create_all` schema).
4. Create `alembic_version` on production so Alembic is the tracking authority going forward.
5. Leave `create_all()` helpers in place for this V1 (coexistence). Do not rip them out here.

## Law

- Alembic CLI must be able to build the revision map.
- Production stamp = `alembic stamp heads` after the graph is walkable.
- `alembic upgrade head` is not an authorized production action in this V1.
- Missing-parent files are bridges, not recovered migrations.
- `movement_snapshots` remains model/`create_all` owned until a later authorized DDL task.
- Scheduler, env, dashboard, OEF money rules: untouched.

## Tests

`tests/test_migration_lineage_integrity_v1.py`
