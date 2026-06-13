# Normal Carts Architecture Recovery v1 — Report

**Date (UTC):** 2026-06-13  
**Endpoint:** `GET /api/dashboard/normal-carts`  
**Verdict:** **PASS — architecture recovered locally; batch path matches VIP pattern**

---

## Problem (production evidence)

| Signal | Value |
|--------|--------|
| `partial` | `1` |
| `deadline_exceeded` | `1` |
| `timeout_stage` | `payload_row` |
| `candidate_rows` | 45 |
| `rows_built` | 6 |
| Request duration | ~14s |

Root cause: duplicate full-list builds (active + archived), per-row DB in projection (`group_is_terminal_archived`, legacy lifecycle truth, lifecycle classifier fallbacks), and lifecycle schedule/purchase/timeline lookups without batch prefetch.

---

## Target architecture

```
Batch Query → Batch Related Data → Pure Projection → JSON
```

Aligned with VIP dashboard recovery (`services/vip_dashboard_batch_v1.py`).

---

## Audit — N+1 sources removed

| Area | Before | After |
|------|--------|-------|
| API handler | Two `_normal_recovery_merchant_lightweight_alert_list_for_api` passes | Single `build_normal_carts_unified_rows()` |
| Archive check in loop | `_normal_recovery_group_is_terminal_archived` → per-row `sent_count` / `Store` queries | `_normal_recovery_group_is_archived_merchant_batch` uses `batch.sent_real_count`, `configured_cap_by_ac` |
| Legacy lifecycle truth | `attach_merchant_recovery_lifecycle_truth` per row (timeline/purchase DB) | Skipped on batch path (`skip_legacy_lifecycle_truth=True`); `customer_lifecycle_state` is SoT |
| Lifecycle classifier | `_next_schedule_due_at`, `_scheduled_effective_delay_seconds`, `_last_provider_sent_at` DB fallbacks | `schedule_prefetched=True`, batch `next_due_by_ac` / `effective_delay_seconds_by_ac`, `matched_logs` prefetch |
| Merchant lifecycle pack | `lifecycle_replied_evidence` / `lifecycle_purchased_evidence` re-hit DB | `timeline_statuses` + `purchase_truth_prefetched` through `build_normal_recovery_merchant_lifecycle` |
| Batch reads | Partial prefetch | Full maps: reasons, phones, schedules, timeline, purchase, archive, alias keys, queued followup index |

---

## New / changed code

| File | Role |
|------|------|
| `services/normal_carts_dashboard_batch_v1.py` | Unified build + `build_normal_carts_dashboard_api_payload()` + `_perf` |
| `main.py` | Batch archive projection; `skip_legacy_lifecycle_truth`; API `db_ready` once |
| `services/cartflow_merchant_lifecycle_precedence.py` | Prefetch-aware purchase/reply evidence |
| `services/cartflow_merchant_lifecycle.py` | Pass `timeline_statuses` into provider/reply branches |
| `services/merchant_recovery_lifecycle_truth.py` | `purchase_truth_prefetched`; timeline on reply evidence |
| `services/customer_lifecycle_states_v1.py` | Skip DB when `matched_logs` prefetched |
| `tests/test_normal_carts_dashboard_batch_v1.py` | Query budget + `_perf` + scale tests |
| `scripts/normal_carts_batch_verify_v1.py` | Local verification runner |

---

## Measurable `_perf` block

```json
{
  "query_count": 1,
  "duration_ms": 355.23,
  "candidate_rows": 46,
  "visible_rows": 45,
  "rows_built": 46,
  "rows_returned": 45,
  "partial": false,
  "degraded": false,
  "timeout_stage": null,
  "projection_ms": 30.88,
  "load_ms": 152.63
}
```

(Source: local verify with 45 seeded rows, post-warm.)

---

## Local verification

| Check | Target | Result |
|-------|--------|--------|
| `pytest tests/test_normal_carts_dashboard_batch_v1.py` | 3 passed | **PASS** |
| Business queries (10 rows, warmed) | ≤ 40 | **PASS** |
| Business queries (50 rows, warmed) | ≤ 55 | **PASS** |
| `partial` / `degraded` | false | **PASS** |
| `scripts/normal_carts_batch_verify_v1.py --rows 45` | `pass: true`, queries ≤ 55 | **PASS** (37 queries, 355ms) |

---

## Production follow-up

Deploy this commit set, then run production verification (`docs/cartflow_normal_carts_architecture_recovery_v1_production_verification.md`).

---

**STOP — architecture recovery complete pending production deploy.**
