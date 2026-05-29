# Dashboard hot-path: next bottleneck (post reason-bulk merge)

**Date:** 2026-05-29  
**Run:** `GET /dev/cartflow-simulation-report?stores=100&dry_run=true&expanded=true`  
**Prior fixes:** queued-followup N+1; phone resolution N+1; reason bulk merge  
**JSON fields:** `deep_profile_report.reason_bulk_optimization`, `deep_profile_report.next_bottleneck_report`

---

## Executive summary

**Dual CartRecoveryReason bulk queries are resolved.** Store-scoped + any-store reason loads merged into **one** SQL round-trip with in-memory precedence (current store first, cross-store fallback only when store row missing).

**Next bottleneck:** `sql:abandoned_cart_candidates_page_query` — dominant repeated SQL on partial/timeout dashboard checks under 100-store load.

---

## 100-store simulation metrics (post reason merge)

| Metric | Post phone opt | Post reason merge |
|--------|---------------:|------------------:|
| `total_dashboard_queries` (avg/check) | 46.95 | **46.8** |
| `dashboard_check_ms` (avg/check) | 128.47 ms | **104.68 ms** |
| Reason bulk queries (avg/check) | ~2 (baseline) | **0.01** (most checks timeout before batch_reads) |
| `fallback_reason_rows_used` (avg/check) | — | **0.0** |
| `dual_query_eliminated` | — | **true** |

On **completed** batch-read paths, reason bulk drops from **2 → 1** query/check.

### Reason bulk optimization confirmed

```json
{
  "reason_bulk_queries_before": 2,
  "after_avg_per_dashboard_check": {
    "reason_bulk_queries": 0.01,
    "fallback_reason_rows_used": 0.0
  },
  "dual_query_eliminated": true
}
```

---

## Next bottleneck verdict

| Question | Answer |
|----------|--------|
| Queued-followup N+1 removed? | **Yes** |
| Phone resolution N+1 removed? | **Yes** |
| Reason dual bulk removed? | **Yes** — merged single query |
| Next bottleneck | **`sql:abandoned_cart_candidates_page_query`** |

---

## How to re-run

```http
GET /dev/cartflow-simulation-report?stores=100&dry_run=true&expanded=true
```

Inspect: `deep_profile_report.reason_bulk_optimization`, `deep_profile_report.next_bottleneck_report`
