# Dashboard Counter Parity Audit V1 (Read-Only)

**Date:** 2026-07-02  
**Scope:** Merchant lazy dashboard (`merchant_app.html` + `merchant_dashboard_lazy.js`) — counters vs visible rows for Waiting, Active, Sent, Engaged, Completed, Archived.  
**Constraint:** Investigation only — no recovery/snapshot/lifecycle/row-builder/scheduler/cache behavior changes. Temporary `[COUNTER AUDIT]` / `[ROW AUDIT]` logs added for runtime comparison.

---

## Executive summary

Dashboard counters and visible rows **do not share a single global query**. Counters are computed **in-memory over the current API page slice** (`merchant_carts_page_rows`, default limit 50 active + 50 archived), while several UI surfaces read **different fields or pipelines**. The dominant parity risks are:

1. **Page-window counts, not store totals** — all filter-bar numbers are `len(active_rows)`-bounded, not full-store SQL counts.
2. **Summary vs normal-carts divergence** — home/summary badges use `_normal_carts_dashboard_stats()` (lightweight list, limit 250, separate DB aggregates).
3. **Completed tab ≠ recovered filter** — `#page-completed` uses broader `isCompletedDashboardRow()` / archived visuals; filter bar `recovered` uses lifecycle bucket only.
4. **Archived is a separate row list** — `merchant_archived_carts_page_rows` is not included in `merchant_cart_filter_counts` but merged into the completed tab.
5. **Client count reconciliation** — `effectiveFilterCounts()` may preserve prior counts, or derive from rows when incoming `all` is 0 or `< rows.length`.
6. **Snapshot mode** — counters are **frozen at snapshot write time**; rows served from `dashboard_snapshots` JSON (same fields, possibly stale).

---

## UI label → audit counter mapping

| Audit name | Merchant UI | DOM / field | API field |
|------------|-------------|-------------|-----------|
| **Waiting** | Sidebar «بانتظار الإرسال» badge | `#ma-nav-badge-abandoned` | `merchant_nav_badge_abandoned` |
| **Active** | Filter «الكل» | `#ma-filt-all` | `merchant_cart_filter_counts.all` |
| **Sent** | Filter «رسالة أُرسلت» | `#ma-filt-sent` | `merchant_cart_filter_counts.sent` |
| **Engaged** | Filter «يحتاج متابعة» | `#ma-filt-attention` | `merchant_cart_filter_counts.attention` |
| **Completed** | Sidebar «مكتملة» + filter «تم الاسترداد» | `#page-completed` tbody + `#ma-filt-recovered` | `recovered` count vs `completedCartsFromRows()` |
| **Archived** | Archived slice (no filter-bar chip) | archived rows in payload | `merchant_archived_cart_count` / `merchant_archived_carts_page_rows` |

There is **no filter-bar chip for Waiting**; waiting appears only on the nav badge.

---

## Step 1 — Counter source map

### Waiting

| Item | Detail |
|------|--------|
| **Function** | `lifecycle_nav_badge_waiting_count()` |
| **File** | `services/customer_lifecycle_states_v1.py` |
| **Called from** | `build_normal_carts_dashboard_api_payload()` → `merchant_nav_badge_abandoned` (`services/normal_carts_dashboard_batch_v1.py`) |
| **Data source** | In-memory `active_rows` (= `merchant_carts_page_rows`) |
| **Query** | None (post-build iteration) |
| **Filters** | `lifecycle_state_to_filter_bucket(state) == "waiting"` → states `active`, `waiting_first_send` |

**Alternate (summary only):** `_normal_carts_dashboard_stats()` → `lifecycle_authority_waiting_count()` over `_normal_recovery_merchant_lightweight_alert_list_for_api(250, lifecycle="active")` — **different row set** than normal-carts batch builder.

### Active

