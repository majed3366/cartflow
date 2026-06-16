-- CartFlow production schema repair (PostgreSQL / Railway)
-- Run against the database in DATABASE_URL for the production app service.
-- REVIEW: do not delete unused Railway Postgres instances until confirmed.

ALTER TABLE stores
ADD COLUMN IF NOT EXISTS integration_source TEXT;

ALTER TABLE stores
ADD COLUMN IF NOT EXISTS connected_at TIMESTAMP NULL;

ALTER TABLE stores
ADD COLUMN IF NOT EXISTS zid_authorization_token TEXT;

ALTER TABLE stores
ADD COLUMN IF NOT EXISTS merchant_user_id INTEGER NULL;

ALTER TABLE merchant_users
ADD COLUMN IF NOT EXISTS primary_store_id INTEGER NULL;

CREATE INDEX IF NOT EXISTS ix_stores_integration_source
ON stores (integration_source);
