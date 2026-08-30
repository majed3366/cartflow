# Startup unowned checkout — owner identification

Live leftover after `76c0d411` deploy `dea0640c`:

| Field | Value |
|-------|--------|
| Thread | MainThread / Task-2 (Starlette startup task, not `db-ready-startup-warm`) |
| request_id | unowned |
| Last query | `SELECT stores.id AS stores_id, stores.zid_store_id ...` |
| Last event | `[DB CHECKOUT]` at `18:46:50.557Z` — **no matching CHECKIN** |
| Startup complete | `18:46:50.571Z` |

## Path

`_startup_whatsapp_queue` (MainThread)  
→ `seed_demo_store_product_catalog_if_empty()`  
→ `db.session.query(Store).filter(zid_store_id in demo, demo2)`  
→ `updated == 0` → **return without commit/rollback/remove**

No request ContextVar → `scopefunc` fallback `("thr", MainThread ident)` → thread-scoped Session remains registered → QueuePool checkout + Postgres idle in transaction.

Warm thread is a **different** owner: it already `release_scoped_db_session()` in `finally`. The leftover is not that thread.

## Hypotheses

| ID | Verdict |
|----|---------|
| H1 startup uses `db.session` without UoW cleanup | **SUPPORTED** |
| H2 outside request ContextVar → thread scope | **SUPPORTED** |
| H3 startup completes, thread Session remains | **SUPPORTED** |
| H4 no commit/rollback/close on the success-empty path | **SUPPORTED** |
| H5 helper returns ORM while retaining Session | **PARTIAL** (returns int; rows stay attached) |
| H6 lifespan task stays alive holding DB | **FALSIFIED** (hook returns; leftover is scoped Session, not a live task) |
| H7 instrumentation mislabels a valid owner | **FALSIFIED** (unowned is correct) |
| H8 another startup component owns SELECT stores | **FALSIFIED** (only seed queries Store on that hook) |
