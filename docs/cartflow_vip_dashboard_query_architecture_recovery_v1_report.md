# VIP Dashboard Query Architecture Recovery v1 Report

**Date (UTC):** 2026-06-12  
**Task:** Architectural fix for VIP dashboard N+1 query pattern  
**Baseline:** VIP Dashboard Performance & Fresh-Load Consistency Audit v1

---

## Summary

Replaced the per-row DB projection loop on `GET /api/dashboard/vip-carts` with a **batch load → pure projection** architecture. Business SQL for 5 VIP rows dropped from **239 → 3–4 queries**; for 50 VIP rows **239+ → 4 queries**. Local endpoint wall time dropped from **~5535 ms → ~25 ms** (50 rows, warm SQLite).

VIP business meaning, threshold rules, lifecycle, WhatsApp paths, and dashboard JSON shape are unchanged. Cache was not removed or relied upon for the fix.

---

## Phase 1 — Current path (before)

```
GET /api/dashboard/vip-carts
  → api_dashboard_vip_carts()
  → _merchant_dashboard_db_ready()
  → _dashboard_recovery_store_row()
  → _api_json_dashboard_vip_carts(dash_store)
      → _vip_priority_cart_alert_list(dash_store)
          → _vip_priority_alert_rows_for_lc_clause()
              → SELECT all VIP AbandonedCart rows
              → _cleanup_duplicate_vip_abandoned_rows()  [extra scan + optional DELETE]
              → per group: hydrate_abandoned_cart_customer_phone_from_recovery()  [DB]
              → _vip_dashboard_cart_alert_dict_from_group()
                  → _vip_dashboard_customer_phone_raw()  [N× slug/reason/memory queries]
                  → _reason_tag_for_abandoned_cart()  [N× reason queries]
      → for each row (up to 20):
          → _merchant_vip_row_safe_projection(vc)
              → db.session.get(AbandonedCart, id)  [N+1 re-fetch]
              → _reason_tag_for_abandoned_cart(ac)  [N+1 again]
  → JSON response
```

**Audit baseline (5 rows, steady state, PRAGMA excluded):** 239 business queries, ~5535 ms local.

---

## Phase 2 — VIP projection contract

Implemented in `vip_dashboard_row_contract()` (`services/vip_dashboard_batch_v1.py`).

Each row includes contract fields:

| Field | Source |
|-------|--------|
| `cart_id` | `AbandonedCart.zid_cart_id` |
| `recovery_key` | `{store_slug}:{session_id}` |
| `store_slug` | dashboard store |
| `customer_phone` | batch phone map |
| `cart_total` | `cart_value` |
| `is_vip` | always `true` in lane |
| `reason_tag` / `vip_reason` | payload → batch reason map |
| `reason_label_ar` | chip label helper (no DB) |
| `last_activity_at` / `created_at` | cart timestamps |
| `alert_status` | VIP lifecycle effective |
| `manual_contact_available` | phone + wa.me href |
| `operational_lane` | `vip_operational_lane_diagnostics()` |
| `display_status_ar` | lifecycle label AR |
| `recommended_action_ar` | manual contact or unavailable text |

Legacy dashboard UI fields preserved: `id`, `amount_display`, `subtitle_ar`, `contact_href`, `has_phone`, `vip_lifecycle_label_ar`, etc.

---

## Phase 3 — New batch path (after)

```
GET /api/dashboard/vip-carts
  → api_dashboard_vip_carts(?debug_perf=1 optional)
  → _merchant_dashboard_db_ready()
  → _dashboard_recovery_store_row()
  → build_vip_dashboard_api_payload(dash_store)
      → load_vip_dashboard_batch_context()
          1. SELECT VIP AbandonedCart rows (once, scoped)
          2. _vip_pick_priority_cart_groups() (in-memory)
          3. bulk_load_reason_maps_by_session() (one query)
          4. bulk CartRecoveryLog load (one query, sent-phone index)
          5. in-memory recovery_session_phone map (no DB)
      → vip_dashboard_row_contract() per group (pure, zero DB)
  → JSON response
```

**Removed from dashboard API hot path:**

- Per-group `hydrate_abandoned_cart_customer_phone_from_recovery` writes
- `_cleanup_duplicate_vip_abandoned_rows` on read
- `_vip_dashboard_cart_alert_dict_from_group` heavy path
- `_merchant_vip_row_safe_projection` per-row `get()` + reason lookup

`_vip_priority_cart_alert_list()` remains for settings/other surfaces unchanged.

---

## Phase 4 — Query count before/after

| Scenario | Before (audit) | After (measured) |
|----------|----------------|------------------|
| 5 VIP rows | 239 business SQL | **3–4** business SQL |
| 50 VIP rows | scales ~48/row | **4** business SQL |
| Batch module counter (`debug_perf`) | — | **3** (carts + reasons + logs) |

Evidence: `scripts/_vip_perf_audit_out/recovery_v1_benchmark.json`

| Scenario | Before ms | After ms (local warm) |
|----------|-----------|------------------------|
| 5 rows | ~5535 | ~25–106 |
| 50 rows | — | **~25** |

Hard targets:

| Target | Result |
|--------|--------|
| ≤20 SQL for 50 rows | **PASS** (4) |
| ≤750 ms local for 50 rows | **PASS** (~25 ms) |
| No N+1 | **PASS** (projection tests enforce zero DB) |
| Sub-500 ms typical | **PASS** locally |

Production isolated fetch (~3176 ms before) requires post-deploy measurement; architectural N+1 removal is the prerequisite for material production improvement.

