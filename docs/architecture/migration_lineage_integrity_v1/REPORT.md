# Migration Lineage Integrity V1 — Report

**Date (UTC):** 2026-09-11  
**Status:** AUTHORIZED PRODUCTION SCHEMA AUTHORITY REPAIR

## VERDICT

**A — LINEAGE WALKABLE; STAMP HEADS ONLY**

The repo graph is repaired with two no-op bridges. Alembic can load the revision map. Production tracking is restored by stamping the two current heads. Historical `upgrade` is not run.

## BEFORE

- `KeyError: m1n2o3p4q5r6` (and the same class of break for `p2q3r4s5t6u7`)
- Live `alembic_version`: ABSENT
- Schema owner in practice: `create_all()`
- OEF table existed; Alembic could not record `k2l3m4n5o6p7`

## AFTER (repo)

| Item | Result |
|------|--------|
| `m1n2o3p4q5r6` file | YES (no-op bridge, `down_revision=None`) |
| `p2q3r4s5t6u7` file | YES (no-op bridge, `down_revision=None`) |
| Map walkable | YES |
| Heads | `k1l2m3n4o5p6q7`, `k2l3m4n5o6p7` |
| Bases | `a3ff333f6d46`, `m1n2o3p4q5r6`, `p2q3r4s5t6u7` |
| `upgrade head` executed | NO |

## AUTHORITY

| Layer | Role after V1 |
|------|--------|
| Alembic revision map | Must load. Blocking defect if it does not. |
| `alembic_version` | Tracking authority for future additive revisions. |
| `create_all()` helpers | Still present. Not removed. Not a substitute for a walkable map. |
| `upgrade head` on production | Forbidden in this V1. |

## SAFE NEXT MIGRATION

New revision revises **both** heads or a later merge. Do not attach a new file to a missing parent. Run `inspect_lineage()` in CI.

## NOT DONE

- Reconstruct `movement_snapshots` Alembic DDL
- Remove `create_all()` from schema helpers
- Merge the two heads into one
- Level 3 / OEF write / dashboard / Scheduler