| Item | Detail |
|------|--------|
| **Function** | `lifecycle_filter_counts_from_rows()` → key `all` |
| **File** | `services/customer_lifecycle_states_v1.py` |
| **Called from** | `build_normal_carts_dashboard_api_payload()` → `merchant_cart_filter_counts.all` |
| **Data source** | `len(active_rows)` after unified build + pagination slice |
| **Query** | Underlying rows from `build_normal_carts_unified_rows()`: `AbandonedCart` candidates (`status in abandoned/recovered`), store scope, sub-VIP threshold, pick cap, lifecycle bucket filter |
| **Filters** | Counts every row in the **active page slice** (includes archived-lifecycle rows still on active list) |

**Alternate (summary KPI):** `lifecycle_authority_active_count()` — excludes `archived` and `completed` lifecycle states from lightweight list (250 cap).

### Sent

| Item | Detail |
|------|--------|
| **Function** | `lifecycle_filter_counts_from_rows()` → key `sent` |
| **File** | `services/customer_lifecycle_states_v1.py` |
| **Data source** | `active_rows` |
| **Filters** | `lifecycle_state_visible_tabs()` includes `sent` for: `waiting_customer_reply`, `waiting_next_scheduled`, `return_to_site`, `waiting_purchase_window`, `recovery_followup_complete` |

### Engaged

| Item | Detail |
|------|--------|
| **Function** | `lifecycle_filter_counts_from_rows()` → key `attention` |
| **File** | `services/customer_lifecycle_states_v1.py` |
| **Data source** | `active_rows` |
| **Filters** | States: `customer_reply`, `customer_engaged`, `needs_intervention` |

### Completed

| Item | Detail |
|------|--------|
| **Filter-bar function** | `lifecycle_filter_counts_from_rows()` → key `recovered` |
| **File** | `services/customer_lifecycle_states_v1.py` |
| **Data source** | `active_rows` |
| **Filters** | `customer_lifecycle_state == completed` → bucket `recovered` |

**Completed page (separate):** client `completedCartsFromRows()` — broader: purchased, `merchant_coarse_status==converted`, archived visual, terminal+label heuristics; merges **active + archived** page rows.

**Summary alternate:** `_normal_carts_dashboard_stats().normal_recovered_count` = SQL `COUNT(AbandonedCart WHERE status='recovered')` — store-wide, not page slice.

### Archived

| Item | Detail |
|------|--------|
| **Function** | `len(archived_rows)` → `merchant_archived_cart_count` |
| **File** | `services/normal_carts_dashboard_batch_v1.py` |
| **Data source** | `merchant_archived_carts_page_rows` (paginated slice, default 50) |
| **Query** | Same unified builder; `archived_ok` via `_normal_recovery_merchant_lifecycle_bucket_ok(lc_raw="archived", ...)` |
| **Filters** | Terminal archived groups, manual archive, purchased terminal, stale rules |

**Not in** `merchant_cart_filter_counts`. Archived lifecycle rows on the active list still increment `all` but only appear in `(all,)` visible tabs.

---

## Step 2 — Row source map

### Builder

| Item | Detail |
|------|--------|
| **Builder function** | `build_normal_carts_unified_rows()` → `build_normal_carts_dashboard_api_payload()` |
| **Canonical wrapper** | `build_canonical_normal_carts_payload()` (`services/dashboard_snapshot_normal_carts_parity_v1.py`) |
| **File** | `services/normal_carts_dashboard_batch_v1.py` |

### Data source (live)

1. SQL: `AbandonedCart` ordered by `last_seen_at DESC`, capped (`row_cap` 220–500).
2. Augment + VIP pick (`_vip_pick_priority_cart_groups`, max ~96–160 groups).
3. Batch reads (logs, phones, reasons, purchase truth, archives).
4. Per-group projection: `_merchant_normal_recovery_light_payload_merchant_batch()`.
5. Lifecycle attach: `attach_customer_lifecycle_state_to_row()` sets `customer_lifecycle_state`, `merchant_cart_bucket`, `merchant_cart_visible_tabs`.

