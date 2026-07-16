# Work Package Review — WP-4 Knowledge Time Authority Migration

| Field | Value |
|-------|-------|
| Investigation | INV-001 |
| Work Package | WP-4 |
| Branch | `feature/inv001-wp4` |
| Date submitted (UTC) | 2026-07-16 |
| Decision | ☐ Approved — **awaiting Architecture Review** |

## 1. Summary

Knowledge merchant temporal windows now derive exclusively from Time Authority via `services/knowledge_time_authority_v1.py` (`last_n_days` + `comparison_period`). Legacy `_window_bounds` / `_utc_now` removed from metrics and product metrics. Production Golden Comparison: V2 bounds identical to frozen pre-WP-4 formula. Simulation/historical contexts select May evidence while July production inject returns zero for the same DB. `main.py` untouched.

## 2. Commit hash

_(recorded after commit)_

## 3. Branch name

`feature/inv001-wp4`

## 4. Files created

| Path |
|------|
| `services/knowledge_time_authority_v1.py` |
| `tests/time_authority/test_wp4_knowledge_migration.py` |
| `docs/investigations/WP-04_BRIEF.md` |
| `docs/investigations/WP-04_REVIEW.md` |

## 5. Files modified

| Path |
|------|
| `services/knowledge_metrics_v1.py` |
| `services/knowledge_product_metrics_v1.py` |
| `services/knowledge_layer_v1.py` |
| `services/knowledge_health_v1.py` |
| `docs/SYSTEM_SUMMARY.md` |
| `docs/investigations/INV-001.md` |
| `docs/investigations/INVESTIGATION_DASHBOARD.md` |

## 6. Files intentionally untouched

`main.py`; Dashboard; Daily Brief; Monthly Summary; Attention; Timeline; Movement; Purchase Truth; Simulator bind; `routes/knowledge.py` (already passes `window_days` only); routing/producer `_utc_now_iso` metadata stamps.

## 7. Knowledge paths migrated

| Path | Recipe |
|------|--------|
| `knowledge_metrics_v1.collect_knowledge_metrics` | `last_n_days` + `comparison_period` |
| `knowledge_product_metrics_v1.collect_knowledge_product_metrics` (+ session lane window) | `last_n_days` |
| `knowledge_layer_v1.build_knowledge_report` stamp | QTC / inject `authoritative_now` |
| `knowledge_health_v1.build_knowledge_health` stamp | same |
| Attribution / insights | Consume metrics bounds (no private window math) |

## 8. Knowledge paths deferred

| Path | Owner |
|------|--------|
| `product_foundation_health_v1` open-ended `>= start` (no `< end`) | Align upper bound in Product Foundation / later KL bridge hardening — **not WP-5**; note for Architecture |
| `knowledge_routing_v1` / `knowledge_producer_metadata_v1` publish/route timestamps | Not filtering windows — leave |
| Client `merchant_knowledge_layer.js` `window_days=7` param | Presentation param only — WP-11 if needed |

## 9. Tests executed and results

```text
python -m pytest tests/time_authority/ tests/test_knowledge_layer_v1.py \
  tests/test_knowledge_layer_v1_completion_v1.py tests/test_knowledge_layer_migration_v1.py -q
```

**151 passed** (time_authority WP-1…WP-4 + core KL suites). Additional Knowledge routing/dashboard suites run separately.

## 10. Golden Comparison evidence

Frozen legacy formula in `test_wp4_knowledge_migration.py::_legacy_knowledge_window_bounds` matched against `resolve_knowledge_windows` for `window_days ∈ {1,7,14,30,90}` × boundary `now` values (May, July, leap day, year end, midnight). **All identical.**

## 11. Production equivalence result

**PASS** — bounds identical; deterministic metrics/insights for same `now`; merchant `to_dict()` omits internal provenance; existing KL tests green.

## 12. Simulation/historical correctness result

**PASS** — July inject → `cart_count=0`; `simulation_scope` / `historical_replay_scope` at May → carts visible; provenance carries `simulation_run_id` / `replay_id`.

## 13. Query-count comparison

Instrumented `before_cursor_execute` on metrics collection: count stable across repeated calls; no query explosion (`< 40`). Window construction adds **0** DB queries (pure bridge).

## 14. Query-shape/index evidence

Migrated collectors retain `timestamp >= start AND timestamp < end` (naive UTC bounds). No `func.date` / `func.year` wrapping on window columns.

## 15. Operational performance impact

Window resolve O(1), I/O-free. No material latency path change; focused micro-bench &lt;1s for 1000 resolves.

## 16. Scheduler impact

None.

## 17. Pool impact

None — same request-scoped Knowledge reads; no extra sessions.

## 18. Architectural Debt Introduced

**None.**

Legacy `_window_bounds` / `_utc_now` removed from migrated Knowledge modules (not left as parallel authority). Golden legacy formula exists **only in tests**.

## 19. Consumer Migration Status

| Consumer | Status |
|----------|--------|
| Knowledge | **Migrated** (approved scope) |
| Dashboard | Not Started |
| Daily Brief | Not Started |
| Monthly Summary | Not Started |
| Attention | Not Started |
| Timeline | Not Started |
| Movement | Not Started |
| Purchase Truth | Not Started |
| Simulator binding | Not Started |

## 20. Risks introduced

| Risk | Level | Notes |
|------|-------|-------|
| Foundation health still open-ended upper bound | Low | Lower bound now authority-aligned; deferred close |
| Ambient production uses QTC middleware now | Low | Same SystemClock as prior wall default |

## 21. Rollback confirmation

1. Revert WP-4 commit(s) on `feature/inv001-wp4`.  
2. Preserve WP-1…WP-3.  
3. No other consumer rollback.  
4. Production Knowledge windows restore to private `_window_bounds` behaviour.

## 22. Time Contract impact

Knowledge is first consumer of WP-3 recipes; production maths unchanged; non-production contexts now honored.

## 23. Reality Contract impact

Partial Gate A prep — Lab-class wall vs as-of contrast covered in WP-4 tests. Full Reality Lab still Gate A after WP-5.

## 24. main.py impact assessment

**None.**

## 25. Recommendation on whether WP-5 may begin

**No.** STOP after WP-4. Await Architecture Review and explicit approval before Dashboard migration.

---

**STOP.** Do not begin WP-5.
