# V2.2 Production Deploy Gate

**Date (UTC):** 2026-09-11  
**Method:** Railway GraphQL `serviceInstanceDeployV2` exact SHA, then in-container Alembic **stamp only**.  
**Forbidden:** `alembic upgrade`, `alembic downgrade`, historical CREATE/ALTER, env mutation, Scheduler deploy, autodeploy ON.

## Observed baseline (Phase 1, 2026-09-11, read-only)

| Item | Value |
|------|--------|
| Live API SHA | `ed277ed738dc3279080818c7cd12bac612d8d9ed` |
| API deployment | `f9803e8d-9794-4030-ba36-56f2f584d7cd` SUCCESS |
| Scheduler SHA | `f91e799d289c99f055ab7edb5cca2063dcd88c9e` |
| Scheduler deployment | `2b1e5665-ae6e-4e5b-9e8a-aa1b205fedf9` |
| `alembic_version` | `k1l2m3n4o5p6q7`, `k2l3m4n5o6p7` |
| Tables | 57 (includes deprecated `commercial_decision_commitments`) |
| Purchase Truth | 1114 |
| OrderEconomicFact | 0 |
| Autodeploy | OFF |

## Candidate

| Item | Value |
|------|--------|
| Worktree | `C:\Users\Toshiba\Desktop\cartflow-mhr-v22` |
| Branch | `candidate/migration-lineage-reconciliation-v2-2` |
| Parent | `ed277ed738dc3279080818c7cd12bac612d8d9ed` |
| Overlay | Reconstruction revisions E0–E13, merge, f1–f10; three approved `down_revision` reparents; stamp-from-ancestors helper |

## Stamp command (production)

```
CARTFLOW_REFUSE_CREATE_ALL=1 python scripts/stamp_canonical_from_ancestors.py --execute
```

Rollback metadata only (if stamp verification fails and physical schema is untouched):

restore `alembic_version` to `k1l2m3n4o5p6q7` + `k2l3m4n5o6p7`.

## Post-deploy / post-stamp

Filled after execution.
