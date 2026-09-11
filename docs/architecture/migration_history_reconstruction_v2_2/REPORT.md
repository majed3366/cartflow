# Migration Lineage Reconciliation V2.2 — Report

**Date (UTC):** 2026-09-11  
**General release:** NO

## Pre-stamp gates (local)

| Gate | Result |
|------|--------|
| Fresh PostgreSQL replay to `f10altparity01` | PASS (twice, V2.1) |
| Production structural parity | PASS |
| Unresolved active drift | 0 |
| `commercial_decision_commitments` | EXPECTED_DEPRECATED_DRIFT |
| Revision graph | VALID — both production heads are ancestors of `f10altparity01` |
| Stamp dry-run (disposable PG, ancestors → stamp) | PASS — physical schema identical; Alembic logged `stamp_revision` not upgrade |
| Stamped disposable boot | PASS — `/ping` 200, `/health?db=1` 200, `schema_authority.ok` true, `create_all` refused |

## Paths

```
k1l2m3n4o5p6q7 → mrgk1k2hd01a → e1…e13 → f1…f10altparity01
k2l3m4n5o6p7 → mrgk1k2hd01a → (same)
```

## Production mutation

See [`PRODUCTION_DEPLOY_GATE.md`](PRODUCTION_DEPLOY_GATE.md).
