# Migration Lineage Reconciliation V2.2 — Report

**Date (UTC):** 2026-09-11  
**Verdict:** A — MIGRATION_LINEAGE_INTEGRITY_CLOSED  
**General release:** NO

## Closure fields

| Field | Value |
|-------|--------|
| PRE API SHA | `ed277ed738dc3279080818c7cd12bac612d8d9ed` |
| CANDIDATE SHA | `d2f07ce0170a1fd9a33247be2aeefdd4b5726680` |
| POST API SHA | `d2f07ce0170a1fd9a33247be2aeefdd4b5726680` |
| EXACT SHA MATCH | YES |
| DEPLOYMENT ID | `693444f8-b4c1-44f0-b11f-cba234db2584` SUCCESS |
| SCHEDULER SHA | `f91e799d289c99f055ab7edb5cca2063dcd88c9e` UNCHANGED |
| SCHEDULER DEPLOYMENT | `2b1e5665-ae6e-4e5b-9e8a-aa1b205fedf9` UNCHANGED |
| PRE ALEMBIC CURRENT | `k1l2m3n4o5p6q7`, `k2l3m4n5o6p7` |
| CANONICAL HEAD | `f10altparity01` |
| REVISION GRAPH VALID | YES |
| PRE-STAMP ACTIVE SCHEMA PARITY | PASS |
| UNRESOLVED ACTIVE DRIFT | 0 |
| STAMP DRY RUN | PASS |
| PRODUCTION COMMAND TYPE | STAMP ONLY |
| UPGRADE EXECUTED | NO |
| DOWNGRADE EXECUTED | NO |
| PRODUCTION POST-STAMP CURRENT | `f10altparity01` |
| ALEMBIC HEADS | `f10altparity01` |
| BUSINESS TABLE DDL | NO |
| BUSINESS DATA MUTATED | NO |
| TABLE COUNT BEFORE / AFTER | 57 / 57 |
| PT BEFORE / AFTER | 1114 / 1114 |
| OEF BEFORE / AFTER | 0 / 0 |
| SCHEMA FINGERPRINT (column count) | 1031 / 1031 |
| CREATE_ALL PRODUCTION | DISABLED |
| PING / HEALTH / DB HEALTH | 200 / 200 / 200 |
| SCHEMA AUTHORITY | TRUE |
| QUEUEPOOL timeout_count | 0 |
| FORWARD CHILD MIGRATION TEST | PASS (not shipped) |
| COMMERCIAL_DECISION_COMMITMENTS | DEPRECATED / UNTOUCHED (12 rows) |
| NEW TECHNICAL DEBT | NONE |

## Paths

```
k1l2m3n4o5p6q7 → mrgk1k2hd01a → e1…e13 → f1…f10altparity01
k2l3m4n5o6p7 → mrgk1k2hd01a → (same)
```

## Rollback (metadata only)

If stamp verification had failed and physical schema was untouched:

restore `alembic_version` to `k1l2m3n4o5p6q7` + `k2l3m4n5o6p7`.

Not used. Physical schema was unchanged.
