# INV-002 Phase 5 Review — Reality Attach

| Field | Value |
|-------|-------|
| Investigation ID | INV-002 |
| Work Package | Phase 5 — Reality Attach |
| Title | Bind Reality Simulator to Platform Time + Identity Authorities |
| Branch | `feature/inv002-phase5` |
| Delivery commit | *(stamped at commit)* |
| Author | Engineering (agent) |
| Reviewer | ☐ Architecture Board |
| Date submitted (UTC) | 2026-07-17 |

---

## Executive Summary

Reality Attach is implemented as an **authority-input binder only**. It registers a simulation run declaration, binds `SimulationClock` / as-of into **Platform Time Authority** (Query Time Context + `SimulationClockProvider`), and supplies ATTACH-path fields so **Platform Identity Authority** seals MQIC to the run’s canonical store. Attach is explicitly **not** an authority (`is_authority: false`). Home, Knowledge, Daily Brief, and Timeline remain consumers of MQIC / Time Authority with **no surface rewrites**.

**STOP:** Merchant Reality Validation / RV-C campaign / INV-002 closure **not started**.

---

## Commit hash / Branch

| Field | Value |
|-------|--------|
| **Branch** | `feature/inv002-phase5` |
| **Base** | `feature/inv002-wp6` @ `2b076c5` |
| **Delivery commit** | *(stamped at commit)* |
| **ICT command** | `python -m pytest tests/identity_authority/ -q --tb=line` |
| **ICT result** | **80 passed** |
| **Phase 5 attach tests** | **14 passed** (`test_phase5_reality_attach.py`) |
| **`main.py` impact** | **None** |

---

## Files created

| Path |
|------|
| `services/identity_authority/reality_attach_v1.py` |
| `tests/identity_authority/test_phase5_reality_attach.py` |
| `Phase5_REVIEW.md` |

## Files modified

| Path | Change |
|------|--------|
| `services/identity_authority/__init__.py` | Export Phase 5 attach API; `__version__ = "7"` |
| `services/identity_authority/session_membership_v1.py` | Merge active attach inputs into Phase 3 `ResolveIdentityInput`; ATTACH in diagnostics paths |
| `docs/SYSTEM_SUMMARY.md` | §10 changelog |
| `docs/investigations/INV-002.md` | Status: Phase 5 delivered; await RV-C |

## Files intentionally untouched

| Path / class | Reason |
|--------------|--------|
| `main.py` | Composition-only; no attach business rules (ICT-40) |
| `services/merchant_timeline_v1.py` | Consumer unchanged |
| `services/merchant_home_composition_v1.py` | Consumer unchanged |
| `services/knowledge_*` / Daily Brief routes | Consumer unchanged |
| `services/store_reality_simulator/**` | Simulator remains write/lab engine; Attach binds authorities |
| Widget / Setup / WhatsApp / Recommendations | Out of scope (RV-B) |
| Provider adapters / alias directory | Phase 6 |

---

## Authority chain verification

```text
Reality Simulator declaration
        │
        ▼
Reality Attach (input binder only — not an authority)
        │
        ├─▶ Time Authority  →  QTC SIMULATION + SimulationClockProvider
        │
        └─▶ Identity Authority → ResolveMQIC ATTACH → sealed MQIC
                    │
                    ▼
         Home / Knowledge / Brief / Timeline  (unchanged consumers)
```

| Check | Result |
|-------|--------|
| Reality consumes Platform Authorities | **PASS** |
| One MQIC | **PASS** (dual-resolve fail closed) |
| One Time Authority | **PASS** (`authority_now` / QTC only) |
| No duplicate authority chain | **PASS** (`_assert_chain_contracts`) |
| Fail closed on mismatch | **PASS** (membership / slug / dual attach) |

---

## MQIC verification

| Assert | Evidence |
|--------|----------|
| ATTACH path sets run canonical | `test_ict20_attach_sets_mqic_to_run_canonical` |
| Authority owner unchanged | `test_mqic_authority_owner_unchanged` |
| Phase 3 merge yields ATTACH | `test_phase3_declaration_merges_attach_inputs` |
| Consumers share attached MQIC | `test_consumers_unchanged_use_attached_mqic` |
| Production path without attach | `test_production_path_unaffected_without_attach` |

---

## Time Authority verification

| Assert | Evidence |
|--------|----------|
| SimulationClock → TA provider | `test_attach_binds_time_authority_simulation_clock` |
| `authority_now()` = sim start | Same |
| Source id `simulation` | Same |
| Detach restores ambient | `test_attach_removed_cleanly` |

---

## Attach diagnostics

`attach_diagnostics()` exposes (ops only, not merchant UX):

- Attach state / lifecycle state  
- Authority health (IA + TA bound flags, path, QTC mode)  
- Simulation provenance (run id, time source, authority sources, identity provenance, canonical, replay)  
- Lifecycle diagnostics  

`is_authority` is always `false`.

---

## Attach contracts

| Contract | Status |
|----------|--------|
| ICT-20 Attach → run canonical MQIC | **PASS** |
| ICT-21 Unauthorized attach rejected | **PASS** |
| Attach / detach clean | **PASS** |
| Deterministic replay | **PASS** |
| Fail-closed mismatch | **PASS** |

---

## Regression tests

| Suite | Result |
|-------|--------|
| `tests/identity_authority/` (full ICT) | **80 passed** |
| Prior WP-1…WP-6 suites | Included; green |

---

## Deterministic replay evidence

Same declaration (`RUN_ID`, May-end start, fixed correlation) → identical `(store_slug, canonical, simulation_run_id, path, authority_now, qtc.run_id)` across two attach cycles (`test_deterministic_replay_preserved`).

---

## Query / I/O / Latency / Scheduler / Pool impact

| Dimension | Impact |
|-----------|--------|
| **Query** | **None** — no new DB query class; membership supplied by caller / existing Phase 3 loaders |
| **I/O** | **None** — no provider HTTP |
| **Latency** | Negligible contextvar + resolve (same ResolveMQIC) |
| **Scheduler** | **None** |
| **Pool** | **None** |

---

## Merchant-facing behaviour comparison

| Surface | Before Phase 5 | After Phase 5 (no attach) | After Phase 5 (attached) |
|---------|----------------|---------------------------|--------------------------|
| Home / KL / Brief / Timeline | Consume MQIC | **Unchanged** | Consume **same** MQIC APIs; tenant = run canonical when Attach active |
| Merchant chrome | No attach fields | Unchanged | Unchanged (diagnostics ops-only) |

---

## Rollback boundary

| Action | Effect |
|--------|--------|
| Revert Phase 5 commit / remove `reality_attach_v1` | Production session path intact |
| Platform Identity Authority | Intact |
| Platform Time Authority | Intact |
| Consumers | Intact (no consumer diffs to revert) |

`git revert <delivery>` **or** reset to `2b076c5`.

---

## Recommendation for RV-C

**Ready for Architecture Review of Phase 5.** After Board acknowledgment:

1. Open **RV-C** (Simulation attach honesty) — Small Reality (or equivalent) run’s canonical ≡ walkthrough MQIC after Attach; session surfaces see sim truth under QTC; probe-`demo` alone insufficient.  
2. Do **not** start full Merchant Reality Validation campaign until RV-C passes.  
3. Do **not** close INV-002.

---

## STOP

No Merchant Reality Validation.  
No RV-C execution in this delivery.  
No INV-002 closure.  
Await Architecture Review and RV-C authorization.
