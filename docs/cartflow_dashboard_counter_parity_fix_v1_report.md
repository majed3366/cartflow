# Dashboard Counter Parity Fix + Governance V1

**Date:** 2026-07-02  
**Status:** Implemented

## Problem fixed

Counters previously reflected **page-window slices** (50 rows) or **divergent pipelines** (summary vs normal-carts). Merchants saw numbers whose meaning changed by source.

## Solution

**One Source Of Truth Per Question** — `build_merchant_cart_counter_totals()` in `services/dashboard_counter_totals_v1.py` produces store-level totals using the same row projection + lifecycle attach as the dashboard (higher scan caps, no page slice).

## Counter definitions

| Counter | Merchant meaning |
|---------|------------------|
| `active_total` | Non-VIP carts on active dashboard (not lifecycle archived/completed) |
| `waiting_total` | Active carts in waiting bucket (`active`, `waiting_first_send`) |
| `sent_total` | Active carts in sent lifecycle bucket |
| `engaged_total` | Active carts in attention bucket (reply / engaged / intervention) |
| `completed_total` | Same rule as «مكتملة» page (`is_completed_dashboard_row`) |
| `archived_total` | Carts in archived dashboard bucket |
| `no_phone_total` | Active carts without phone before first send; filter hidden when 0 |

## Source-of-truth map

See `services/dashboard_counter_governance_v1.py` (`COUNTER_SOURCE_OF_TRUTH_MAP`).

| UI surface | Canonical field |
|------------|-----------------|
| Filter «الكل» | `merchant_store_cart_counts.active_total` |
| Nav badge «بانتظار الإرسال» | `waiting_total` / `merchant_nav_badge_abandoned` |
| Filter «رسالة أُرسلت» | `sent_total` |
| Filter «يحتاج متابعة» | `engaged_total` |
| Filter «تم الاسترداد» | `completed_total` |
| Completed page | `completed_total` (same semantics) |
| Archived | `archived_total` |
| Page-only (audit) | `merchant_visible_page_counts` |

**Internal-only (different questions):** `messages_sent_count`, `normal_recovered_count`, KPI today/month SQL — not used for cart tab badges.

## API payload fields

```json
{
  "merchant_store_cart_counts": { "active_total": 120, "waiting_total": 40, ... },
  "merchant_cart_filter_counts": { "all": 120, "waiting": 40, ... },
  "merchant_visible_page_counts": { "all": 50, "waiting": 12, ... },
  "merchant_counter_health": {
    "counter_source": "canonical",
    "counter_generated_at": "...",
    "counter_snapshot_stale": false,
    "counter_query_scope": "store_total",
    "counter_parity_version": "v1"
  }
}
```

## Files changed

| File | Change |
|------|--------|
| `services/dashboard_counter_totals_v1.py` | **New** — canonical builder |
| `services/dashboard_completed_row_semantics_v1.py` | **New** — completed page rule |
| `services/dashboard_counter_governance_v1.py` | **New** — source map |
| `services/normal_carts_dashboard_batch_v1.py` | Wire canonical totals into API |
| `services/dashboard_snapshot_read_v1.py` | Snapshot counter health + audit |
| `services/dashboard_snapshot_normal_carts_slim_v1.py` | Persist counter fields in snapshots |
| `main.py` | `_normal_carts_dashboard_stats` + summary delegate to canonical (no new business logic) |
| `static/merchant_dashboard_lazy.js` | Store totals for display; page counts audit-only |
| `tests/test_dashboard_counter_totals_v1.py` | **New** |
| `tests/test_dashboard_completed_row_semantics_v1.py` | **New** |

## Unchanged (per scope)

Recovery execution, lifecycle transitions, purchase truth, scheduler, snapshot builder logic, WhatsApp, widget.

## Verification logs

Server:
```
[COUNTER TOTALS AUDIT] merchant=... source=canonical scope=store_total active_total=...
[COUNTER PAGE AUDIT] merchant=... visible_page_rows=50 page_waiting=...
```

Browser console: `[COUNTER TOTALS AUDIT]`, `[COUNTER PAGE AUDIT]`, `[ROW AUDIT]`

## Test results

```
tests/test_dashboard_counter_totals_v1.py — 6 passed
tests/test_dashboard_completed_row_semantics_v1.py — 6 passed
tests/test_dashboard_snapshot_normal_carts_slim_v1.py + stability suites — 33 passed
```

## Before / after

| Scenario | Before | After |
|----------|--------|-------|
| Store has 120 active, page shows 50 | Filter «الكل» = 50 | Filter «الكل» = 120 |
| Summary vs carts waiting badge | Different pipelines (250 vs 50 slice) | Same `build_merchant_cart_counter_totals` |
| Completed filter vs page | `recovered` bucket only vs broader page | Both use `completed_total` / `is_completed_dashboard_row` |
| Snapshot stale | Counts shown without health | `merchant_counter_health.counter_snapshot_stale` explicit |
| `nophone` chip | Always 0 | Hidden when `no_phone_total` = 0 |
