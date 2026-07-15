# CartFlow Store Reality Simulator V1 — Phase 3 Report

**Status:** COMPLETE — STOP for architectural and product review  
**Date (UTC):** 2026-07-15  
**Package:** `services/store_reality_simulator/`

---

## Verdict

Phase 3 delivers a **Controlled Reality Engine** that plans and executes governed historical merchant behaviour for the **demo** store only, through real CartFlow pipelines, with isolation, performance guards, versioned scenarios, manifests, Reality Score, cold ledger, archive, and findings-only validation reports.

No Phase 4 work. No product-logic changes from findings.

---

## Deliverables

1. Reality Engine (`reality_engine_v1.py`) — plan / dry-run / batched execute / auto-pause  
2. Planner + behaviour catalog — deterministic journeys (browse → cart → hesitation → WA mock → purchase patterns)  
3. Scenario versioning (`scenario_id` / `scenario_version` / `scenario_revision` + aliases)  
4. Scale profiles — small (3d) → medium → large → full → stress (never first)  
5. `simulation_manifest.json` builder + on-disk write under `docs/architecture/srs_runs/`  
6. Reality Score (internal only)  
7. Cold `simulation_event_ledger` + hot run metadata columns  
8. Performance guards (pool / batch latency / failures / memory hook)  
9. Archive / restore / delete (`simulation_run_archives`)  
10. Validation report + internal simulation dashboard payload  
11. Migration `t2u3v4w5x6y7`  
12. Tests: `tests/test_store_reality_simulator_phase3_v1.py` (+ Phase 2 suite still green)  
13. Architecture doc: `docs/architecture/store_reality_simulator_v1_phase3_reality_engine.md`

---

## How to run (demo only)

```python
from services.store_reality_simulator.reality_engine_v1 import (
    dry_run_reality,
    execute_reality_run,
)

planned = dry_run_reality({
    "scenario_ids": ["S01_normal_store_baseline", "shipping_hesitation"],
    "seed": 7,
    "start_date": "2026-05-01",
    "scale_profile": "small",  # start small
})

# Execute after review / when mode prepared:
# execute_reality_run(planned["simulation_run_id"], max_batches=20)
```

---

## Success criteria

| Criterion | Result |
|-----------|--------|
| Believable governed behaviour | PASS |
| Meaningful historical behaviour | PASS |
| Platform derives truth | PASS (Purchase Truth ingest observed) |
| Performance protections | PASS (guards + auto-pause) |
| Dashboard/merchant isolation | PASS (demo + mock WA) |
| Data growth governed | PASS (caps, batches, cold ledger, archive) |
| Reality Score | PASS |
| Manifest | PASS |
| Scenario versioning | PASS |
| No product-logic changes from findings | PASS |

---

## Architectural findings (report only — do not fix in Phase 3)

1. **Unsupported storefront chrome** still cannot become Knowledge visitor metrics — markers only.  
2. **Service-boundary ingress** (not full HTTP) is the Time Machine–compatible path; document for Phase 4 if HTTP parity is required.  
3. **Purchase store remapping** (`demo` → linked Zid slug) is platform behaviour; simulator must not override.  
4. **Purchase reconcile → DB READY warm** can inflate batch wall time in SQLite/test; guards correctly pause unless thresholds are raised for validation jobs.  
5. Store identity alias conflict warnings (`demo` / cartflow_zid) appear under test fixtures — platform concern, not simulator ownership.

---

## STOP

Await review before Phase 4 or any product changes driven by this report.