### Snapshot source

| Mode | Path |
|------|------|
| **When** | `dashboard_snapshot_mode_enabled()` |
| **Read** | `build_normal_carts_from_snapshot()` → `dashboard_snapshots` type `normal_carts` |
| **File** | `services/dashboard_snapshot_read_v1.py` |
| **Rows** | Pre-serialized `merchant_carts_page_rows` + `merchant_archived_carts_page_rows` (slim allowlist) |
| **Counts** | Persisted `merchant_cart_filter_counts` from write-time live builder |

### Filtering rules (visible rows)

| Layer | Rule |
|-------|------|
| **Server inclusion** | VIP lane skip; lifecycle `active_ok` / `archived_ok`; sent-log fallback; pagination `page_limit`/`page_offset` (default 50+50) |
| **Client tab filter** | `applyCartFilterMode()` hides rows via `display:none` using `rowMatchesCartFilterMode()` on `data-ma-filter`, `data-ma-primary-bucket`, `data-ma-visible-tabs` |
| **Status rules** | Row attributes from lifecycle attach (`merchant_cart_bucket`, `merchant_cart_visible_tabs`); filter matching in `merchant_cart_row_matches_filter()` (`services/merchant_cart_row_classifier.py`) |

### Rendered tables

| Table | Rows shown |
|-------|------------|
| `#ma-tbody-all-carts` | All `merchant_carts_page_rows` (then client filter hides) |
| `#ma-tbody-completed` | `completedCartsFromRows(active, archived)` — not filter-bar driven |
| Home preview | `merchant_table_rows` (first 8) |

---

## Step 3 — Parity matrix

| Counter | Same source as rows? | Different filters? | Excludes archived rows? | Excludes stale rows? | Live DB vs snapshot? | Counts hidden rows? |
|---------|---------------------|--------------------|-------------------------|----------------------|----------------------|---------------------|
| **Waiting** | Same page slice | Badge uses lifecycle bucket; sidebar `?tab=waiting` filters on `visible_tabs` | Yes — archived lifecycle not in waiting bucket | Stale groups may be excluded at build | Snapshot: frozen counts | Yes — hidden rows still in badge count |
| **Active (all)** | Same page slice | Summary `normal_cart_count` uses **different** pipeline (250 lightweight) | Archived **page slice** separate; archived-on-active still in `all` | Stale may drop at build | Snapshot: frozen | Yes — `display:none` rows still counted |
| **Sent** | Same page slice | Lifecycle buckets vs classifier `merchant_cart_filter_counts_from_rows` should align if `visible_tabs` consistent | Archived lifecycle: only in `all` | Same as builder | Snapshot: frozen | Yes |
| **Engaged** | Same page slice | Same as sent | Same | Same | Snapshot: frozen | Yes |
| **Completed** | **Partial** | Filter `recovered` ⊂ completed page logic | Completed page merges archived slice | Same | Snapshot: frozen | Filter bar yes; completed page separate |
| **Archived** | Same archived slice | Not in filter-bar counts | N/A — separate list | Same | Snapshot: frozen | No filter bar; may appear on completed page |

### Additional mismatches

| Issue | Description |
|-------|-------------|
| **Page cap** | Counters reflect at most `page_limit` active rows (50 default), not total store carts. |
| **`nophone` counter** | `lifecycle_filter_counts` includes `nophone` key but lifecycle `lifecycle_state_visible_tabs()` **never** emits `nophone` — counter stays **0** while legacy classifier had `no_phone` bucket. |
| **Unused classifier counts** | `merchant_cart_filter_counts_from_rows()` exists but API uses `lifecycle_filter_counts_from_rows()` instead. |
| **Client reconciliation** | `effectiveFilterCounts()` can preserve stale counts or derive from rows when `incoming.all` is 0 or `< rows.length`. |
| **Summary sent total** | `messages_sent_count` / `merchant_dashboard_refresh_sent_total` = **all** `CartRecoveryLog` sent rows for store — not dashboard page slice. |

