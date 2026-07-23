# WP-ET-06 — Recovery + Cart Evidence Publishers

**Status:** Implemented — await architectural approval  
**Date (UTC):** 2026-07-23  
**Package:** WP-ET-06 (Blueprint §11)  
**Dependencies:** WP-ET-05 (approved / closed)  
**Authority:** [`EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`](../architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md) C-11, C-12, Stage 3, WP-ET-06; [`lifecycle_truth_contract.md`](../lifecycle_truth_contract.md)

**Rollback point:** Stage 3 — set `CARTFLOW_EVIDENCE_DUAL_WRITE` OFF (or unset); stop Evidence publishers; legacy cart-event + recovery timeline remain authoritative. Evidence versions retained (Blueprint: keep versions).

---

## 1. Implemented Blueprint scope

| Blueprint item | Status |
|----------------|--------|
| **Objective** | C-12, C-11 dual-write |
| **Expected output** | Recovery/Cart Evidence |
| **Verification** | Lifecycle Truth Contract alignment tests |
| **Unchanged** | Bundle loader, Knowledge, Findings, recovery stop (legacy Purchase Truth), timeline persistence semantics |
| **Not in scope** | WP-ET-07 Behaviour/Product, Bundle Composer, consumer cutover, BFSV, Reality Validation |

---

## 2. Architectural responsibilities completed

| Responsibility | Completed |
|----------------|-----------|
| C-11 Cart Truth Authority Evidence publish from cart observations | Yes |
| C-12 Recovery Truth Authority Evidence publish from recovery/timeline observations | Yes |
| Lifecycle Truth Contract state vocabulary on Recovery Evidence | Yes |
| Must not weaken terminal purchase stop | Yes (`must_not_weaken_purchase_stop`, stop authority = legacy) |
| Sent ≠ delivered / return ≠ replied on Recovery Evidence | Yes |
| Truth Before Consumption through Eligible (not Consumable) | Yes |
| Consumer cutover | **None** (prohibited) |
| Same flag as Stage 3 (`CARTFLOW_EVIDENCE_DUAL_WRITE`) | Yes (default OFF) |

---

## 3. Components added / modified

| Path | Change |
|------|--------|
| `services/evidence_truth/lifecycle_truth_alignment_v1.py` | **Added** — timeline→contract map + invariant checks |
| `services/evidence_truth/cart_evidence_publisher_v1.py` | **Added** — C-11 |
| `services/evidence_truth/recovery_evidence_publisher_v1.py` | **Added** — C-12 |
| `services/evidence_truth/evidence_dual_write_v1.py` | **Modified** — cart + recovery kinds |
| `services/evidence_truth/observation_types_v1.py` | **Modified** — `RAW_KIND_RECOVERY` + observation type |
| `services/evidence_truth/observation_normalizer_v1.py` | **Modified** — recovery subject / payload |
| `services/evidence_truth/observation_shadow_dual_write_v1.py` | **Modified** — recovery observation helper |
| `services/evidence_truth/gate_a_evidence_partial_harness_v1.py` | **Modified** — Stage-3 families |
| `services/evidence_truth/consumer_eligibility_v1.py` | **Modified** — C-11/C-12 rows |
| `services/evidence_truth/__init__.py` / flags / observability | **Modified** |
| `main.py` | **Modified** — cart Evidence publish after observation shadow (flagged) |
| `services/recovery_truth_timeline_v1.py` | **Modified** — recovery Observation + Evidence shadow after successful timeline write |
| `tests/test_evidence_truth_wp_et_06_recovery_cart_publishers_v1.py` | **Added** |
| WP-ET-01/02 import allowlists | **Modified** — authorize timeline hook |

---

## 4. Evidence Truth objects produced

### 4.1 Cart Evidence (`cart_state_v1`)

