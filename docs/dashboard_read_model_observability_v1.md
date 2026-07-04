# Dashboard Read Model Observability V1

**Status:** Implemented
**Classification:** Constitution §4 Stage-4 (Implementation) of the Dashboard Read Model domain
**Scope:** Observability only — no read-model redesign, no builder redesign, no behavior/UI change, no migration
**Maturity move:** Dashboard Read Model **Level 2 (Governed) → Level 3 (Measured)**

---

## 1. Objective

Make the Dashboard Read Model **measurable in production** so operators can answer, from
real request data (not test-only counters):

- Which read path served this request? (snapshot / bounded-live / live-only)
- What are the real dashboard **p50 / p90 / p99** route latencies?
- How stale are snapshots, how far behind is the builder, how many stores are waiting?
- Is the hot slice degrading (query-budget hits / timeouts)?

This is the first execution phase approved by
`docs/dashboard_read_model_implementation_plan_v1.md` (recommended V1 scope = **I1 + I2 + I3 + I5**).
It directly closes audit risk **R2 (dead latency metrics)** and makes audit risk
**R1 (builder throughput ceiling)** *measurable*, which is the mandatory prerequisite for any
future R1 optimization under **Measure Before Optimize**.

Governance basis: `dashboard_read_model_governance_v1.md` §7 (Observability), §8 (Metrics),
contracts **DR-7** (latency metrics real in production), **DR-OV-1…3**, **DR-MT-1…3**, **DR-B5**
(builder must expose coverage and lag).

---

## 2. What was implemented

### I1 — Real production latency
`route_ms`, `snapshot_read_ms`, `hot_slice_ms` are now recorded from the **real serving path**
(not synthetic, not test-only). Exposed as `p50_ms / p90_ms / p99_ms / last_ms / sample_count`,
overall **and per endpoint** (`summary`, `normal-carts`, `widget-panel`, `refresh-state`,
`store-connection`). `source` flips from `log_only`/`in_process_buffer` to
`production_read_path` once real samples exist.

### I2 — Read path distribution
Every enforced request is bucketed by:
- **read path** — `snapshot` (single indexed read) vs `bounded_live` (snapshot + hot-slice merge,
  = `normal-carts`) vs `live_only` (reserved; 0 today).
- **branch** — `hit` / `stale` / `no_snapshot` / `missing_store_slug` / `degraded` /
  `route_budget_exceeded` / `snapshot_read_error`, both overall and per endpoint (with hit/stale/
  degraded rates).

### I3 — Builder coverage / lag (visibility only, no builder change)
`assess_builder_coverage()` exposes, via **bounded DB-side aggregate queries** (no O(stores)
app-side work):
- `eligible_store_count`, `built_store_count`, `stores_never_built`
- `stores_waiting_for_refresh` (stale-built + never-built)
- `builder_cycle_seconds` = ⌈eligible / stores_per_tick⌉ × loop interval
- `builder_lag_seconds` = age of the *oldest* store's freshest `normal_carts` snapshot
- `stores_built_per_tick` (from the last successful builder tick), `stores_per_tick_limit`,
  `builder_loop_interval_seconds`, `oldest_built_snapshot_at`

### I5 — Hot slice degrade metrics
From the hot-slice meta the merge already computes:
`reads`, `hot_merged` / `snapshot_only`, `hot_merge_rate_pct`, `degraded_rate_pct`,
`timeout_rate_pct` (reason `slow_*`), `limit_hit_rate_pct` (reason `query_budget_exceeded_*`),
and hot-slice query volume `queries_p50 / queries_p90 / queries_max` vs `queries_cap` (15) / `rows_cap` (25).

---

## 3. Architecture — one production hook, defensive by construction

```
build_*_from_snapshot()  (5 read wrappers)
        │  (snapshot read → client guards → [hot slice] → enrich → counters)
        ▼
enforce_route_budget(payload, wall0, endpoint)      # single serving choke point
        │  computes route_ms (pre-existing) ...
        └── _record_read_observability(...)          # NEW, wrapped in try/except
                    ▼
        dashboard_read_observability_v1.record_dashboard_read_sample(...)
                    ├── bounded in-memory deques + counters  (I1/I2/I5)
                    └── operational_metrics_v1.record_dashboard_timing_sample(...)  # feeds legacy pipe
                                                                                    # → classify_dashboard_status
```

