# Product Exposure schema — migration safety (live `57fa657`)

**Date (UTC):** 2026-09-09  
**Mechanism:** SQLAlchemy `create_all()` via `schema_product_exposure_v1.ensure_product_exposure_schema` (same class as catalog).

| Check | Result |
|-------|--------|
| Additive | YES — two new tables only |
| Destructive ALTER | NO |
| Existing table rewrite | NO |
| Idempotent | YES — `CREATE TABLE` / indexes no-op if present |
| Existing runtime coexist | YES — unused tables until first persist |
| Index creation | WITH new tables (`UNIQUE event_id`, 3 raw composites, UNIQUE fact grain) |

**Lock/write impact:** short `ACCESS EXCLUSIVE` on the **new** relations only at first `create_all`. No lock on `stores`, carts, catalog, snapshots. Expected duration: milliseconds on empty new tables.

**Alembic:** not required for V1 (matches catalog pattern). No data backfill.

**Uncertain?** NO.
