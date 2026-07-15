# Store Reality Simulator V1 — Identity Isolation Report (Phase 3.1)

**Status:** COMPLETE — STOP for architectural review  
**Date (UTC):** 2026-07-15  
**Scope:** Architecture verification only. No Phase 4. No scenario expansion. No product-logic redesign beyond mandatory isolation pins/guards.

---

## 1. Architecture summary

The Store Reality Simulator writes **source events** for the canonical demo merchant (`store_slug=demo`) through service-boundary ingress under `simulation_scope`. Derived surfaces (Knowledge, Dashboard, Monthly Summary, Attention) are never written by the simulator.

Phase 3.1 adds a **permanent identity isolation layer**:

| Control | Location |
|---------|----------|
| Pre-write gate (`demo` + `simulation_run_id`) | `identity_guard_v1.require_simulation_write_identity` |
| Recovery key prefix `demo:` | `assert_recovery_key_isolated` |
| Post-write store assertion | `assert_written_store_is_demo` |
| Purchase Truth pin while sim active | `recovery_store_context.resolve_purchase_truth_store_slug` |
| No alias expansion of recovery-key head while sim active | `canonical_store_slug_from_recovery_key` |
| Outbound provider block | `safe_delivery_adapter_v1` (Phase 2) |

**Principle:** Simulation identity must never escape. If a write would land under a real merchant identity, the architecture fails closed (abort + `CRITICAL SIMULATION ISOLATION FAILURE`).

---

## 2. Identity resolution graph

```
Simulator config.store_slug
        |
        v
 assert_demo_store / require_simulation_write_identity
        |
        v
 recovery_key = "demo:srs_..."   (identity_v1.simulation_recovery_key)
        |
        +---> AbandonedCart.store_id --> Store.zid_store_id == "demo"
        +---> schedules / reasons / logs / movement.store_slug == "demo"
        +---> Purchase Truth ingest
                    |
                    v
         resolve_purchase_truth_store_slug
                    |
         [SIM ACTIVE] ---- pin ----> "demo"   (Phase 3.1)
                    |
         [PROD PATH]  ---- may remap via ---->
              canonical_store_slug_from_recovery_key
              --> resolve_canonical_store_slug (alias table)
              --> coerce_cart_event_store_slug (auth merchant)
```

---

## 3. Purchase Truth identity path

| Step | File | Function | Behaviour |
|------|------|----------|-----------|
| Ingest entry | `services/purchase_truth.py` | `ingest_purchase_truth` | Calls resolve then `record_purchase` |
| Store authority | `services/recovery_store_context.py` | `resolve_purchase_truth_store_slug` | **Was unsafe for sim** (see §8); **now pins `demo` when simulation active** |
| Canonical head | same | `canonical_store_slug_from_recovery_key` | **Was expanding `demo` via alias**; **now returns literal head when simulation active** |
| Durable row | `services/cartflow_purchase_truth.py` | `record_purchase` | Persists `store_slug` from resolved value |
| Simulator post-check | `ingress_adapter_v1._purchase` | `assert_written_store_is_demo` | Aborts if row escaped |

**Owner of remapping (platform):** Recovery store-context / store-identity alias system — intentional for production checkout where payload says `demo` but recovery_key is merchant zid. **Not acceptable for simulation.**

---

## 4. Provider identity path

| Path | Result |
|------|--------|
| `simulation_outbound_guard` | Blocks all real WhatsApp/provider sends while sim active; rejects non-demo slug |
| Ingress mock WA | Writes `CartRecoveryLog` with `store_slug=demo`, `status=mock_sent`; never calls Twilio/Meta |
| Zid / Salla / Shopify gateway | Not invoked by Reality Engine ingress |

**Confirmed:** Simulation does not enter provider identity resolution for delivery.

---

## 5. Recovery identity path

| Artifact | Isolation |
|----------|-----------|
| `recovery_key` | Always `demo:srs_...` from planner; guarded by `assert_recovery_key_isolated` |
| `RecoverySchedule.store_slug` | Forced `demo` |
| Timeline events | Written with `store_slug=demo` |
| Lifecycle closure | Uses Purchase Truth resolved slug (pinned to `demo` in sim) |

---

## 6. Simulation identity path

1. Config loader rejects non-demo `store_slug`.  
2. Run registry stores `store_slug=demo`.  
3. `simulation_scope` asserts demo + non-empty `simulation_run_id`.  
4. Every durable ingress write calls `require_simulation_write_identity`.  
5. Cleanup is tagged-only by `simulation_run_id` (never broad demo wipe).

---

## 7. Every identity transformation

