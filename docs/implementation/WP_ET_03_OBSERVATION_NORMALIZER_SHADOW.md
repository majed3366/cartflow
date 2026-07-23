# WP-ET-03 — Observation Normalizer Shadow Dual-Write

**Status:** Implemented — await review / approval  
**Date (UTC):** 2026-07-23  
**Package:** WP-ET-03 (Blueprint §11)  
**Dependencies:** WP-ET-00, WP-ET-01, WP-ET-02 (approved / closed)  
**Authority:** [`EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`](../architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md) C-07, Stage 2, WP-ET-03  

**Rollback point:** Stage 2 — set `CARTFLOW_EVIDENCE_OBSERVATION_DUAL_WRITE` OFF (or unset); Raw paths untouched  

---

## 1. Implemented Blueprint scope

| Blueprint item | Status |
|----------------|--------|
| **Objective** | C-07 dual-write for priority Raw types |
| **Expected output** | Observation store + accounting linkage |
| **Verification** | Gate A partial (Raw≈Observation) |
| **Priority Raw kinds** | cart-event, purchase, communication, product signals, traffic (helper ready) |
| **Unchanged** | All legacy readers; Bundle semantics; Knowledge; Findings; Guidance |
| **Not in scope** | WP-ET-04 Eligibility, family Evidence publishers, Bundle Composer, consumer cutover, BFSV, Reality Validation |

---

## 2. Touched components

| Path | Change |
|------|--------|
| `services/evidence_truth/observation_types_v1.py` | **Added** — raw kinds + observation types |
| `services/evidence_truth/observation_model_v1.py` | **Added** — `CanonicalObservationV1` |
| `services/evidence_truth/observation_store_v1.py` | **Added** — in-process shadow store |
| `services/evidence_truth/observation_normalizer_v1.py` | **Added** — Raw → Observation (fail-closed identity) |
| `services/evidence_truth/observation_shadow_dual_write_v1.py` | **Added** — flagged shadow dual-write + typed helpers |
| `services/evidence_truth/gate_a_partial_harness_v1.py` | **Added** — Gate A partial harness |
| `services/evidence_truth/consumer_eligibility_v1.py` | **Added** — Consumer Eligibility Matrix (governance) |
| `services/evidence_truth/__init__.py` / `flags_v1.py` | **Modified** — exports; flag note |
| `main.py` | **Modified** — cart-event + conversion shadow hooks (flagged) |
| `services/purchase_truth.py` | **Modified** — purchase ingest shadow hook |
| `services/whatsapp_delivery_truth_v1.py` | **Modified** — communication shadow hook |
| `services/product_data/product_data_line_snapshots_hook_v1.py` | **Modified** — product signal shadow hook |
| `tests/test_evidence_truth_wp_et_03_observation_shadow_v1.py` | **Added** |
| WP-ET-01/02 import allowlist tests | **Modified** — authorize listed call sites |

---

## 3. Contracts exercised

| Contract | How |
|----------|-----|
| C-07 normalize | `normalize_raw_to_observation_v1` |
| Fail closed identity | Missing `store_slug` / subject → `identity_mismatch` reject; no store write |
| Idempotent dual-write | Same `raw_ref` → observation not double-counted |
| Accounting linkage | `raw_in` + `observation_out` / `record_reject` on shadow path |
| Gate A partial | `run_gate_a_partial_raw_observation_v1` |
| Flag default OFF | No-op when unset |

---

## 4. New Producers introduced

| Producer | Owner | Output | Enabled? | Feature flag | Production status |
|----------|-------|--------|----------|--------------|-------------------|
| Cart-event observation shadow | Evidence Truth Platform (C-07) via `maybe_shadow_cart_event_observation_v1` | `CanonicalObservationV1` (`cart_state_observed_v1`) | Only when flag ON | `CARTFLOW_EVIDENCE_OBSERVATION_DUAL_WRITE` | Hooked in `main.api_cart_event`; **idle by default** |
| Purchase observation shadow | C-07 via `maybe_shadow_purchase_observation_v1` | `purchase_observed_v1` | Flag ON | same | Hooked in `api_conversion` + `purchase_truth` ingest; **idle by default** |
| Communication observation shadow | C-07 via `maybe_shadow_communication_observation_v1` | `message_lifecycle_observed_v1` | Flag ON | same | Hooked in `persist_delivery_truth`; **idle by default** |
| Product signal observation shadow | C-07 via `maybe_shadow_product_signal_observation_v1` | `product_interest_observed_v1` | Flag ON | same | Hooked in line-snapshots hook; **idle by default** |
| Traffic observation shadow | C-07 via `maybe_shadow_traffic_observation_v1` | `store_visit_observed_v1` | Flag ON | same | **Helper only** — no traffic ingress call site (no Raw traffic owner wired); ready for later attach |

