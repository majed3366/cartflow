# V2.2 Production Deploy Gate

**Date (UTC):** 2026-09-11  
**Status:** CLOSED  
**Method:** Railway GraphQL `serviceInstanceDeployV2` exact SHA, then in-container Alembic **stamp only**.  
**Forbidden actions not run:** `alembic upgrade`, `alembic downgrade`, historical CREATE/ALTER, env mutation, Scheduler deploy, autodeploy ON.

## Phase 1 baseline (read-only)

| Item | Value |
|------|--------|
| Live API SHA | `ed277ed738dc3279080818c7cd12bac612d8d9ed` |
| API deployment | `f9803e8d-9794-4030-ba36-56f2f584d7cd` SUCCESS |
| Scheduler SHA | `f91e799d289c99f055ab7edb5cca2063dcd88c9e` |
| Scheduler deployment | `2b1e5665-ae6e-4e5b-9e8a-aa1b205fedf9` |
| `alembic_version` | `k1l2m3n4o5p6q7`, `k2l3m4n5o6p7` |
| Tables | 57 |
| Purchase Truth | 1114 |
| OrderEconomicFact | 0 |
| CDC rows | 12 |
| Autodeploy | OFF |

## Candidate

| Item | Value |
|------|--------|
| Worktree | `C:\Users\Toshiba\Desktop\cartflow-mhr-v22` |
| Branch | `candidate/migration-lineage-reconciliation-v2-2` |
| Parent | `ed277ed738dc3279080818c7cd12bac612d8d9ed` |
| Candidate SHA | `d2f07ce0170a1fd9a33247be2aeefdd4b5726680` |

## Deploy

| Item | Value |
|------|--------|
| Command | `serviceInstanceDeployV2` exact SHA only |
| Deployment | `693444f8-b4c1-44f0-b11f-cba234db2584` SUCCESS |
| Post-deploy SHA (`GET /`) | `d2f07ce0170a1fd9a33247be2aeefdd4b5726680` |
| Post-deploy alembic | still `k1l2` + `k2l3` |
| Post-deploy tables / PT / OEF | 57 / 1114 / 0 |
| Schema changed by deploy | NO |

## Stamp

Pre-reconciliation rows: `k1l2m3n4o5p6q7`, `k2l3m4n5o6p7`

Command:

```
CARTFLOW_REFUSE_CREATE_ALL=1 python scripts/stamp_canonical_from_ancestors.py --execute
```

Alembic log: `Running stamp_revision k1l2m3n4o5p6q7, k2l3m4n5o6p7 -> f10altparity01`

After: `alembic_version = f10altparity01`. Tables 57, columns 1031, PT 1114, OEF 0, CDC 12.

## Post-stamp health

`/ping` 200, `/health` 200, `/health?db=1` 200, `schema_authority.ok` true, QueuePool `timeout_count` 0, Scheduler unchanged.
