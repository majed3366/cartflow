# Production database schema repair (v1)

**Status:** Active — run before continuing signup/OAuth debugging.

## 1. Which database is production using?

After deploy, read Railway logs for:

```text
[PRODUCTION DB IDENTITY] context=startup scheme=postgresql host=... database=...
```

That `host` + `database` pair is the Postgres instance bound to the **app service** `DATABASE_URL`. Compare with Railway → Project → Postgres plugin → Connect. If they differ, the app may be pointed at the wrong DB (**REVIEW** — do not delete other Postgres services until confirmed).

## 2. Manual repair SQL (PostgreSQL)

Run on the database from step 1 (`scripts/production_store_schema_repair.sql`):

```sql
ALTER TABLE stores ADD COLUMN IF NOT EXISTS integration_source TEXT;
ALTER TABLE stores ADD COLUMN IF NOT EXISTS connected_at TIMESTAMP NULL;
ALTER TABLE stores ADD COLUMN IF NOT EXISTS merchant_user_id INTEGER NULL;
ALTER TABLE merchant_users ADD COLUMN IF NOT EXISTS primary_store_id INTEGER NULL;
CREATE INDEX IF NOT EXISTS ix_stores_integration_source ON stores (integration_source);
```

## 3. Automatic repair (app startup)

`ensure_production_store_schema()` runs on:

- App startup (`_ensure_cartflow_api_db_warmed`)
- First HTTP request (`production_store_schema_middleware`)
- Signup / Zid OAuth entry points

Expected logs:

```text
[PRODUCTION DB IDENTITY] context=startup ...
[MERCHANT AUTH SCHEMA] context=startup ok=true ...
[STORE ZID SCHEMA] context=startup ok=true columns=integration_source,connected_at
[PRODUCTION DB SCHEMA] context=startup ok=true
```

## 4. Unused Railway databases

Other empty Postgres instances in the project: mark **REVIEW** only; do not delete until `DATABASE_URL` identity is confirmed.

## 5. Verification order

1. Redeploy — no `UndefinedColumn: stores.integration_source`
2. Schema logs `ok=true`
3. Retry `POST /signup` — if 400, capture `[SIGNUP 400]`
4. Only then continue `merchant_session_no_store` / OAuth
