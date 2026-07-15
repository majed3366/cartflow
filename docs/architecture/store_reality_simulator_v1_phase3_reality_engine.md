# Store Reality Simulator V1 — Phase 3 Controlled Reality Engine

**Status:** Phase 3 complete — **STOP for architectural and product review**  
**Date (UTC):** 2026-07-15  
**Scope:** Governed historical behaviour for the demo merchant only. No Phase 4. No product-logic changes from findings.

---

## Principle

The Reality Engine exercises the **real** CartFlow platform. Derived truth (Purchase Truth, Movement, Knowledge, Dashboard, Timeline, Recovery, Attention) remains exclusively owned by CartFlow. The simulator is subordinate to the platform; production architecture always wins.

---

## What Phase 3 delivers

| Capability | Module / artifact |
|------------|-------------------|
| Governed behaviour planning | `planner_v1.py`, `behavior_catalog_v1.py` |
| Scenario versioning | `scenario_registry_v1.py` (`scenario_id` / `scenario_version` / `scenario_revision`) |
| Progressive scale | `scale_profiles_v1.py` — small→medium→large→full→stress |
| Batched execution + clock | `reality_engine_v1.py` + Phase 2 `SimulationClock` |
| Service-boundary ingress | `ingress_adapter_v1.py` (demo-only; mock WA; no providers) |
| Cold event ledger | `simulation_event_ledger` + `event_ledger_v1.py` |
| Hot run metadata | extended `simulation_runs` columns |
| Manifest + replay | `manifest_v1.py` → `simulation_manifest.json` |
| Reality Score (internal) | `reality_score_v1.py` — never merchant-facing |
| Performance guards | `performance_guards_v1.py` — auto-pause |
| Archive / restore / delete | `archive_v1.py` + `simulation_run_archives` |
| Validation report | `validation_report_v1.py` — findings only |
| Simulation dashboard payload | `observability_v1.py` — internal only |

Migration: `alembic/versions/t2u3v4w5x6y7_store_reality_simulator_phase3.py`  
Tests: `tests/test_store_reality_simulator_phase3_v1.py`

---

## Architecture

```
Config + seed + scale_profile
        |
        v
+-------------------+     cold      +------------------------+
| Reality Planner   |-------------->| simulation_event_ledger|
| (deterministic)   |               | (archive-ready)        |
+---------+---------+               +-----------^------------+
          | manifest + reality score            | status updates
          v                                     |
+-------------------+   batches + guards   +----+---------------+
| simulation_runs   |<---------------------| Reality Executor   |
| (hot metadata)    |   checkpoint/pause   | simulation_scope   |
+-------------------+                      +---------+---------+
                                                     |
                          service-boundary ingress   |
                                                     v
                    Cart / Reason / Phone / Movement / Schedule /
                    Mock WA / Purchase Truth  --> platform pipelines
```

---

## Scenario versioning

Every scenario carries:

- `scenario_id` (canonical, e.g. `S03_shipping_cost_hesitation`)
- `scenario_version` (e.g. `v1`)
- `scenario_revision` (integer)

Aliases (e.g. `shipping_hesitation` → S03) resolve before planning. Manifests and ledger rows record the exact version executed for replay.

---

## Simulation manifest

Every plan/execute path builds `simulation_manifest.json` with:

Simulation Run ID, Seed, Scenario IDs/Versions, Commit Hash, Platform Version, Start/End Date, Clock Mode, Products, Customers, Sessions, Expected Events, Configuration, Execution Time, Reality Score, Warnings, Known Limitations, and a `replay` block.

Written under `docs/architecture/srs_runs/<run_id>/` when the filesystem allows.

---

## Reality Score

Internal-only dimensions (examples): customer / traffic / purchase / product / recovery / knowledge / timeline / session / behaviour realism → overall.  
`merchant_facing: false` / `internal_only: true`. Never exposed on merchant surfaces.

---

## Isolation and safety

- Demo store only
- Never on merchant request paths
- Independent run registry, checkpoints, accounting, ledger, logging, metrics payload
- Safe delivery adapter: no real WhatsApp / provider calls
- Tagged-only cleanup by `simulation_run_id`
- Hot metadata vs cold ledger; archives remain replayable

---

## Performance protection

- Batch size + max events per run (profile-bounded)
- Pause between batches
- Checkpoint after every batch
- Pool / memory / failure / batch-latency guards → **auto-pause**
- Resume only via explicit execute call after pause

If protecting production conflicts with simulation convenience, production wins.

---

## Progressive scale (never max first)

| Profile | Days | Intent |
|---------|------|--------|
| small | 3 | Controlled validation |
| medium | 14 | Medium history |
| large | 30 | Large history |
| full | 60 | Full history |
| stress | 90+ | Stress — never first |

---

## Validation report (findings only)

Completed/paused runs produce an internal report covering Reality Score, performance, knowledge/dashboard/timeline/purchase/movement/recovery reviews, data growth, query/memory notes, architectural findings, weaknesses, unexpected behaviour, and recommended improvements.

**Phase 3 does not change product logic based on these findings.**

---

## Known limitations (honest)

1. Storefront chrome events (page/scroll/dwell/widget_open) remain **unsupported markers** in the plan (not faked into platform tables).
2. Ingress is **service-boundary** under `SimulationClock`, not full HTTP TestClient wall-clock paths.
3. Purchase Truth may remap `demo` → linked Zid store slug (platform behaviour).
4. First purchase in test/SQLite can trigger DB READY warm path (long batch wall); guards still apply with configurable thresholds.
5. Knowledge Layer visitor metrics may remain unavailable (platform gap from Phase 1).

---

## Success criteria checklist

| Criterion | Status |
|-----------|--------|
| Believable governed behaviour (not random noise) | Met (catalog + planner) |
| Meaningful historical sequences | Met (journeys over scale days) |
| CartFlow derives conclusions | Met (real Purchase Truth / pipelines) |
| Performance guards + pause | Met |
| Merchant isolation (demo only, no outbound) | Met |
| Governed data growth (batch/caps/archive) | Met |
| Reality Score generated | Met |
| Manifest generated | Met |
| Scenario versioning | Met |
| No product-logic regression changes | Met (findings-only) |

---

## STOP

Do **not** begin Phase 4.  
Do **not** optimize.  
Do **not** change product logic from findings.  
Await architectural and product review.
