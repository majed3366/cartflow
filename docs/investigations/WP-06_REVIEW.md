# Work Package Review — WP-6 Daily Brief Time Authority Migration

| Field | Value |
|-------|-------|
| Investigation | INV-001 |
| Work Package | WP-6 |
| Branch | `feature/inv001-wp6` |
| Date submitted (UTC) | 2026-07-16 |
| Decision | ☐ Approved — **awaiting Architecture Review** |

## 1. Summary

Daily Brief is now a Time Authority consumer. Rolling windows and comparison periods come from the same `resolve_knowledge_windows` path as Knowledge and Dashboard. `brief_date` and `generated_at` use QTC authoritative now. Knowledge Routing composition-root `routed_at` uses `knowledge_stamp_now` (no wall clock). Private Brief `date.today` / `datetime.now` ownership removed. **WP-7 not started.**

## 2. Commit hash

`d12602c3a412c841a148ee39e325bcbc7f54fc1e`

## 3. Branch

`feature/inv001-wp6`

## 4. Files created

| Path |
|------|
| `services/merchant_daily_brief_time_v1.py` |
| `tests/time_authority/test_wp6_daily_brief_cross_surface.py` |
| `docs/investigations/WP-06_BRIEF.md` |
| `docs/investigations/WP-06_REVIEW.md` |

## 5. Files modified

| Path |
|------|
| `services/merchant_daily_brief_v1.py` |
| `services/merchant_daily_brief_composer_v2.py` |
| `services/merchant_home_composition_v1.py` |
| `services/knowledge_routing_v1.py` |
| `docs/SYSTEM_SUMMARY.md` |
| `docs/investigations/INV-001.md` |
| `docs/investigations/INVESTIGATION_DASHBOARD.md` |
| `INVESTIGATION_DASHBOARD.md` (root stub, if present) |

## 6. Files intentionally untouched

`main.py`; Monthly Summary; Attention product semantics; Timeline; Movement; Purchase Truth; Simulator; Knowledge collectors (WP-4); Dashboard KPI math (WP-5)

## 7. Daily Brief paths migrated

| Path | Authority |
|------|-----------|
| Rolling / comparison windows | `resolve_brief_windows` → `resolve_knowledge_windows` |
| `brief_date` (v1, composer v2, Home fallback) | `brief_date_iso` → QTC stamp date |
| API `generated_at` | `brief_stamp_now` |
| Observability `time_window` | `brief_time_observability` |
| Routing `routed_at` | `knowledge_stamp_now` |
| Home greeting hour (same stamp family) | `knowledge_stamp_now` |

## 8. Legacy paths removed

- `merchant_daily_brief_v1` wall `datetime.now` for `generated_at`
- `_brief_date_iso` → `date.today()` in Brief v1 / composer v2 / Home
- `knowledge_routing_v1._utc_now_iso` → `datetime.now(timezone.utc)`
- Private Brief ownership of today / last-N / comparison / reporting timestamps

## 9. Tests executed

```text
python -m pytest tests/time_authority/test_wp6_daily_brief_cross_surface.py -q
→ 20 passed

python -m pytest tests/test_merchant_daily_brief_v1.py tests/test_merchant_daily_brief_composer_v2.py tests/test_knowledge_routing_v1.py -q
→ 31 passed

python -m pytest tests/time_authority/ --ignore=tests/time_authority/test_wp5_dashboard_knowledge_cross_surface.py -q
→ 140 passed (includes WP-6 + Gate A + foundation)

python -m pytest tests/test_knowledge_layer_v1.py tests/test_dashboard_kpi_time_wp5a.py -q
→ 17 passed
```

Note: `test_wp5_dashboard_knowledge_cross_surface.py` DB integration cases (`half_open_boundary_rolling`, `sim_sees_may_production_july_zero`) fail in this local DB fixture environment **with or without WP-6 changes** (verified via stash bisect). Pure window-equality tests in that file pass. Not a WP-6 regression.

## 10. Cross-surface equality evidence

Production / simulation / replay: Brief windows **identical** to Knowledge and Dashboard for the same context (`assert_brief_dashboard_knowledge_windows_equal` + parametrized days).

## 11–12. Query-count / shape

No new SQL, joins, or scans. Brief time bridge is pure. Existing Brief/Knowledge/Dashboard query shapes unchanged (`timestamp >= start` and `timestamp < end` where already migrated).

## 13–15. Latency / scheduler / pool

No scheduler or pool changes; window generation O(1); no repeated temporal recomputation beyond existing resolve calls; no new I/O.

## 16. Architectural Debt Introduced

**None.**

## 17. Architectural Debt Removed

| Removed responsibility |
|------------------------|
| Brief private calendar “today” (`date.today`) |
| Brief private wall `generated_at` |
| Composer / Home private `_brief_date_iso` |
| Routing composition wall `routed_at` |
| Risk of Brief ≠ Knowledge ≠ Dashboard window interpretation |

## 18. Consumer Migration Status

| Consumer | Status |
|----------|--------|
| Knowledge | Migrated |
| Dashboard/Home | Migrated |
| Daily Brief | **Migrated** |
| Monthly Summary | Not Started |
| Attention | Not Started |
| Timeline | Not Started |
| Movement | Not Started |
| Purchase Truth | Not Started |
| Simulator | Not Started |

## 19. Risks introduced

| Risk | Level | Notes |
|------|-------|-------|
| `brief_date` now UTC QTC date vs prior local `date.today` | Low | Aligns with Knowledge/Dashboard UTC contract |
| Routing stamp under Fixed/Sim changes `routed_at` | Low | Intended for sim/replay |

## 20. Rollback

Revert WP-6 commits on `feature/inv001-wp6` (Brief/routing/home + bridge + tests/docs only).

## 21. main.py impact

**None.**

## 22. Time Contract impact

Daily Brief + routing stamps bound to Query Time Context; three-surface temporal truth unified for rolling windows.

## 23. Reality Contract impact

None mandatory (Gate A already passed under WP-5). WP-6 does not alter Gate A evidence requirements.

## 24. Recommendation on WP-7

**Do not begin WP-7** until Architecture Review approves WP-6.
