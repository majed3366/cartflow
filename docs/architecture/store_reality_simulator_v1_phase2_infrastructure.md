# Store Reality Simulator V1 — Phase 2 Infrastructure

**Status:** Phase 2 complete — **STOP for review**  
**Date (UTC):** 2026-07-15  
**Commit scope:** Core infrastructure only — **no event generation, no scenario execution**

---

## Approved decisions (implemented)

| Decision | Approach |
|----------|----------|
| Timestamp Authority | **Clock Injection** — `SystemClock` (production) / `SimulationClock` (simulation) via contextvars |
| Orchestration persistence | **Hybrid** — `simulation_runs` + `simulation_row_index`; config/accounting/checkpoint/progress as JSON |
| Cleanup | **Tagged-only** via `simulation_row_index` + `simulation_run_id` |
| Safe delivery | **Simulation Adapter** + demo-only reject |
| Principle | Generate governed reality later; never inject derived truth |

---

## Architecture (Phase 2)

```
┌─────────────────────────────────────────────────────────────┐
│ simulation_scope(run_id, SimulationClock)                   │
│   contextvars: SimulationContext + active Clock             │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
                ▼                             ▼
┌───────────────────────────┐   ┌─────────────────────────────┐
│ Platform truth-path now() │   │ Outbound delivery           │
│ timeline / movement /     │   │ send_whatsapp               │
│ purchase / closure /      │   │ send_whatsapp_message       │
│ schedule survival         │   │ → safe_delivery_adapter     │
│ → utc_now() / get_clock() │   │   demo-only + mock/suppress │
└───────────────────────────┘   └─────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Orchestration (DB)                                          │
│ simulation_runs: status, seed, dates, accounting JSON,      │
│   checkpoint JSON, progress JSON, config JSON               │
│ simulation_row_index: tagged PKs for cleanup isolation      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Registry / helpers (no execution)                           │
│ scenario_registry · config_loader · identity · seed ·       │
│ accounting · checkpoint · progress · cleanup                │
└─────────────────────────────────────────────────────────────┘
```

---

## Package layout

```
services/store_reality_simulator/
  __init__.py
  contracts_v1.py
  clock_v1.py
  context_v1.py
  seed_v1.py
  identity_v1.py
  scenario_registry_v1.py      # metadata only
  config_loader_v1.py
  accounting_v1.py
  run_registry_v1.py
  checkpoint_v1.py
  progress_v1.py
  row_index_v1.py
  safe_delivery_adapter_v1.py
  cleanup_v1.py
```

Migration: `alembic/versions/s1t2u3v4w5x6_store_reality_simulator_phase2.py`  
(merges heads `p2q3r4s5t6u7` + `r4s5t6u7v8w9`)

Models: `SimulationRun`, `SimulationRowIndex` in `models.py`

---

## Clock injection wiring (Phase 2)

`simulation_scope(...)` activates `SimulationClock` via contextvars and **patches**
participating modules' `_utc_now` for the scope duration (then restores):

- `recovery_truth_timeline_v1`
- `customer_movement_snapshot_v1`
- `cartflow_purchase_truth` / `purchase_truth`
- `lifecycle_closure_records_v1`
- `recovery_restart_survival`

Platform code therefore believes simulated time is real time while the scope is active.
Outside the scope, production uses wall-clock `SystemClock` unchanged.

---

## Safe delivery wiring

- `services/whatsapp_send.send_whatsapp` — early guard
- `main.send_whatsapp_message` — early Meta CTA guard
- Fail-closed if adapter unavailable while simulation is active

---

## Explicitly not implemented (Phase 3+)

- Scenario execution / historical event generation
- Visits, scrolls, widget/WA/purchase journey planners
- Knowledge / dashboard / movement / monthly data injection (forbidden forever)
- Admin control UI routes
- Full platform-wide `_utc_now` retrofit (additional services as they join simulation)

---

## Tests

`tests/test_store_reality_simulator_phase2_v1.py` — clock, seed, identity, config, run persistence, checkpoint/resume, accounting init, adapter, demo protection, cleanup isolation, progress, restart recovery.

---

## STOP

Phase 2 stops here. Do not generate events or start Phase 3 until architectural review.