| Field | Value |
|-------|--------|
| **family** | `cart` |
| **owner** | `cart_truth_authority` |
| **source observations** | `cart_state_observed_v1` |
| **lifecycle state** | `eligible` (never consumable) |
| **eligible consumers** | Accounting; Gate A; ops diagnostics read |
| **prohibited consumers** | Bundle/KL/Findings/Guidance/UI/stop/BFSV/RV |
| **verification** | **PASS** — constitutional metadata; abandon/active signals; no purchase/visitor invention |

### 4.2 Recovery Evidence (`recovery_progression_v1`)

| Field | Value |
|-------|--------|
| **family** | `recovery` |
| **owner** | `recovery_truth_authority` |
| **source observations** | `recovery_progression_observed_v1` |
| **lifecycle state** | `eligible` (never consumable) |
| **eligible consumers** | Accounting; Gate A; ops diagnostics read |
| **prohibited consumers** | Same as Cart + must not drive recovery terminal stop |
| **verification** | **PASS** — Lifecycle Truth Contract alignment; `provider_sent`→`sent`; `webhook_delivered` remains `sent` (delivery_signal only); `customer_reply`→`replied`; never invents `purchased` |

---

## 5. Scalability review

| Decision | Scalability posture |
|----------|---------------------|
| In-process bounded Evidence store (max 5000) | Bounded memory; future SQL archival-compatible versions |
| Append-only versions + supersession | Immutable history; no full historical scans |
| Per-event dual-write at ingress | O(1) per write; no synchronous recomputation of timelines |
| Soft-match limited to purchase/cart (same subject/event) | Bounded recent list (200); no unbounded queries |
| Recovery observations keyed by timeline status | Distinct observations per progression step; no scan of full history |
| No Bundle/KL coupling | No hidden raw-event reads by consumers |

**Avoided:** full historical scans, unbounded queries, synchronous recomputation, consumer coupling to Raw.

---

## 6. Performance impact assessment

| Path | Default (flag OFF) | Flag ON |
|------|--------------------|---------|
| Cart-event | Extra try/except no-op after observation shadow | +1 Observation ensure (often reuse) + 1 Evidence publish (in-process) |
| Timeline write | Extra try/except only after successful insert | Same pattern; no DB Evidence table |
| Bundle / Findings / Home | Untouched | Untouched |

Default production: **no measurable behaviour change**. Flag-ON path is append-only in-process work — not a scan.

---

## 7. Verification

| Check | Result |
|-------|--------|
| Lifecycle Truth Contract alignment | **PASS** (mapping + F2/F3-class invariants + Gate A E9/E10) |
| Purchase stop not weakened | **PASS** (`must_not_weaken_purchase_stop`, legacy stop authority) |
| Gate A Observation→Evidence (Stage 3) | **PASS** |
| Prior Gate A Raw≈Observation | **PASS** |
| Flag default OFF / rollback | **PASS** |
| Consumer cutover | **None** |
| WP-ET-00…06 suite | **63 passed** |

---

## 8. Rollback point (Stage 3)

1. Unset / set `CARTFLOW_EVIDENCE_DUAL_WRITE=0`.  
2. Optional: reset in-process Evidence/Observation ledgers in non-prod.  
3. Legacy cart-event + recovery timeline behaviour identical.

---

## 9. Architectural deviations

**None.**

Recovery observation kind (`RAW_KIND_RECOVERY`) is introduced as the Observation input required by C-12 (Blueprint: publish from observations). It does not redesign Observation Normalizer contracts or change ownership.

---

## 10. Deferred work

| Package | Content |
|---------|---------|
| **WP-ET-07** | Behaviour + Product Evidence |
| **WP-ET-08** | Visitor Truth Authority |
| **WP-ET-09+** | Bundle Composer / consumer cutover |
| Durable SQL Evidence store | Optional later |

---

## 11. STOP

WP-ET-06 complete. **Do not begin WP-ET-07.** Do not resume BFSV or Reality Validation. Await architectural approval.