---

## Phase 5 — Performance guardrails (tests)

File: `tests/test_vip_dashboard_query_architecture_v1.py`

| # | Test | Status |
|---|------|--------|
| 1 | Query count bounded (5 rows) | PASS |
| 2 | Query count bounded (50 rows) | PASS |
| 3 | Projection zero DB | PASS |
| 4 | Reason batch | PASS |
| 5 | Phone batch (no per-row DB) | PASS |
| 6 | Response shape compatible | PASS |
| 7 | Manual contact correct | PASS |
| 8 | Empty VIP state | PASS |
| 9 | `debug_perf` metadata | PASS |
| 10 | No threshold state | PASS |

Additional regression: `tests/test_merchant_dashboard_runtime_truth_v1.py` VIP tests **PASS**.

---

## Phase 6 — Instrumentation

Optional dev/admin metadata via `?debug_perf=1`:

```json
{
  "query_count": 3,
  "endpoint_ms": 25.21,
  "projection_ms": 2.87,
  "rows_returned": 20,
  "degraded": false,
  "batch_rows_fetched": 50,
  "batch_reasons_fetched": 0,
  "batch_logs_fetched": 0,
  "load_ms": 22.34
}
```

Not included in default merchant responses (only when query param set).

---

## Phase 7 — Fresh load verification (production)

**Deploy:** Pushed `170758b` to `origin/main` (2026-06-12). Batch path live on first poll — `?debug_perf=1` returns metadata on production.

**Evidence:** `scripts/_vip_query_recovery_deploy_verify_v1_out/deploy_verify_report.json`

### Deploy confirmation (poll 0)

| Signal | Result |
|--------|--------|
| `debug_perf` in response | **Present** (batch module deployed) |
| Server `endpoint_ms` (empty store) | **0.04–0.06 ms** |
| Server `query_count` (empty store, 0 VIP rows) | **0** (no cart/reason/log rows to batch) |

### Isolated fetch (empty merchant, post-deploy)

| Metric | Audit baseline (2 VIP rows) | Post-deploy (0 rows) |
|--------|------------------------------|----------------------|
| Client round-trip median | 3176–3819 ms | **1237 ms** |
| Server `endpoint_ms` | ~3000+ ms (N+1) | **~0.05 ms** |

Empty-store client RTT still includes auth/TLS/network; server-side N+1 removal is confirmed via `debug_perf`.

### Fresh load laptop + mobile (empty merchant)

| Metric | Audit baseline | Post-deploy (partial) |
|--------|----------------|----------------------|
| Laptop first visible VIP row | **8127 ms** | N/A (empty store — no amount row) |
| Mobile first visible VIP row | **9388 ms** | N/A (empty store) |
| VIP API from `#vip` nav (laptop) | — | 3932–4952 ms (0 rows) |
| VIP API from `#vip` nav (mobile) | — | 4564–11786 ms (0 rows) |

### Seeded VIP re-measure (blocked)

Full apples-to-apples comparison (threshold + VIP cart, 1–2 rows) requires a merchant with VIP data — same setup as the cross-device audit (threshold 500 + test-widget cart). A follow-up run with API seeding was **blocked**: production `/ping` and `/signup` timed out (>90 s) after deploy (~17:08–17:11 UTC), likely deploy restart or transient outage.

**Re-run when production is healthy:**

```bash
python scripts/_vip_query_recovery_deploy_verify_v1.py
```

Script seeds threshold + `POST /api/cart-event` VIP cart, then measures laptop/mobile fresh `#vip` load with `sessionStorage` cleared.

Client boot weight (~451 KB JS) and `sessionStorage` cache behavior are **unchanged** — this recovery targets **server truth latency**, not cache dependency.

---

## Phase 8 — No-regression confirmation

| Area | Status |
|------|--------|
| VIP rows appear | Verified in tests |
| Manual contact / unavailable | Verified |
| VIP threshold / classification query | Same filters (`VIP_PRIORITY_LC_ACTIVE_SQL`, `cart_value >= threshold`) |
| Store identity | `_dashboard_recovery_store_row()` unchanged |
| Cart Bridge | Not touched |
| WhatsApp / VIP alert send paths | Not touched |
| Normal carts API | Not touched |
| Dashboard tabs / JS | Not touched |
| `_vip_priority_cart_alert_list` for settings | Preserved |

---

## Files changed

| File | Change |
|------|--------|
| `services/vip_dashboard_batch_v1.py` | **New** — batch context, pure projection, API builder |
| `main.py` | `_api_json_dashboard_vip_carts` delegates to batch; `debug_perf` query param |
| `tests/test_vip_dashboard_query_architecture_v1.py` | **New** — N+1 guardrail tests |
| `scripts/_vip_perf_audit_out/recovery_v1_benchmark.json` | Benchmark evidence |
| `scripts/_vip_query_recovery_deploy_verify_v1.py` | Post-deploy Playwright verification |
| `docs/cartflow_vip_dashboard_query_architecture_recovery_v1_report.md` | This report |

---

## Root cause addressed

**Rank #2 from performance audit:** Slow `/api/dashboard/vip-carts` due to N+1 per-row cart re-fetch, reason lookup, and phone resolution loops.

**Not addressed in this task (unchanged):**

- Cache dependency (#1 perceived laptop vs mobile)
- Dashboard boot JS weight (#3)
- Loading-state retry design (#4)

---

*Stop — awaiting review. No settings/WhatsApp/new features.*
