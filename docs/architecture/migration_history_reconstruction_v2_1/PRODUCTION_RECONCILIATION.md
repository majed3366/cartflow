# Production reconciliation — design only (V2.1)

**V2.1 execute:** NO (design)  
**V2.2 execute:** YES — stamp only. See [`../migration_history_reconstruction_v2_2/`](../migration_history_reconstruction_v2_2/).  
**Production upgrade:** NEVER AUTHORIZED  
**Date (UTC):** 2026-09-11

## Current production physical state (read-only)

| Item | Value |
|------|--------|
| Database | `cartflow_restore_20260827` |
| Stamp | `k1l2m3n4o5p6q7` + `k2l3m4n5o6p7` |
| Live tables | 57 including `commercial_decision_commitments` |
| Purchase Truth rows | 1114 |
| Order Economic Facts | 0 |

Production already contains the reconstructed objects. It was built historically by `create_all` plus later surviving Alembic ALTERs, then **stamp heads only**. The reconstructed CREATE revisions have **never** run there.

## Why upgrade is forbidden

`alembic upgrade` from the current stamp would walk E1–E13 and follow-on CREATEs/ALTERs against tables that already exist. That is a historical replay on live data. This task forbids it.

Do not:

- replay reconstructed CREATE revisions
- drop or recreate tables
- unstamp production
- run historical upgrade blindly

## Candidate later transition (not this task)

Proven in V2.1:

- Fresh empty PostgreSQL + `alembic upgrade heads` → `f10altparity01`
- Full structural parity vs production live objects (CDC excluded as DEPRECATE)
- Unresolved active drift = 0

Expected later concept, **only after a separate authorization**:

```
production physical schema
+ proven full parity
+ existing stamp (k1l2 + k2l3)
→ controlled stamp ONLY to f10altparity01
```

Stamp is not automatically safe. It is safe **only if**:

1. Production schema still matches the last classified inventory (re-inspect immediately before stamp).
2. No one runs `upgrade` from `k1l2`/`k2l3` on production first.
3. CDC remains in place (do not drop).
4. Scheduler SHA and API deploy are handled as a separate authorized change — this reconstruction is repo + isolated proof only.

`if_not_exists` on reconstructed CREATEs is not the production path. It would hide fresh-DB failures.

## After a future authorized stamp

New real schema work revises `f10altparity01`. Fresh installs replay the full graph. Production does not replay E0–E13.

## This task

Production mutated: **NO**  
Production Alembic stamp changed: **NO**  
Production replayed: **NO**