**Behavior neutrality guarantees**
- The observability call lives **only inside `enforce_route_budget`** (the single choke point all
  five wrappers already call) and in the enforcement guard's error branch. Both call sites wrap the
  recording in `try/except` so observability can **never** raise into a dashboard response.
- Recording is **side-effect-only into module-local state**. It adds **no keys** to any response
  payload. The only payload mutation `enforce_route_budget` performs (`_snapshot.route_ms`,
  and `budget_exceeded` on overrun) predates this work and is unchanged.
- Buffers are bounded (`deque(maxlen=256)`), so memory is constant regardless of traffic.
- No PII: only endpoint name, read-path class, branch class, and timings/counts are stored.
- Feeding the legacy `record_dashboard_timing_sample` pipe means `classify_dashboard_status` now
  reacts to **real** production latency (route p90 ≥ 200ms → warning, ≥ 500ms → critical) — the
  concrete fix for R2 "dead latency metrics".

---

## 4. Files changed

| File | Change |
|------|--------|
| `services/dashboard_read_observability_v1.py` | **New.** Read-path observability read model: per-endpoint latency (p50/p90/p99), read-path + branch distribution, hot-slice degrade metrics. Single hook `record_dashboard_read_sample`; report `build_dashboard_read_observability_report`; `reset_*_for_tests`; classifiers `classify_read_path` / `classify_read_branch`. |
| `services/dashboard_snapshot_read_v1.py` | `enforce_route_budget` gains `endpoint=` and calls new defensive `_record_read_observability(...)`; 5 wrappers pass their endpoint. No serving logic change. |
| `services/dashboard_snapshot_enforcement_guard_v1.py` | Error path records the `snapshot_read_error` branch (defensive); degraded response unchanged. |
| `services/scheduler_snapshot_loop_health_v1.py` | Loop health additively records last-tick `stores_built` / `stores_seen` / `last_tick_at` (feeds `stores_built_per_tick`). |
| `services/operational_metrics_v1.py` | `p99_ms` added to timing summary; `collect_dashboard_read_observability_metrics()`; `assess_builder_coverage()` (bounded aggregates); report `metrics.dashboard` now carries `read_observability` + `builder_coverage`; timing `route_ms/snapshot_read_ms/hot_slice_ms` prefer real production data; 11 new metric contracts registered. |
| `tests/test_dashboard_read_observability_v1.py` | **New.** 13 tests (classification, percentiles, distribution, hot-slice degrade, production wiring via `enforce_route_budget`, read parity/behavior neutrality, error branch, builder coverage, real-latency status). |

All new metrics surface on the existing read-only endpoint `GET /dev/operational-metrics`
under `metrics.dashboard.read_observability` and `metrics.dashboard.builder_coverage`
(plus real per-request percentiles under `metrics.dashboard.route_ms/snapshot_read_ms/hot_slice_ms`).

---

## 5. Metrics added (contracts)

`dashboard.read.route_p99_ms`, `dashboard.read.read_path_distribution`,
`dashboard.read.branch_hit_rate`, `dashboard.hot_slice.degraded_rate`,
`dashboard.hot_slice.timeout_rate`, `dashboard.hot_slice.limit_hit_rate`,
`dashboard.builder.cycle_seconds`, `dashboard.builder.lag_seconds`,
`dashboard.builder.stores_waiting_for_refresh`, `dashboard.builder.stores_built_per_tick`
(owner `dashboard_read_observability_v1` / `dashboard_snapshot_builder_v1`). All are
denominator-based rates or bounded gauges (DR-MT-2), sourced from `production_read_path` or a
`derived_bounded_query` (DR-MT-1: no test-only / log-only KPI).

---

## 6. Verification

