# Work Package Review — WP-2 Query Time Context

| Field | Value |
|-------|-------|
| Investigation | INV-001 |
| Work Package | WP-2 |
| Branch | `feature/inv001-wp2` |
| Date submitted (UTC) | 2026-07-16 |
| Decision | ☐ Approved — **awaiting Architecture Review** |

## 1. Summary

Implemented governed Query Time Context propagation: enriched immutable model (mode, provenance, authoritative_now, timezone policy UTC, correlation/request/job/simulation/replay ids, opaque scope_key), build/validate/activate lifecycle, request/worker/replay/simulation/frozen scopes via contextvars, HTTP middleware with **minimal** `main.py` registration. No consumer migration. Merchant ambient behaviour unchanged (SystemClock).

## 2. Commit hash

`47647e83d298409bb480a8b83f9e4237b1a95227`

## 3. Branch name

`feature/inv001-wp2`

## 4. Files created

| Path |
|------|
| `services/time_authority/context_scope.py` |
| `services/time_authority/http_middleware.py` |
| `tests/time_authority/test_wp2_query_time_context.py` |
| `docs/investigations/WP-02_BRIEF.md` |
| `docs/investigations/WP-02_REVIEW.md` |

## 5. Files modified

| Path |
|------|
| `services/time_authority/query_context.py` |
| `services/time_authority/contracts.py` |
| `services/time_authority/authority.py` |
| `services/time_authority/validators.py` |
| `services/time_authority/__init__.py` |
| `services/time_authority/README.md` |
| `tests/time_authority/test_wp1_platform_time_authority.py` (provenance version assert) |
| `main.py` (2-line middleware registration only) |
| `docs/SYSTEM_SUMMARY.md` |
| `docs/investigations/INV-001.md` |
| `docs/investigations/INVESTIGATION_DASHBOARD.md` |

## 6. Files intentionally untouched

Knowledge, Dashboard, Timeline, Purchase Truth, Monthly, Attention, Movement, `store_reality_simulator` engine bind, filtering/emptiness modules.

## 7. Tests executed

```text
python -m pytest tests/time_authority/ -q
```

## 8. Results

**42 passed** (WP-1 + WP-2)

## 9. Architectural observations

- Canonical kinds unchanged (`current_production`, `simulation`, …); aliases `production`/`test` at boundaries only.
- Simulation requires `simulation_run_id` (fail closed).
- Timezone policy frozen to UTC pending Architecture Q1.
- Provenance marked `merchant_visible: False`.
- Reality Simulator `simulation_scope` remains separate until WP-10.

## 10. Risks introduced

| Risk | Level | Notes |
|------|-------|-------|
| HTTP middleware always activates production QTC | Low | Same SystemClock; no merchant result change |
| Pytest name collision with `test*` helpers | Mitigated | Renamed to `frozen_clock_scope` |

**Regression risk:** Low

## 11. Rollback confirmation

1. Revert WP-2 commits on `feature/inv001-wp2`.  
2. Remove `register_query_time_context_middleware(app)` from `main.py`.  
3. WP-1 foundation remains.  

Independently reversible: **Yes**.

## 12. Evidence

Pytest 42 passed; this review.

## 13. `main.py` impact assessment

| Question | Answer |
|----------|--------|
| Modified? | Yes — composition only |
| Diff | Import + `register_query_time_context_middleware(app)` |
| Business/time logic in main? | **No** |
| Responsibility increased beyond composition? | **No** |

## 14. Reality Contract impact

No change to Reality Simulator behaviour. Simulation QTC helper is opt-in Time Authority mode only.

## 15. Time Contract impact

Propagation + provenance foundation only. No filtering windows (WP-3). Ambient production path unchanged.

## 16. Recommendation

**WP-3 may begin only after Architecture Approval of this WP-2 review.**
