# Work Package Review — WP-5A Controlled KPI Time Extraction

| Field | Value |
|-------|-------|
| Investigation | INV-001 |
| Work Package | WP-5A |
| Branch | `feature/inv001-wp5a` |
| Date submitted (UTC) | 2026-07-16 |
| Decision | ☐ Approved — **awaiting Architecture Review** |

## 1. Summary

Extracted legacy merchant KPI temporal projections from `main.py` into `services/dashboard_kpi_time_v1.py`. `main.py` retains thin call-site wiring only. Legacy calendar-today, open-ended rolling 7d/30d, and wall-clock acquisition preserved exactly. **No WP-3 Time Authority migration. WP-5 not started. Gate A not run.**

## 2. Commit hash

`cc649cb3b55b7d3839491e936f890fa0ddf16f4a`

## 3. Branch name

`feature/inv001-wp5a`

## 4. Files created

| Path |
|------|
| `services/dashboard_kpi_time_v1.py` |
| `tests/test_dashboard_kpi_time_wp5a.py` |
| `docs/investigations/WP-05A_BRIEF.md` |
| `docs/investigations/WP-05A_REVIEW.md` |

## 5. Files modified

| Path |
|------|
| `main.py` (remove extracted bodies; thin imports/calls) |
| `docs/SYSTEM_SUMMARY.md` |
| `docs/investigations/INV-001.md` |
| `docs/investigations/INVESTIGATION_DASHBOARD.md` |

## 6. Files intentionally untouched

Knowledge; Daily Brief; Monthly; Attention; Timeline; Movement; Purchase Truth; Simulator; merchant UI; Time Authority package; Dashboard counter/hot-slice (WP-5 scope).

## 7. Exact functions/helpers extracted

| Former `main.py` symbol | New owner |
|-------------------------|-----------|
| `_merchant_ref_today_utc_bounds` | `legacy_today_utc_bounds` |
| `_merchant_ref_non_vip_scoped_base_query` | `non_vip_scoped_base_query` |
| `_merchant_kpi_today_projection` | `merchant_kpi_today_projection` |
| `_merchant_month_window_projection` | `merchant_month_window_projection` |
| `_merchant_reason_counts_store_window` | `merchant_reason_counts_store_window` |
| (+ `legacy_rolling_start` pure helper for rolling starts) | |

## 8. main.py line/responsibility reduction

- Removed ~180 lines of KPI window math + projection queries from `main.py`.
- Call sites: `_api_json_dashboard_summary` and activation inspect path → service imports only.
- No temporal arithmetic / query construction remains for this scope in `main.py`.

## 9–10. Tests executed and results

```text
python -m pytest tests/test_dashboard_kpi_time_wp5a.py -q   → 17 passed
python -m pytest tests/time_authority/ -q                     → 119 passed
```

## 11. Golden behavior comparison

Frozen formulas in tests match service for today / rolling 7/30/N bounds; open-ended future row included; empty/store/boundary fixtures green. **PASS.**

## 12–13. Query-count / query-shape

Same filters and predicates as pre-extraction (`>= start` / `< end` for today; open-ended rolling). Instrumented today-projection query count stable after warm-up. No new joins/tables.

## 14–17. Ops / scheduler / pool / I/O

No scheduler; no pool change; no new I/O; no material latency path change (structural move only).

## 18. Architectural Debt Introduced

**None.**

## 19. Architectural Debt Removed

- KPI temporal/business ownership removed from `main.py`
- Functions listed in §7 deleted from `main.py`
- Composition-layer responsibility reduced for Dashboard KPI windows

## 20. Temporary Debt Retained

| Item | Owner | Removal |
|------|-------|---------|
| Legacy wall-clock + open-ended rolling KPI semantics in `dashboard_kpi_time_v1` | INV-001 **WP-5** | WP-5 migration + Golden Comparison |

## 21. Consumer Migration Status

| Consumer | Status |
|----------|--------|
| Knowledge | Migrated (WP-4) |
| Dashboard/Home Time Authority | **Not Started** |
| Dashboard/Home legacy KPI ownership | **Extracted from main.py** (WP-5A) |
| Daily Brief … Simulator binding | Not Started |

## 22. Risks

| Risk | Level | Notes |
|------|-------|-------|
| Lazy import of scope filter from `main` | Low | Same pattern as `dashboard_counter_totals_v1` |
| Optional `now=` test inject | Low | Production call sites omit it → wall clock |

## 23. Rollback

```text
git revert <wp5a-commit>
# or restore main.py functions and delete services/dashboard_kpi_time_v1.py
```

Preserves WP-1…WP-4; no Knowledge rollback.

## 24–25. Time / Reality Contract

Time: no contract change (legacy preserved). Reality: Gate A **not** run (deferred until WP-5).

## 26. main.py impact assessment

Controlled exception exercised: bodies removed; thin service calls only; no new logic.

## 27. Confirmation that WP-5 has not started

**Confirmed.** No Time Authority wiring in KPI paths.

## 28. Recommendation on whether original WP-5 may resume

**Yes, after Architecture Approval of WP-5A** — WP-5 can migrate `dashboard_kpi_time_v1` to WP-3 recipes without further ownership extraction from `main.py`.

---

**STOP.** Do not begin WP-5. Do not run Gate A. Do not begin WP-6.
