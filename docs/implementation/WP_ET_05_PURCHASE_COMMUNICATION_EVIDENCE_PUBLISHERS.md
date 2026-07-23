# WP-ET-05 — Purchase + Communication Evidence Publishers

**Status:** Implemented — await architectural approval  
**Date (UTC):** 2026-07-23  
**Package:** WP-ET-05 (Blueprint §11)  
**Dependencies:** WP-ET-03, WP-ET-04 (approved / closed) + Implementation Checkpoint V1  
**Authority:** [`EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`](../architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md) C-13, C-14, Stage 3, WP-ET-05  

**Rollback point:** Stage 3 — set `CARTFLOW_EVIDENCE_DUAL_WRITE` OFF (or unset); stop Evidence publishers; existing Purchase Truth / WhatsApp delivery truth remain authoritative. Evidence versions retained in shadow store (Blueprint: keep versions).

---

## 1. Implemented Blueprint scope

| Blueprint item | Status |
|----------------|--------|
| **Objective** | C-13, C-14 dual-write |
| **Expected output** | Evidence versions; terminal parity |
| **Verification** | Purchase stop + delivery≠sent tests |
| **Unchanged** | Bundle loader, Knowledge, Findings, recovery stop (legacy Purchase Truth) |
| **Not in scope** | WP-ET-06 Recovery/Cart publishers, Bundle Composer, consumer cutover, BFSV, Reality Validation |

---

## 2. Components added / modified

| Path | Change |
|------|--------|
| `services/evidence_truth/evidence_governance_v1.py` | **Added** — lifecycle + accounting/observability vocab |
| `services/evidence_truth/evidence_model_v1.py` | **Added** — `EvidenceTruthRecordV1` + constitutional validator |
| `services/evidence_truth/evidence_store_v1.py` | **Added** — in-process immutable Evidence version store |
| `services/evidence_truth/evidence_publisher_core_v1.py` | **Added** — Observation→Evidence publish + C-03 stamp |
| `services/evidence_truth/purchase_evidence_publisher_v1.py` | **Added** — C-13 Purchase Evidence wrap |
| `services/evidence_truth/communication_evidence_publisher_v1.py` | **Added** — C-14 Communication Evidence wrap |
| `services/evidence_truth/evidence_dual_write_v1.py` | **Added** — flagged dual-write orchestration |
| `services/evidence_truth/gate_a_evidence_partial_harness_v1.py` | **Added** — Gate A partial Observation→Evidence |
| `services/evidence_truth/consumer_eligibility_v1.py` | **Modified** — Evidence rows; consumers prohibited |
| `services/evidence_truth/flags_v1.py` | **Modified** — note WP-ET-05 wires `CARTFLOW_EVIDENCE_DUAL_WRITE` |
| `services/evidence_truth/observability_v1.py` | **Modified** — authority status labels |
| `services/evidence_truth/__init__.py` | **Modified** — exports |
| `services/purchase_truth.py` | **Modified** — flagged Evidence publish after observation shadow |
| `services/whatsapp_delivery_truth_v1.py` | **Modified** — flagged Evidence publish after observation shadow |
| `tests/test_evidence_truth_wp_et_05_purchase_communication_publishers_v1.py` | **Added** |

---

## 3. Truth Before Consumption

Every produced Evidence Truth completes:

| Step | How |
|------|-----|
| Produced | Family publisher builds envelope + record |
| Accounted | C-04 `evidence_out` (+ observation ensure path) |
| Observable | `observability_status=ops_visible` + observability identity |
| Verified | Envelope + constitutional metadata validation |
| Eligible | C-03 stamp + `lifecycle_state=eligible` |
| Consumable | **Not authorized** — `consumable=False`; store rejects Consumable |

---

## 4. Evidence Truth Objects Produced

### 4.1 Purchase Evidence (`purchase_confirmed_v1`)

| Field | Value |
|-------|--------|
| **family** | `purchase` |
| **owner** | `purchase_truth_authority` |
| **source observations** | `purchase_observed_v1` (`CanonicalObservationV1.observation_id`) |
| **current lifecycle state** | `eligible` (never `consumable`) |
| **eligible consumers** | Accounting; Gate A harness; ops admin diagnostics **read** only |
| **prohibited consumers** | EvidenceBundle (legacy + Composer); Knowledge; Business Findings; Guidance; Dashboard/Merchant UI; recovery terminal stop; BFSV; Reality Validation |
| **verification status** | **PASS** — constitutional metadata enforced; readiness Ready + confidence Confirmed when eligible; terminal meaning documented; production stop remains `purchase_truth_legacy` |

