# DB pressure audit — CartFlow (temporary instrumentation)

This document captures **how to read the new logs**, **static hotspots** found in the codebase (no production traffic sample), and **suspected architectural causes**. It is meant to **guide the next optimization pass** — not to apply blind caching or pool-size increases.

## 1. Instrumentation added (temporary)

**Module:** `services/db_request_audit.py`  
**Wiring:** HTTP middleware `db_scoped_session_cleanup` in `main.py` (same `finally` as `remove_scoped_session()`).

### Enable / disable

| Variable | Effect |
|----------|--------|
| `ENV=development` | Audit **on** unless overridden below |
| `CARTFLOW_DB_REQUEST_AUDIT=1` | Force **on** (e.g. staging) |
| `CARTFLOW_DB_REQUEST_AUDIT=0` | Force **off** |
| `CARTFLOW_DB_SLOW_REQUEST_MS` | Slow threshold (default **750** ms) |

### Log lines (search in your log sink)

- `[DB REQUEST START]` — endpoint string (method + path + short query)
- `[DB REQUEST END]` — duration + best-effort pool line (`checked_out`, `size`, `overflow` when available)
- `[DB QUERY COUNT]` — **executed SQL statements** in the request (cursor executes) + heuristic **`store_sql_hits`** ( statements touching `stores`)
- `[DB SLOW REQUEST]` — same as END but when duration ≥ threshold
- `[DB SESSION LEAK SUSPECTED]` — **heuristic only**:
  - GET/HEAD/OPTIONS with ORM `new`/`dirty` before `remove_scoped_session()`
  - nested audit context (middleware re-entry / bug)

**Important:** Query count uses `before_cursor_execute` on the bound `Engine`. Background work (e.g. widget config refresh thread) runs **without** a request bucket — those statements are **not** attributed to an HTTP endpoint here.

**SQLite / NullPool:** Pool metrics may show `metrics=n/a`; query counts still apply.

## 2. How to produce “worst endpoints” from logs

1. Enable audit in a non-prod environment mirroring load (or production with `CARTFLOW_DB_REQUEST_AUDIT=1` briefly).
2. Use the dashboard and storefront as a real user would (include auto-refresh / tabs).
3. Correlate:
   - **`[DB QUERY COUNT]`** `queries=` — primary pressure signal
   - **`[DB SLOW REQUEST]`** — latency outliers
   - **`store_sql_hits`** — how Store-centric the request is
4. Group by the `endpoint=` prefix (path only if you strip query in analysis).

The **static** section below lists where you should expect spikes **before** measuring.

## 3. Static hotspots (code inspection)

### 3.1 Widespread `db.create_all()` in request paths

**`main.py` alone** contains **many** `db.create_all()` calls inside handlers and helpers. Each call can force metadata sync work and extra connection use on **every** hit. Any route that chains multiple helpers may pay this cost **several times per request**.

Likely heavy when combined with:

- Full dashboard render
- Multiple API calls on first paint
- Demo / store pages that touch recovery helpers

**Recommendation (later):** move `create_all` + schema guards to startup or a migrations pipeline; gate with idempotent cheap checks once per process.

### 3.2 Main dashboard GET `/dashboard`

Implementation loads **many** aggregates in sequence, including (non-exhaustive):

- `_dashboard_recovery_store_row()` (Store) — reused but other helpers still query
- `_merchant_kpi_today_projection`, `_merchant_month_window_projection`
- `_merchant_reason_counts_store_window` (7d **and** 30d separately)
- `_normal_recovery_merchant_lightweight_alert_list` (+ Python loop over rows for buckets)
- `_vip_priority_cart_alert_list` iterated multiple times for projections
- `_normal_carts_dashboard_stats()`, `merchant_followup_actions_for_dashboard`
- `_merchant_recovery_message_history_rows`, `merchant_widget_panel_bundle`

**Risk pattern:** Many **round-trips**, possible **duplicate Store / policy reads**, repeated `ensure_store_widget_schema`-style paths in deeper helpers.

**Recommendation (later):** one orchestration layer that batches counts, caches Store row per request (`request.state`), and avoids N× `create_all`.

### 3.3 Dashboard analytics HTML routes

Routes such as:

- `GET /dashboard/analytics`
- `GET /api/dashboard/recovery-trend`

use **multiple** `db.session` aggregations and often call `db.create_all()` / `_ensure_store_widget_schema()` in financial context builders.

**Recommendation (later):** materialized aggregates or incremental counters for trend charts.

### 3.4 `GET /api/recovery-settings` (large JSON payloads)

Loads the latest **`Store`** and merges **many** field bundles (templates, triggers, VIP, catalogs, guided defaults). Suitable for caching or splitting “read subsets” used by specific UI tabs.

### 3.5 `POST /api/dashboard/merchant-widget-settings`

Writes Store + **`update_widget_config_cache_from_dashboard`** (intentionally decouples widget hot path). Still expect write + large read backs for panel.

### 3.6 CartFlow analytics API

`routes/cartflow.py` — `compute_recovery_analytics` / `/api/cartflow/analytics/{slug}` performs **counts** on `cart_recovery_logs` and **iterates steps**. Fine for admins; spikes if polled frequently.

### 3.7 `resolve_store_row_for_cartflow_slug` helpers

Still call `db.create_all()` in **`services/vip_abandoned_cart_phone.py`** for scoped-session paths — any frequent caller inherits that cost unless refactored.

### 3.8 ORM listeners (extra CPU per row, not pooled connections themselves)

**`services/widget_config_cache.install_cart_recovery_ready_signals_once`**

- `CartRecoveryLog` `after_insert` / `after_update` → maintains in-memory `after_step1` keys.

Cost is **application-side**; does not add SQL by itself but runs on every qualifying ORM flush.

### 3.9 Background refresh (off request path)

**`services/widget_config_cache.maybe_schedule_background_refresh`** — bounded thread pool + throttled refresh; opens its **own** session via `sessionmaker(bind=...)`. Won’t appear in `[DB QUERY COUNT]` for HTTP logs.

Watch total DB concurrency if **many distinct** `store_slug` values churn.

### 3.10 Suspected frontend polling

Not enumerated in backend static files here. Common clients:

- Recovery settings editors refetching `GET /api/recovery-settings`
- Dashboard SPA patterns hitting `/api/dashboard/*`

Use browser devtools Network + new logs’ `endpoint=` to confirm.

## 4. Interpretation cheatsheet

| Signal | Meaning |
|--------|--------|
| High `queries` + low `duration_ms` | Many small SELECTs → N+1 or repeated helpers (`create_all`, per-row lazy loads) |
| High `duration_ms` + moderate `queries` | Large scans, Python post-processing, or lock wait |
| High `store_sql_hits` | Store-centric; consider per-request memoization of `Store` |
| `[DB SESSION LEAK SUSPECTED]` on GET | Investigate missing `rollback`, implicit writes in read handlers, or false positive from legitimate identity map state |

## 5. Recommended next steps (no implementation in this task)

1. **Measure** with audit enabled under realistic navigation; rank endpoints by `queries` then by `duration_ms`.
2. **Eliminate per-request `db.create_all()`** from hot paths (largest bang-for-buck).
3. **Request-scoped memo** for `_dashboard_recovery_store_row()` and shared template/Store reads on dashboard.
4. **Split** `GET /api/recovery-settings` if the UI only needs subsets per tab.
5. **Review** any client polling interval against `/api/recovery-settings` and heavy dashboard APIs.

## 6. Change log

- **2026-05-13:** Added `services/db_request_audit.py` + middleware hooks; this report (static phase).