All producers: never raise into callers; never change Raw persistence meaning; never publish Evidence.

---

## 5. Consumer Eligibility Matrix

| Producer | Artifact | Permitted consumers | Prohibited consumers | Activation condition | Justification |
|----------|----------|---------------------|----------------------|----------------------|---------------|
| C-07 Observation Normalizer / shadow dual-write | `CanonicalObservationV1` | Family authorities (**future** WP-ET-05+); Evidence Accounting (counters); Gate A harness; ops admin diagnostics read | Legacy EvidenceBundle loader; Bundle Composer; Knowledge Layer; Business Findings Engine; Guidance / Decision / Home; Merchant Dashboard UI; Merchant Evidence Registry (labels); BFSV; Reality Validation | **Produce:** flag `CARTFLOW_EVIDENCE_OBSERVATION_DUAL_WRITE=ON`. **Consume by authorities:** not activated in WP-ET-03 | Architecture: authorities read observations only; Bundle/Knowledge/Findings must not treat Observations as Findings authority; WP-ET-03 is shadow produce-only |

Code registry: `services/evidence_truth/consumer_eligibility_v1.py` (`CONSUMER_ELIGIBILITY_MATRIX_V1`).

---

## 6. Runtime paths touched

| Path | Behaviour when flag OFF | Behaviour when flag ON |
|------|-------------------------|------------------------|
| Cart-event / conversion / purchase ingest / WA delivery persist / product line snapshots | No-op after try/except | Shadow normalize + store + accounting |
| EvidenceBundle / Knowledge / Findings | Untouched | Untouched |
| Merchant UI | Untouched | Untouched |

---

## 7. Persistence impact

| Class | Impact |
|-------|--------|
| Canonical observation store | **In-process** append-only shadow store (max 5000); Blueprint “store and/or shadow table” |
| DB migrations | **None** in WP-ET-03 |
| Raw tables | **Unchanged** |

---

## 8. Observability / accounting impact

- Shadow path increments C-04 `raw_in` / `observation_out` and audited rejects.  
- Gate A partial harness validates Raw≈Observation accounting linkage.  
- C-05 freshness still stub (no publisher timestamps for Evidence stage).  

---

## 9. Verification

| Suite | Result |
|-------|--------|
| WP-ET-03 tests | **6 passed** |
| WP-ET-00 / 01 / 02 | **33 passed** (15+10+8) |
| Findings + registry regression | **25 passed** |
| Combined verification run | **64 passed** |
| Flag default OFF | Confirmed |
| Gate F/G | Not authorized / not executed |
| Rollback | Flag OFF restores zero observation writes |
---

## 10. Rollback point (Stage 2)

1. Unset / set `CARTFLOW_EVIDENCE_OBSERVATION_DUAL_WRITE=0`.  
2. Optional: `reset_canonical_observation_store_v1()` + `reset_evidence_accounting_ledger_v1()`.  
3. Raw ingress behaviour remains identical.  

---

## 11. Deferred work

| Package | Content |
|---------|---------|
| **WP-ET-04** | C-03 Eligibility & Freshness Engine |
| **WP-ET-05+** | Family Evidence publishers consuming observations |
| Traffic call site | Attach when Visitor/traffic Raw ingress has a durable owner |
| Durable SQL observation table | Optional later; contract already store-backed |

---

## 12. Architectural deviations

**None.**

In-process observation store satisfies Blueprint “new store and/or shadow table” without DB migration. Traffic producer is implemented as a helper without a production call site because no traffic Raw ingress owner exists to hook (documented in producers table) — not a redesign.

---

## 13. STOP

WP-ET-03 complete pending review.

**Do not begin WP-ET-04. Do not resume BFSV. Do not resume Reality Validation.**

---

*End of WP-ET-03 implementation report.*