### 4.2 Communication Evidence (`message_lifecycle_v1`)

| Field | Value |
|-------|--------|
| **family** | `communication` |
| **owner** | `communication_truth_authority` |
| **source observations** | `message_lifecycle_observed_v1` |
| **current lifecycle state** | `eligible` (never `consumable`) |
| **eligible consumers** | Accounting; Gate A harness; ops admin diagnostics **read** only |
| **prohibited consumers** | Same as Purchase (Bundle/KL/Findings/Guidance/UI/BFSV/RV) |
| **verification status** | **PASS** — Sent ≠ Delivered: `status=sent` → `sent_claimed=true`, `delivered_claimed=false`; delivery requires delivered/read-class status |

---

## 5. Constitutional metadata (every Evidence object)

Required and enforced by `validate_evidence_constitutional_metadata_v1`:

| Field | Source |
|-------|--------|
| owner | Family ownership registry |
| canonical family | Evidence family |
| source observations | Observation refs |
| timestamp authority | `wall_clock_utc` |
| confidence | C-03 stamp (+ Confirmed when purchase Ready) |
| readiness | C-03 stamp |
| accounting identity | `acct:ev:{evidence_id}:v{n}` |
| observability identity | `ops:ev:{evidence_id}:v{n}` |
| eligibility | `shadow_dual_write_only` |
| version | `evidence_version` (monotonic) |

---

## 6. Feature flag / production safety

| Flag | Default | Behaviour |
|------|---------|-----------|
| `CARTFLOW_EVIDENCE_DUAL_WRITE` | **OFF** | No-op when unset |
| `CARTFLOW_EVIDENCE_OBSERVATION_DUAL_WRITE` | OFF | Unchanged |

When Evidence flag ON: publisher ensures Observation (reuse if present; else force shadow write), then publishes Evidence. Call sites remain try/except no-raise. Legacy Purchase Truth / delivery truth persistence unchanged.

**Production behaviour with defaults:** unchanged (both dual-write flags OFF).

---

## 7. Consumer Eligibility Matrix (WP-ET-05)

| Producer | Artifact | Permitted | Prohibited | Activation |
|----------|----------|-----------|------------|------------|
| C-13 | `EvidenceTruthRecordV1 (purchase_confirmed_v1)` | Accounting, Gate A, ops diagnostics | Bundle/KL/Findings/Guidance/UI/stop/BFSV/RV | Produce: Evidence flag ON; consume: **none** |
| C-14 | `EvidenceTruthRecordV1 (message_lifecycle_v1)` | Accounting, Gate A, ops diagnostics | Same | Produce: Evidence flag ON; consume: **none** |

Code: `services/evidence_truth/consumer_eligibility_v1.py`.

---

## 8. Contracts / verification

| Check | Result |
|-------|--------|
| Purchase terminal parity | Evidence payload `terminal_for_recovery=true` + `production_stop_authority=purchase_truth_legacy`; recovery stop **not** wired to Evidence |
| delivery ≠ sent | Classifier + payload assertions; Gate A check E5 |
| Gate A partial Observation→Evidence | `run_gate_a_partial_observation_evidence_v1` **PASS** |
| Prior Gate A Raw≈Observation | Still **PASS** |
| Flag default OFF | Confirmed |
| Rollback | Flag OFF → no new Evidence writes; versions retained |
| Consumer cutover | **None** |
| WP-ET-00…05 unit suite | **55 passed** |

---

## 9. Persistence impact

| Class | Impact |
|-------|--------|
| Evidence versions | In-process shadow store (max 5000 versions) |
| Observation store | May be written by Evidence path when observation missing |
| DB migrations | **None** |
| Legacy purchase / WA tables | **Unchanged** |

---

## 10. Architectural deviations

**None.**

Evidence dual-write may materialize Observations when the observation flag is OFF (documented) so C-13/C-14 always publish from Observations per Architecture. Soft-match reuse of prior observations is purchase-only (communication status changes must create distinct observations).

---

## 11. Deferred work

| Package | Content |
|---------|---------|
| **WP-ET-06** | Recovery + Cart Evidence publishers |
| **WP-ET-07+** | Behaviour / Product / Visitor |
| **WP-ET-09+** | Bundle Composer / consumer cutover |
| Durable SQL Evidence store | Optional later |

---

## 12. STOP

WP-ET-05 complete. **Do not begin WP-ET-06.** Do not resume BFSV or Reality Validation. Await architectural approval.
