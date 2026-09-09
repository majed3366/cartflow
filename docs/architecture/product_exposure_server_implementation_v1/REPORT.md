# CartFlow — Product Exposure Server Implementation V1

**Status:** IMPLEMENTED · local proof complete  
**Date (UTC):** 2026-09-09  
**Deploy:** NO · **API Exact-SHA deploy:** NO · **Scheduler deploy:** NO · **Storefront wire:** NO  
**AI calls:** 0 · **External API calls:** 0  
**NEW TECHNICAL DEBT:** NONE

Tests: `tests/test_product_exposure_server_v1.py` (36) + CORS path coverage in `tests/test_cartflow_storefront_cors_v1.py` + API startup isolation in `tests/test_cost_recurrence_prevention_v1.py`.  
Result: **36/36 exposure tests passed**; CORS + startup isolation passed.

---

## Schema

### `product_exposure_events` (`ProductExposureEvent`)

Insert-only raw SoT while retained (HOT 0–30 UTC days).

| Column | Notes |
|--------|--------|
| `id` | PK |
| `event_id` | UNIQUE transport idempotency |
| `store_slug` | canonical `stores.zid_store_id`, never client alias |
| `product_id` | opaque catalog id |
| `session_id` | syntax-only anonymous session |
| `page_context` | `pdp` |
| `occurred_at` | admitted client UTC |
| `received_at` | server UTC |
| `source` | `storefront_widget_v1` |
| `truth_version` | `exposure_v1` |
| `commercial_dedupe_key` | `store\|session\|product\|pdp` |
| `commercial_bucket` | persisted row `occurred_at` truncated to seconds |
| `commerce_platform` | adapter enum (`zid` / `unknown` / …) — not a Zid column |
| `identity_source` | `storefront_runtime` |
| `event_source` | `cartflow_storefront` |
| `referrer_domain` | optional hostname only |
| `claimed_utm_*` | optional claimed metadata |
| `lab_flag` | default false; merchant path never inserts lab |

Not stored: phone, email, name, full URL, cookies, tokens, raw query string.

### `product_exposure_daily_facts` (`ProductExposureDailyFact`)

Grain: UNIQUE `(store_slug, product_id, date_utc)` where `date_utc` is admitted `occurred_at` UTC date (`YYYY-MM-DD`).

| Column | Notes |
|--------|--------|
| `pdp_view_count` | +1 per commercially persisted raw row only |
| `viewing_session_count` | distinct `session_id` with ≥1 persisted row that UTC day |
| `truth_version` | `exposure_v1` |
| `sealed_at` | NULL until seal |
| `seal_truth_version` | `exposure_v1` on seal |
| `seal_source_window_start/end` | `[date 00:00, next date 00:00)` |
| `seal_source_row_count` | raw COUNT(*) for that product-day |

No helper tables.

Migration: SQLAlchemy `create_all` via `schema_product_exposure_v1.ensure_product_exposure_schema` (same pattern as catalog). No Alembic in this bundle.

---

## Indexes

| Name | Columns | Owner / purpose |
|------|---------|-----------------|
| `uq_product_exposure_event_id` | UNIQUE `event_id` | Transport idempotency + concurrent replay |
| `ix_pex_commercial_seq` | `(store_slug, session_id, product_id, page_context, occurred_at)` | Last persisted commercial lookup (30m window) |
| `ix_pex_session_day` | `(store_slug, product_id, session_id, occurred_at)` | `viewing_session_count` COUNT against raw for that UTC day |
| `ix_pex_store_time` | `(store_slug, occurred_at)` | Retention / seal candidate scan |
| `uq_pex_daily_facts_grain` | UNIQUE `(store_slug, product_id, date_utc)` | Inline UPSERT |

No extra indexes. Sliding 30m window is **not** a hash-bucket unique index (avoids hour-boundary splits).

---

## Endpoint contract

`POST /api/storefront/product-viewed`

