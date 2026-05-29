# Dashboard hot-path: next bottleneck (post queued-followup optimization)

**Date:** 2026-05-29  
**Run:** `GET /dev/cartflow-simulation-report?stores=100&dry_run=true&expanded=true`  
**Prior fix:** `perf: remove queued followup n+1 from dashboard hot path`  
**JSON field:** `deep_profile_report.next_bottleneck_report`

---

## Executive summary

**Queued-followup N+1 is resolved.** Per-group `_has_recent_queued_followup` DB probes are **0**; replaced by one bulk prefetch (`sql:batch_queued_followup_logs_bulk`).

**Next bottleneck: phone resolution loop** — `loop:batch_resolve_customer_phone_per_abandoned` → `_merchant_normal_batch_resolve_customer_phone_raw` (once per abandoned candidate row, up to ~row_cap). This was the #2 item in the pre-optimization audit and remains the top structural N+1 in code.

---

## 100-store simulation metrics

| Metric | Value |
|--------|------:|
| `total_dashboard_queries` (avg/check) | **46.95** |
| `dashboard_check_ms` (avg/check) | **117.38 ms** |
| Dashboard calls profiled | 500 |
| Queued-followup per-group DB queries | **0.0** |
| Queued-followup bulk prefetch queries | **~0.02** (~1/check) |
| Prior baseline total queries | 658 |
| Prior baseline queued-followup queries | 48 |

### Queued-followup optimization confirmed

```json
{
  "n_plus_one_removed": true,
  "after_avg_per_dashboard_check": {
    "queued_followup_per_group_db_queries": 0.0,
    "queued_followup_bulk_prefetch_queries": 0.02
  }
}
```

---

## Top 5 slowest functions (wall time)

| Rank | Function | Avg wall ms | Total queries |
|------|----------|------------:|--------------:|
| 1 | `_normal_recovery_merchant_lightweight_alert_list_for_api` | 109.02 | 22,568 |
| 2 | `purchase:lifecycle_closure` | 90.55 | 0 |
| 3 | `purchase_dashboard:_normal_recovery_merchant_lightweight_alert_list_for_api` | 87.04 | 4,100 |
| 4 | `purchase:record_truth` | 51.92 | 0 |
| 5 | `purchase:reconcile` | 34.41 | 0 |

Dashboard list root dominates wall time (~93% of dashboard-profiled ms).

---

## Top repeated queries (schema noise filtered)

Under 100-store load, many dashboard checks hit the **4.5s cooperative wall budget** before `batch_reads` completes. SQL fingerprint samples are dominated by partial/early returns:

| Count (avg/check) | Query |
|------------------:|-------|
| 7 | `abandoned_carts` candidate page SELECT |
| 1 | `cart_recovery_logs` bulk |
| 1 | `cart_recovery_reasons` bulk |
| 1 | `recovery_schedules` bulk |

`PRAGMA table_info` noise is excluded from this table (SQLite schema introspection during startup/warmup).

---

## N+1 patterns (SQL audit)

**None captured above threshold** in the 100-store averaged sample — most checks time out at `candidates_loaded` or `before_batch_reads` and never reach per-row phone resolution.

On **completed** batch-read paths (1-store avg ~121 queries/check), profiler child spans show:

| Span | Queries (avg) | Calls |
|------|--------------:|------:|
| `sql:batch_cart_recovery_reason_by_session` | 2 | 1 |
| `sql:batch_queued_followup_logs_bulk` | 1 | 1 |
| `sql:batch_cart_recovery_logs_bulk` | 1 | 1 |
| `sql:batch_abandoned_cart_peers_for_scope` | 1 | 1 |
| `sql:batch_message_logs_whatsapp_by_abandoned` | 1 | 1 |
| `sql:batch_recovery_schedules_bulk` | 1 | 1 |
| `loop:batch_resolve_customer_phone_per_abandoned` | 0* | 1 |

\*Sim data often resolves phones from batch maps without extra SQL; production carts with sparse batch coverage still hit per-row lookups.

---

## Duplicate lookups

| Kind | Detail |
|------|--------|
| `same_sql_in_multiple_spans` | `abandoned_carts` candidate query attributed to both root function and `sql:abandoned_cart_candidates_page_query` (profiler nesting — not a true duplicate round-trip) |
| **Still open (from pre-audit)** | Dual `cart_recovery_reason` queries (store-scoped + any-store) on same session key set |

---

## Next bottleneck verdict

| Question | Answer |
|----------|--------|
| Queued-followup N+1 removed? | **Yes** — 0 per-group DB queries |
| Phone resolution loop next? | **Yes** — structural N+1 in `_merchant_normal_dashboard_batch_reads` |
| Recommended next optimization (not implemented) | Bulk-complete phone map in batch_reads; eliminate per-row `_merchant_normal_batch_resolve_customer_phone_raw` fallbacks |

**Rationale:** With queued-followup bulk prefetch in place, the highest remaining **per-row** DB loop in the hot path is phone resolution over `full_rows` (~220–500 candidates). Dual reason queries (~2/check) are the top **fixed-count** SQL cost on completed reads.

---

## How to re-run

```http
GET /dev/cartflow-simulation-report?stores=100&dry_run=true&expanded=true
```

Inspect: `deep_profile_report.next_bottleneck_report`