| Transformation | Production intent | Simulation treatment |
|----------------|-------------------|----------------------|
| `demo` → linked Zid via alias (`resolve_canonical_store_slug`) | Unify merchant identity | **Blocked** while sim active (literal head / pin) |
| Sandbox payload → authenticated merchant (`coerce_cart_event_store_slug`) | Attach cart to logged-in merchant | **Skipped** when pin returns early |
| Recovery-key prefix wins over sandbox payload | Match active merchant cart | **Pinned** to `demo` in sim |
| `reconcile_recovery_identity` sandbox→merchant rebuild | Production recovery identity | Not used by SRS ingress writers |

---

## 8. Potential escape points

| # | Escape | Severity (pre-fix) | Status after 3.1 |
|---|--------|----------------------|------------------|
| E1 | Purchase Truth remaps `demo` → linked Zid via alias | **CRITICAL** | **Closed** — pin + post-write assert |
| E2 | `canonical_store_slug_from_recovery_key` expands `demo` | **CRITICAL** | **Closed** — literal head in sim |
| E3 | Non-demo `store_slug` in ingress | High | **Closed** — pre-write gate |
| E4 | Missing `simulation_run_id` | High | **Closed** — abort |
| E5 | Outbound WA to provider | High | **Closed** — Phase 2 adapter |
| E6 | Knowledge/Dashboard consuming remapped PT under merchant | Critical if E1 open | **Mitigated** by E1 close |
| E7 | Untagged side-effects from purchase reconcile (DB READY / other carts) | Medium | Monitor — cleanup is tagged-only; reconcile may touch related demo carts |
| E8 | `demo` Store row vs alias conflict (fixture/prod alias pollution) | Medium | Documented — sim must not rely on alias; pin bypasses it |

---

## 9. Confirmed safe paths

- Config / run registry / context: demo-only  
- Planner recovery keys: `demo:` prefix  
- Cart / reason / schedule / mock WA writers: explicit `demo`  
- Movement ingress: `store_slug=demo` + assert  
- Purchase Truth under active `simulation_scope`: pinned `demo`  
- Safe delivery adapter: no provider calls  
- Cleanup: tagged-only by `simulation_run_id`

---

## 10. Confirmed unsafe paths (pre-Phase 3.1)

1. **Purchase Truth remap (E1)** — observed in Phase 3 execute logs:  
   `store=zid_vip_link_...` after ingest with payload `demo`.  
   Exact chain: `ingest_purchase_truth` → `resolve_purchase_truth_store_slug` → `canonical_store_slug_from_recovery_key` → `resolve_canonical_store_slug("demo")` → linked merchant `zid_store_id`.

2. Without Phase 3.1 guards, architecture **fails** the non-negotiable principle.

---

## 11. Architectural recommendations

1. **Keep the simulation pin** in `resolve_purchase_truth_store_slug` permanently.  
2. **Never register `demo` as an alias** for a production merchant Store in shared environments.  
3. Consider a dedicated simulation store id (`srs_demo`) in a future phase **only if** product agrees — Phase 3.1 keeps writes under `demo` as required.  
4. Extend tagging to every timeline/lifecycle row created as side-effects of purchase reconcile (hardening).  
5. Do not begin Phase 4 until this report is approved.

---

## 12. Risk classification

| Risk | Class | After 3.1 |
|------|-------|-----------|
| Merchant Purchase Truth contamination | Critical | Mitigated (pin + assert + tests) |
| Provider send under sim | Critical | Mitigated (adapter) |
| Dashboard/KL pollution via remapped PT | Critical | Mitigated (no remap) |
| Cleanup collateral damage | High | Mitigated (tagged-only) |
| Alias table pollution of `demo` | Medium | Residual environmental risk; sim no longer depends on alias |

**Residual risk:** Environmental alias pollution of the string `demo` remains a platform hygiene issue; simulation no longer follows that alias during active runs.

---

## 13. Evidence

- Guard module: `services/store_reality_simulator/identity_guard_v1.py`  
- Ingress wiring: `services/store_reality_simulator/ingress_adapter_v1.py`  
- Platform pins: `services/recovery_store_context.py`  
- Tests: `tests/test_store_reality_simulator_phase3_1_identity_isolation_v1.py`  
- Phase 3 purchase assertion updated to require `store_slug == demo`

### Final architectural conclusion

**With Phase 3.1 guards and pins active: simulated durable writes remain under `demo`; Purchase Truth cannot escape to linked merchant/Zid identity during simulation; provider identity is not entered; cleanup is tagged-only.**

Phase 3 product approval remains separate. Phase 4 is not authorized by this report.

---

## STOP

Await review before any further Store Reality Simulator work.