Allowlist keys only. Body max 2048 bytes. CORS path added (transport only — not tenant proof).

| HTTP | Meaning |
|------|---------|
| 200 `{ok, persisted, reason}` | `persisted` \| `idempotent_replay` \| `commercial_dedupe` |
| 400 | malformed JSON/fields/session/event_id; `unknown_field` |
| 403 | `missing_origin` `invalid_origin` `unknown_store` `store_origin_mismatch` `lab_tenant_forbidden` |
| 413 | `payload_too_large` |
| 422 | `product_not_owned` `clock_*` `unknown_source` enum |
| 429 | `rate_limited` |
| 503 | `unavailable` |

No stack traces in client JSON.

Rate limits (in-process, test-disableable): 120/min/origin host, 20/min/session, 600/min/store.

---

## Tenant authority proof

Path: `Origin` → `origin_adapter_v1` (Zid `*.zid.store` permalink extraction **adapter-only**) → `StoreIdentityAlias` / `resolve_store_row_by_identifier` → canonical Store. Payload `store_slug` must resolve to the **same Store.id**. Client slug is never authority. Lab slugs `demo`/`demo2`/`default` → 403. Missing Origin → 403. HTTP Origin → 403.

Core persist/facts have no `*.zid.store` matching.

---

## Product ownership proof

Exact `(canonical_store_slug, product_id)` on `ProductCatalogEntry`. No name/SKU/slug fallback, no create, no Zid Products API. Miss → 422 `product_not_owned`. Deleted catalog row: new ingest 422; historical raw retained until retention.

---

## Event time / session

- `received_at` server-owned.
- Admit `occurred_at` in `[received_at − 15m, received_at + 120s]`.
- Session `^s_[A-Za-z0-9-]{8,64}$` syntax-only. Not auth. Not unique visitors.

---

## Transport idempotency / commercial dedupe

- UNIQUE `event_id`: replay 200 `idempotent_replay`; no second row; no fact increment. Concurrent UNIQUE → IntegrityError → replay.
- Commercial: same store+session+product+`pdp`; last **persisted** `occurred_at`; duplicate iff `0 ≤ Δ < 1800s`.
  - **29:59** duplicate
  - **30:00** new
  - **30:01** new
- Midnight does **not** reset the 30m window.
- Not epoch-bin hashing.

Lock: Postgres `pg_advisory_xact_lock(hash(commercial_dedupe_key))`. SQLite tests: per-key lock + process write lock as dialect stand-in (not a production store-wide mutex).

---

## Transaction proof

Raw INSERT + fact UPSERT in **one** SQLAlchemy commit.

| Failure | Result |
|---------|--------|
| Raw flush then injected fail | rollback; 0 rows |
| Fact upsert injected fail | rollback; 0 rows |
| Commit then “unknown outcome” | row stored; retry same `event_id` → replay; facts not double-counted |
| DB raise | 503 `unavailable`; no row |

**PARTIAL WRITE POSSIBLE: NO**

Ingest does **not** DELETE (opportunistic cleanup withdrawn). Retention is Scheduler-only.

---

## View counts

- `pdp_view_count` += 1 only on commercial persist.
- `viewing_session_count` += 1 iff COUNT of raw rows for `(store, product, session, UTC day)` after insert is 1 (SQL, not +1 per row, no store mutex).
- Same session two persists ≥30m apart same UTC day: views 2, sessions 1.

Rebuild: GROUP BY raw, **replace** counts. Sealed+raw mismatch: unseal → replace.

---

## Seal / retention proof

Tick: `exposure_retention_tick_v1` in existing Scheduler via `run_scheduler_drivers_at_startup`, **only if** `CARTFLOW_EXPOSURE_RETENTION_ENABLED` is on. Default **OFF**. Cadence 3600s (min 300). Skip if tick lock held. Oldest-first. ≤20 store-days seal, ≤200 raw deletes, ≤50 sealed fact deletes. Fact DELETE is a **separate** statement from raw DELETE.