| # | Requirement | Result |
|---|-------------|--------|
| 1 | Production metrics populate | ✅ End-to-end `build_operational_metrics_report` shows `route_ms.source=production_read_path` with real p50/p90/p99; `read_path_distribution` (snapshot 50% / bounded_live 50%); `builder_coverage` (eligible 2, built 1, never_built 1, waiting 1, cycle 45s, lag 0s). |
| 2 | No dashboard behavior change | ✅ Observability is side-effect-only; adds no payload keys; recording wrapped in `try/except`. Enforcement + hot-slice suites pass. |
| 3 | No merchant-visible change | ✅ Response bodies unchanged (`read_observability` never appears in a dashboard response — asserted in tests). |
| 4 | Read parity preserved | ✅ `build_summary_from_snapshot` returns identical payloads across repeated calls with observability enabled. |
| 5 | No measurable latency regression | ✅ Recording is O(1) into in-memory deques/counters under a single lock; report build stays inside the 5s metrics wall budget (`measurement_partial=False`, ~1s in verify). |
| 6 | Metrics survive production execution | ✅ Fed from the real serving choke point (`enforce_route_budget`) + builder loop; bounded buffers persist across requests within the process. |

**Tests:** `tests/test_dashboard_read_observability_v1.py` — **13 passed**.
Related suites re-run: `test_operational_metrics_v1`, `test_dashboard_snapshot_enforcement_v1`,
`test_dashboard_hot_slice_v1`, `test_scheduler_snapshot_loop_health_v1`,
`test_dashboard_snapshot_loop_continuous_v1`, `test_dashboard_snapshot_change_v1`,
`test_dashboard_builder_parity_v1` — all pass **except two pre-existing, unrelated failures**:
`test_allowlisted_in_production_dev_routes` and
`test_scheduler_snapshot_loop_health_v1::test_endpoint_returns_required_fields`. Both are
dev-route registration/allowlist issues in `main.py` (a 404 / a frozenset membership check);
`main.py` was not touched by this work and a dict-content change cannot turn a 200 route into 404.

---

## 7. Operator questions now answerable

| Question | Where |
|----------|-------|
| Which read path served requests? | `metrics.dashboard.read_observability.read_path_distribution.by_read_path` |
| Real p50/p90/p99 dashboard latency? | `metrics.dashboard.route_ms` (+ `route_ms_by_endpoint`) |
| How stale are snapshots? | `metrics.dashboard.data_freshness_seconds`, `snapshot.normal_carts_stale_pct`, `builder_coverage.builder_lag_seconds` |
| How far behind is the builder? | `builder_coverage.builder_lag_seconds`, `builder_cycle_seconds` |
| How many stores are waiting? | `builder_coverage.stores_waiting_for_refresh` (+ `stores_never_built`) |
| Is the hot slice degrading? | `read_observability.hot_slice.degraded_rate_pct / timeout_rate_pct / limit_hit_rate_pct` |

---

## 8. Remaining deferred work (unchanged by this phase)

Per the implementation plan, the following remain **explicitly deferred** and are NOT part of V1:

- **I12 / R1 builder selection scalability** — the *real* fix for the throughput ceiling. Now
  measurable via `builder_cycle_seconds` / `builder_lag_seconds` / `stores_waiting_for_refresh`;
  requires its own Audit→Governance→Implementation cycle and a fleet-scale validation env.
- **Duplication cleanup (D1 counts, D2 refresh token, D3 store_connection)** — behavior-sensitive;
  gated on I2 parity signals.
- **`dashboard_cards` deprecation/removal decision**, **dormant response-cache decision**,
  **normal-carts read-time recompute formalization**, **fleet-wide snapshot-age distribution** — hygiene / P2–P3.

### Known limitations
- `builder_lag_seconds` is computed over stores that have **at least one** `normal_carts` snapshot;
  stores never built are surfaced separately via `stores_never_built` (they have infinite lag by
  definition). `stores_waiting_for_refresh` sums both.
- `eligible_store_count` uses the builder's base predicate (`zid_store_id`+`merchant_user_id`+
  `is_active`) via a single bounded `COUNT`; it is a slight upper bound because the builder also
  excludes placeholder/test-prefix slugs in Python (negligible in production).
- In-process buffers are per worker; percentiles reflect the serving worker. Cross-worker
  aggregation is future work if/when needed.
