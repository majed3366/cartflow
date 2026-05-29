# Dashboard hot-path: next bottleneck (post phone-resolution optimization)

**Date:** 2026-05-29  
**Run:** `GET /dev/cartflow-simulation-report?stores=100&dry_run=true&expanded=true`  
**Prior fixes:** queued-followup N+1 (`perf: remove queued followup n+1 from dashboard hot path`); phone resolution N+1 (`perf: remove phone resolution n+1 from dashboard hot path`)  
**JSON fields:** `deep_profile_report.phone_resolution_optimization`, `deep_profile_report.next_bottleneck_report`

---

## Executive summary

**Phone-resolution per-row DB loop is resolved.** `loop:batch_resolve_customer_phone_per_abandoned` replaced by `loop:batch_resolve_customer_phone_bulk` — one in-memory pass over prefetched batch maps; **0** phone-resolution DB queries and **0** fallbacks to the raw per-row resolver on the normal-carts dashboard path.

**Next bottleneck:** `sql:abandoned_cart_candidates_page_query` — dominant repeated SQL on partial/timeout dashboard checks under 100-store load (~7 avg/check in prior audit). On completed batch-read paths, dual `cart_recovery_reason` bulk queries (~2/check) remain the top fixed-count SQL cost.

---

## 100-store simulation metrics (post phone opt)

| Metric | Before phone opt | After phone opt |
|--------|----------------:|----------------:|
| `total_dashboard_queries` (avg/check) | **46.95** | **46.95** |
| `dashboard_check_ms` (avg/check) | **117.38 ms** | **128.47 ms** |
| Phone-resolution DB queries (avg/check) | ~150 (audit baseline) | **0.0** |
| `phone_resolution_fallback_count` (avg/check) | N/A | **0.0** |
| `phone_resolution_loop_count` (avg/check) | per-row (~220 calls) | **0.02** (most checks timeout before batch_reads) |
| Queued-followup per-group DB queries | **0.0** | **0.0** |

### Phone-resolution optimization confirmed

```json
{
  "phone_resolution_db_queries_before": 150,
  "after_avg_per_dashboard_check": {
    "phone_resolution_db_queries": 0.0,
    "phone_resolution_loop_count": 0.02,
    "phone_resolution_fallback_count": 0.0
  },
  "per_row_db_eliminated": true
}
```

---

## Next bottleneck verdict

| Question | Answer |
|----------|--------|
| Queued-followup N+1 removed? | **Yes** — 0 per-group DB queries |
| Phone resolution N+1 removed? | **Yes** — 0 phone DB queries, 0 fallbacks |
| Next bottleneck | **`sql:abandoned_cart_candidates_page_query`** (partial-check dominant); **`sql:batch_cart_recovery_reason_by_session`** dual-query (~2/check) on completed reads |
| Recommended next optimization (not implemented) | Merge dual cart_recovery_reason bulk queries; profile candidate page query under full batch_reads completion |

---

## How to re-run

```http
GET /dev/cartflow-simulation-report?stores=100&dry_run=true&expanded=true
```

Inspect: `deep_profile_report.phone_resolution_optimization`, `deep_profile_report.next_bottleneck_report`