Seal: recompute coverage + view count + session count + raw row_count; match → set `sealed_at` + metadata; mismatch → leave raw, `fact_seal_failure_total`.

Raw delete only if `occurred_at` date `< utc_today − 30 days` **and** store-day fully sealed. Fail closed otherwise.

Facts: delete sealed rows with `date_utc < utc_today − 400`. Bound 50.

HOT authority: raw. COLD (raw gone): sealed fact. Missing/corrupt cold fact: historical unknown — never paint zero. Not rebuildable.

---

## Scheduler isolation

| Check | Result |
|-------|--------|
| API `_startup_whatsapp_queue` starts retention loop | NO |
| Retention loop/tick import WhatsApp / recovery due-scan / purchase stop | NO |
| Recovery due-scanner imports exposure | NO |
| Cadence class | 3600s sibling of snapshot archive, not 30s due-scan |
| Own asyncio lock | YES |
| Default enabled | NO |

Scheduler **not deployed** in this task.

---

## Query counts / performance (local SQLite pytest)

| Metric | Measured bound |
|--------|----------------|
| Persist TX statements | 6–8 (lock, event_id, last commercial, insert, session COUNT, fact UPSERT) |
| Endpoint wall | < 2000 ms (pytest SQLite; typically far lower) |
| Retention tick queries | ≤ 40 in tests |
| Retention wall | < 5000 ms in tests |
| N+1 on ingest | **0** (no per-product loop) |
| Write amplification | **×2** on persist (raw + fact). Replay/dedupe/reject: ×0 extra commercial writes |
| AI | **0** |
| External API | **0** |

Products UI: **not wired**. Catalog read module has no exposure join. Fanout remains CLOSED.

### Capacity (economics, not live)

~330 commercially persisted PDP events / merchant / day (design envelope).

| Merchants | Writes/day (×2) | Status |
|-----------|-----------------|--------|
| 100 | ~66k | OK |
| 500 | ~330k | OK |
| 1000 | ~660k | OK-ish |
| 10000 | — | **NOT READY** |

---

## Failure matrix

| Case | Result |
|------|--------|
| duplicate event_id | idempotent_replay |
| commercial duplicate | commercial_dedupe |
| 29:59 / 30:00 / 30:01 | dup / new / new |
| invalid / missing origin | 403 |
| store mismatch | 403 store_origin_mismatch |
| foreign / missing product | 422 product_not_owned |
| invalid product id | 400 |
| invalid / missing session | 400 |
| clock too old / future | 422 |
| oversized payload | 413 |
| unknown source | 422 |
| unknown field (url etc.) | 400 |
| DB unavailable | 503 |
| TX rollback raw/fact | 0 rows |
| unknown commit + retry | replay, no double increment |
| concurrent same event_id | one persist, one replay |
| concurrent same session/product | one persist, one commercial_dedupe |
| midnight vs 30m | still commercial_dedupe |
| daily 23:59:59 / 00:00:00 | dates D / D+1 |
| fact update race | ON CONFLICT increment |
| seal valid | sealed_at set; raw deleted |
| seal mismatch | raw kept |
| raw delete without seal | blocked |
| cleanup restart/retry | idempotent |
| quiet merchant | tick seals without new ingest |
| large backlog | ≤20 store-days / tick |
| facts >400d sealed | bounded fact DELETE |
| product deleted | history kept; new ingest 422 |
| tenant purge | bounded; other tenant intact |
| lab tenant | 403 |
| rate limit | 429 |

---

## Observability