---

## Step 4 — Instrumentation added (temporary)

### Server

- `emit_counter_row_audit_logs()` in `services/normal_carts_dashboard_batch_v1.py`
- Called from:
  - `build_normal_carts_dashboard_api_payload()` → `source=live_builder`
  - `build_normal_carts_from_snapshot()` → `source=snapshot`

Example log lines:

```
[COUNTER AUDIT] counter=waiting count=12 source=live_builder filter=lifecycle_state_to_filter_bucket page_limit=50
[ROW AUDIT] active_rows=50 archived_rows=50 source=live_builder lifecycle_filter_counts={...} row_visible_tab_counts={...} row_match_counts={...}
```

`row_match_counts` recomputes per-tab row counts via `merchant_cart_rows_matching_filter()` for side-by-side comparison with lifecycle counts.

### Client

- `static/merchant_dashboard_lazy.js` — console `[COUNTER AUDIT]` / `[ROW AUDIT]` on each normal-carts render (includes `effective_fc`, `derived_fc`, `completed_rows`).

---

## Root cause candidates (ranked)

1. **Page-window semantics** — merchants interpret counters as store totals; system counts only the materialized 50+50 dashboard page.
2. **Summary vs normal-carts split** — `GET /api/dashboard/summary` waiting/active badges from `_normal_carts_dashboard_stats()` disagree with `GET /api/dashboard/normal-carts` after navigation refresh.
3. **Completed dual semantics** — `recovered` filter count ≠ `#page-completed` row list (`completedCartsFromRows` is broader and includes archived slice).
4. **Client count preservation** — thin/snapshot/partial payloads trigger `effectiveFilterCounts` preserve/derive paths → UI shows counts that do not match latest row payload.
5. **Snapshot staleness** — counters frozen at write time while `snapshot_stale=true`; rows present but counts may lag live builder.
6. **Hidden DOM rows** — filter tab hides rows with CSS but counters include all page rows.
7. **`nophone` always zero** — lifecycle SoT does not map any state to `nophone` tab; filter chip misleading if phone-blocked carts classify as `needs_intervention` / `waiting`.

---

## Files referenced

| File | Role |
|------|------|
| `services/customer_lifecycle_states_v1.py` | Counter functions, lifecycle→bucket/tabs |
| `services/normal_carts_dashboard_batch_v1.py` | Row builder + API payload + audit logs |
| `services/merchant_cart_row_classifier.py` | Row filter matching, unused tab-count helper |
| `services/dashboard_snapshot_read_v1.py` | Snapshot serve + audit logs |
| `services/lifecycle_authority_recovery_v1.py` | Summary active/waiting counts |
| `main.py` | API routes, `_normal_carts_dashboard_stats`, `[DASHBOARD COUNTS]` |
| `static/merchant_dashboard_lazy.js` | Render, `effectiveFilterCounts`, completed tab |
| `static/merchant_app.js` | `applyCartFilterMode`, row visibility |
| `templates/merchant_app.html` | Filter bar + nav structure |

---

## Verification checklist (ops)

1. Load merchant dashboard; open browser console — confirm `[COUNTER AUDIT]` / `[ROW AUDIT]`.
2. Tail server logs on `GET /api/dashboard/normal-carts` — compare `lifecycle_filter_counts` vs `row_match_counts` in `[ROW AUDIT]`.
3. Repeat with snapshot mode — `source=snapshot` lines should match persisted payload.
4. Compare summary badge (`merchant_nav_badge_abandoned` from summary) vs normal-carts badge after full load.
5. Open `#completed` — compare `completed_rows` in client `[ROW AUDIT]` vs `ma-filt-recovered`.

**No fixes applied in this audit.**
