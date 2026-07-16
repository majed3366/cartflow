# Work Package Review — WP-5 Dashboard/Home Time Authority Migration

| Field | Value |
|-------|-------|
| Investigation | INV-001 |
| Work Package | WP-5 |
| Branch | `feature/inv001-wp5` |
| Date submitted (UTC) | 2026-07-16 |
| Decision | ☐ Approved — **awaiting Architecture Review (+ Gate A)** |

## 1. Summary

Dashboard KPI projections in `dashboard_kpi_time_v1` now consume Time Authority via the same `resolve_knowledge_windows` / `window_for(TODAY)` path as Knowledge. Rolling windows are half-open `[start, end)`. Home `generated_at` and counter/hot-slice default “now” use authority. Legacy WP-5A wall/open-ended ownership removed. Reality Replay Gate A automated pack **PASS**.

## 2. Commit hash

`0c6f6cba98089984be7e3c285d7352d725cfade0`

## 3. Branch

`feature/inv001-wp5`

## 4. Files created

| Path |
|------|
| `tests/time_authority/test_wp5_dashboard_knowledge_cross_surface.py` |
| `tests/time_authority/test_wp5_reality_replay_gate_a.py` |
| `docs/investigations/WP-05_BRIEF.md` |
| `docs/investigations/WP-05_REVIEW.md` |
| `docs/architecture/reality_replay_gate_a_wp5/GATE_A_REPORT.md` |
| `docs/architecture/reality_replay_gate_a_wp5/gate_a_evidence.json` |

## 5. Files modified

| Path |
|------|
| `services/dashboard_kpi_time_v1.py` |
| `services/merchant_home_composition_v1.py` |
| `services/dashboard_hot_slice_v1.py` |
| `services/dashboard_counter_totals_v1.py` |
| `tests/test_dashboard_kpi_time_wp5a.py` (retargeted to WP-5) |
| `docs/SYSTEM_SUMMARY.md` |
| `docs/investigations/INV-001.md` |
| `docs/investigations/INVESTIGATION_DASHBOARD.md` |

## 6. Files intentionally untouched

`main.py` (call sites unchanged); Daily Brief builder; Monthly; Attention; Timeline; Movement; Purchase Truth; Simulator; Knowledge collectors (already WP-4)

## 7. Dashboard paths migrated

| Path | Recipe |
|------|--------|
| Today KPI projection | `today` |
| Month / rolling KPI + reason windows | `last_n_days` (+ comparison via shared resolve) |
| Home `generated_at` | QTC / authority stamp |
| Hot-slice default now | `authority_now()` |
| Counter totals stamp / stale `now_utc` | `authority_now()` |

## 8. Legacy paths removed

- `legacy_today_utc_bounds`, `legacy_rolling_start`
- `LEGACY_KPI_TIME_*` markers
- Open-ended `>= start` only predicates on rolling KPI/reason queries
- Private wall `datetime.now` window math in `dashboard_kpi_time_v1`

## 9. Tests executed

```text
python -m pytest tests/time_authority/ tests/test_dashboard_kpi_time_wp5a.py -q
→ 142 passed
python -m pytest tests/test_knowledge_layer_v1.py tests/test_knowledge_layer_v1_completion_v1.py -q
```

## 10–11. Golden / cross-surface

Dashboard rolling windows **identical** to Knowledge for same `now`/context (parametrized days). Simulation/replay scopes preserve equality + identity. Gate A: July empty / May sim 27≡27.

## 12–13. Query-count / shape

Same query count class; added exclusive `< end` predicates on rolling filters (index-friendly, no new queries/joins). Window construction O(1), no I/O.

## 14–16. Latency / scheduler / pool

No scheduler or pool changes; no new I/O; request path structural only.

## 17. Architectural Debt Introduced

**None.**

## 18. Architectural Debt Removed

- Temporary WP-5A legacy KPI temporal ownership
- Parallel Dashboard vs Knowledge rolling-window interpretation (open-ended vs half-open / dual clocks)

## 19. Consumer Migration Status

| Consumer | Status |
|----------|--------|
| Knowledge | Migrated |
| Dashboard/Home | **Migrated** |
| Daily Brief … Simulator | Not Started |

## 20. Risks

| Risk | Level | Notes |
|------|-------|-------|
| Open-ended → half-open may drop future-dated rows | Low | Aligns with Knowledge; production wall≈event |
| Greeting / brief_date still local/wall chrome | Low | WP-6 / WP-11 |

## 21. Rollback

Revert WP-5 commits on `feature/inv001-wp5`; WP-5A extraction remains if needed.

## 22. main.py impact

**None** (call sites already thin from WP-5A).

## 23. Time Contract impact

Dashboard is second consumer of WP-3; cross-surface equality enforced.

## 24. Reality Contract impact

Gate A automated pack green — see `GATE_A_REPORT.md`. Full Lab = WP-13.

## 25. Recommendation regarding Reality Replay Gate A

Gate A **executed** (automated evidence PASS). **Recommend Architecture Review approve Gate A before authorizing WP-6.** Do not begin WP-6 until approved.

---

**STOP.** Do not begin WP-6.