In-process low-cardinality counters (no `product_id` / `session_id` / high-card `store_slug` labels):  
`exposure_requests_total`, `exposure_persisted_total`, `exposure_idempotent_replay_total`, `exposure_commercial_dedupe_total`, `exposure_rejected_total`, `exposure_db_failures_total`, `retention_run_total`, `retention_failure_total`, `retention_rows_deleted_total`, `retention_fact_rows_deleted_total`, `fact_seal_success_total`, `fact_seal_failure_total`, gauges `unsealed_days_past_retention_total`, `retention_oldest_raw_age_days`.

---

## FINAL REPORT

IMPLEMENTATION STATUS: **COMPLETE (local proof; not deployed)**

ENDPOINT: **YES** `POST /api/storefront/product-viewed`

RAW TABLE: **YES** `product_exposure_events`

FACT TABLE: **YES** `product_exposure_daily_facts`

MIGRATION: **YES** `schema_product_exposure_v1.ensure_product_exposure_schema` (`create_all`)

INDEXES: **5** (see table above)

TENANT AUTHORITY: **YES** Origin adapter → alias → Store; payload slug must match Store.id

PRODUCT OWNERSHIP: **YES** exact catalog `(canonical_store_slug, product_id)`

MISSING PRODUCT: **422 product_not_owned**

EVENT TIME CONTRACT: **YES** received_at server; −15m / +120s

SESSION CONTRACT: **YES** `^s_[A-Za-z0-9-]{8,64}$` syntax-only

TRANSPORT IDEMPOTENCY: **YES** UNIQUE `event_id` → `idempotent_replay`

COMMERCIAL DEDUPE: **YES** half-open 30m on last persisted `occurred_at`

29:59: **duplicate**  
30:00: **new**  
30:01: **new** (vs the same last persist `t0`; not a chained window)

RAW + FACT ATOMIC: **YES**

PARTIAL WRITE POSSIBLE: **NO**

PDP VIEW COUNT: **+1 per commercially persisted exposure only**

VIEWING SESSION COUNT: **SQL COUNT distinct session with ≥1 raw row that UTC day**

CONCURRENCY PROOF: **YES** (event_id UNIQUE; commercial lock + same-timestamp second → dedupe)

HOT TRUTH OWNER: **raw events (0–30d)**

COLD TRUTH OWNER: **sealed daily facts (31–400d)**

SEAL IMPLEMENTED: **YES**

SEAL VALIDATION: **YES** (coverage + views + sessions + row_count)

RAW RETENTION: **30d; delete only if store-day fully sealed; ≤200/tick**

FACT RETENTION: **400d sealed only; ≤50/tick; separate SQL**

RETENTION OWNER: **existing Scheduler** `exposure_retention_tick_v1`

RETENTION TICK: **YES** (code present)

RETENTION DEFAULT ENABLED: **NO**

SCHEDULER ISOLATION: **YES** (own loop/lock; API does not start it; no WhatsApp/due-scan)

PRODUCTS QUERY FANOUT REOPENED: **NO**

N+1: **0**

AI CALLS: **0**

EXTERNAL API CALLS: **0**

NEW TECHNICAL DEBT: **NONE**

TEST COUNT / RESULTS: **36/36 exposure passed**; CORS path + API startup isolation passed

ENDPOINT WALL TIME: **< 2000 ms** (pytest SQLite bound)

RETENTION WALL TIME: **< 5000 ms** (pytest SQLite bound)

100 MERCHANT COST: **OK** (~66k writes/day at ×2 amp, design envelope)

500 MERCHANT COST: **OK**

1000 MERCHANT COST: **OK-ish**

10000 MERCHANT STATUS: **NOT READY**

PE-RET-001: **CLOSED**

PE-SEAL-001: **CLOSED**

PRODUCTS_READ_MODEL_QUERY_FANOUT_V1: **CLOSED**

READY FOR CLEAN RUNTIME CANDIDATE: **YES**

READY FOR API EXACT-SHA DEPLOY: **NO**

READY FOR SCHEDULER DEPLOY: **NO**

READY FOR STOREFRONT WIRING: **NO**

DEPLOY: **NO**

STOP.
