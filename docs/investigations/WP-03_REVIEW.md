# Work Package Review — WP-3 Governed Time Filtering Contract

| Field | Value |
|-------|-------|
| Investigation | INV-001 |
| Work Package | WP-3 |
| Branch | `feature/inv001-wp3` |
| Date submitted (UTC) | 2026-07-16 |
| Decision | ☐ Approved — **awaiting Architecture Review** |

## 1. Summary

Implemented the governed Time Filtering Contract: pure O(1) window derivation from Query Time Context / Platform Time Authority, frozen half-open interval `[start_at, end_at)` UTC, required recipes, comparison-period symmetry, typed window/emptiness results, window provenance, UTC-only timezone policy with reserved store-local hook (rejected). **No consumer migration. `main.py` untouched.**

## 2. Commit hash

`d217d666589c09099a2f723b28fe8d8806ea738e`

## 3. Branch name

`feature/inv001-wp3`

## 4. Files created

| Path |
|------|
| `services/time_authority/filtering.py` |
| `services/time_authority/emptiness.py` |
| `tests/time_authority/test_wp3_filtering.py` |
| `docs/investigations/WP-03_BRIEF.md` |
| `docs/investigations/WP-03_REVIEW.md` |

## 5. Files modified

| Path |
|------|
| `services/time_authority/contracts.py` |
| `services/time_authority/exceptions.py` |
| `services/time_authority/__init__.py` |
| `services/time_authority/README.md` |
| `docs/SYSTEM_SUMMARY.md` |
| `docs/investigations/INV-001.md` |
| `docs/investigations/INVESTIGATION_DASHBOARD.md` |

## 6. Files intentionally untouched

`main.py`; Knowledge; Dashboard; Daily Brief; Monthly Summary; Attention; Timeline; Movement; Purchase Truth; Simulator engine bind; all merchant UI.

## 7. Tests executed

```text
python -m pytest tests/time_authority/ -q
```

## 8. Results

**77 passed** (WP-1 + WP-2 + WP-3)

## 9. Time Contract impact

| Item | Decision |
|------|----------|
| Interval shape | `[start_at, end_at)` frozen |
| Timezone | UTC-only (Q1 waived for V2; store-local reserved + rejected) |
| Authoritative now | From QTC only; no wall clock in filtering |
| Recipes | today, yesterday, last_n_days, current/previous week/month, explicit_range, comparison_period, simulation/historical/recovery replay ranges |

## 10. Reality Contract impact

None — no consumer bind; Lab contrast fixtures remain for WP-4+.

## 11. Operational performance impact

Window construction: no I/O, no DB, no network, no unbounded loops; micro-benchmark in tests (&lt;1s for 1500 constructions). Merchant request paths unchanged (no callers). Scheduler/pool unchanged.

## 12. Database/query impact

None. Contract produces index-friendly bounds (`>= start AND < end`) but executes no queries.

## 13. Architectural Debt Introduced

**None.**

Temporary compatibility: `WindowRecipeId.THIS_MONTH` / alias `this_month` → `current_month` (vocabulary bridge; not a second filtering system). Removal: optional cleanup after all consumers use `current_month` (no dedicated WP required; may fold into WP-4+).

## 14. Consumer Migration Status

| Consumer | Status |
|----------|--------|
| Dashboard | Not Started |
| Knowledge | Not Started |
| Daily Brief | Not Started |
| Monthly Summary | Not Started |
| Attention | Not Started |
| Timeline | Not Started |
| Movement | Not Started |
| Purchase Truth | Not Started |
| Simulator binding | Not Started |

## 15. Risks introduced

| Risk | Level | Notes |
|------|-------|-------|
| Recipe bounds vs legacy consumer math | Medium | Mitigated by golden tests at migration WPs; last_n_days matches KL rolling shape |
| Store TZ still parked | Low | Explicit rejection of reserved policy; no silent invention |

**Regression risk:** Low (capability-only).

## 16. Rollback confirmation

1. Revert WP-3 commit(s) on `feature/inv001-wp3` (remove `filtering.py`, `emptiness.py`, WP-3 tests/exports).  
2. Preserve WP-1 and WP-2.  
3. No consumer rollback required.  
4. Production behaviour unchanged (no callers).

## 17. Evidence

- Time Contract tests: `tests/time_authority/test_wp3_filtering.py`  
- Suite: `tests/time_authority/` → 77 passed  
- AST/static checks: no `datetime.now` / DB / network in filtering/emptiness  
- `main.py` contains no filtering registration

## 18. main.py impact assessment

**None.** No change required or made. Filtering is not registered at composition root.

## 19. Recommendation on whether WP-4 may begin

**No.** STOP after WP-3. Await Architecture Review and explicit approval before Knowledge migration (WP-4).

## 20. Q1 / Q3 waiver (WP-3 coding gate)

| Question | Waiver for WP-3 |
|----------|-----------------|
| Q1 store timezone | UTC-only for V2 boundaries; `STORE_LOCAL_RESERVED` hook rejects |
| Q3 interval openness | Universal `[start, end)` |

---

**STOP.** Do not begin WP-4. Do not migrate consumers.
