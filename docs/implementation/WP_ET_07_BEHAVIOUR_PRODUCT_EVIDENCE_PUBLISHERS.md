# WP-ET-07 — Behaviour + Product Evidence Publishers

**Status:** Implemented — await architectural approval  
**Date (UTC):** 2026-07-23  
**Package:** WP-ET-07 (Blueprint §11)  
**Dependencies:** WP-ET-03, WP-ET-04 (and Stage-3 publishers WP-ET-05/06 approved / closed)  
**Authority:** [`EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`](../architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md) C-10, C-15, Stage 4, WP-ET-07  

**Rollback point:** Stage 4 — set `CARTFLOW_EVIDENCE_DUAL_WRITE` OFF (or unset); stop Behaviour/Product Evidence publishers; legacy ProductSignal / hesitation paths remain authoritative. Evidence versions retained.

---

## 1. Implemented Blueprint scope

| Blueprint item | Status |
|----------------|--------|
| **Objective** | C-15, C-10 |
| **Expected output** | Behaviour/Product Evidence; signal accounting |
| **Verification** | BFSV Exp 1 *class* check (persist→evidence); no ATC-as-view |
| **Unchanged** | Bundle still does not cut over `has_product_views`; KL/Findings/Guidance/UI; BFSV/RV **not resumed** |
| **Not in scope** | WP-ET-08 Visitor, Bundle Composer, consumer cutover |

---

## 2. Components and Evidence families introduced

| Path | Change |
|------|--------|
| `services/evidence_truth/product_signal_classification_v1.py` | **Added** — view / ATC / cart_line classification |
| `services/evidence_truth/product_evidence_publisher_v1.py` | **Added** — C-10 |
| `services/evidence_truth/behaviour_evidence_publisher_v1.py` | **Added** — C-15 |
| `services/evidence_truth/bfsv_exp1_class_check_v1.py` | **Added** — synthetic persist→evidence class check |
| `services/evidence_truth/evidence_dual_write_v1.py` | **Modified** — product + behaviour kinds |
| `services/evidence_truth/observation_types_v1.py` | **Modified** — `RAW_KIND_BEHAVIOUR` |
| `services/evidence_truth/observation_normalizer_v1.py` / shadow dual-write | **Modified** — behaviour normalize + helper |
| `services/evidence_truth/consumer_eligibility_v1.py` | **Modified** — C-10/C-15 rows |
| `services/product_data/product_data_line_snapshots_hook_v1.py` | **Modified** — product Evidence publish (flagged) |
| `services/product_data/product_hesitation_hook_v1.py` | **Modified** — behaviour Observation + Evidence (flagged) |
| `tests/test_evidence_truth_wp_et_07_behaviour_product_publishers_v1.py` | **Added** |

### Families published

| Family | Type | Owner |
|--------|------|--------|
| **product** | `product_interest_window_v1` | `product_truth_authority` |
| **behaviour** | `hesitation_reason_v1` | `behaviour_truth_authority` |

---

## 3. Truth ownership verification

| Rule | Result |
|------|--------|
| Product owns views/interest only | **PASS** — no purchase/recovery/visitor invention |
| Behaviour owns hesitation/reason only | **PASS** — no product_view / purchase / recovery invention |
| ATC ≠ view | **PASS** — classifier + payload `atc_is_not_view` / `view_claimed=false` |
| `has_product_views_ready` only for explicit views | **PASS** |
| No confirmed-cause invention | **PASS** — `confirmed_cause_invented=false` |
| widget_shown Unavailable without impressions | **PASS** — `widget_shown_readiness=unavailable` |
| Absence ≠ negative evidence | **PASS** — `absence_as_negative=false` |
| Ownership registries unchanged | **PASS** |

---

## 4. Lifecycle-state verification

| Step | Product / Behaviour |
|------|---------------------|
| Produced | Family publishers |
| Accounted | C-04 `evidence_out` |
| Observable | ops_visible + observability identity |
| Verified | Envelope + constitutional metadata |
| Eligible | C-03 stamp; `lifecycle_state=eligible` |
| Consumable | **Not authorized** (`consumable=false`) |

---

## 5. Accounting and observability results

| Check | Result |
|-------|--------|
| Gate A Raw≈Observation (prior) | **PASS** |
| Gate A Observation→Evidence Stage-3 (prior) | **PASS** |
| BFSV Exp 1 class check (synthetic) | **PASS** — `bfsv_resumed=false` |
| Flag default OFF | **PASS** |
| Silent-loss / invariant machinery | Unchanged (C-04) |
| Observability family authorities label | `stage3_4_dual_write_idle` |

---

## 6. Consumer Eligibility Matrix

| Producer | Artifact | Permitted | Prohibited | Activation |
|----------|----------|-----------|------------|------------|
| C-10 | Product Evidence | Accounting, Gate A, ops diagnostics, synthetic Exp1 class check | Bundle/KL/Findings/Guidance/UI/BFSV harness/RV | Produce: Evidence flag ON; consume: **none** |
| C-15 | Behaviour Evidence | Accounting, Gate A, ops diagnostics | Same (no consumers) | Produce: Evidence flag ON; consume: **none** |

Code: `services/evidence_truth/consumer_eligibility_v1.py`.

---

## 7. Scalability and data-growth review

| Decision | Posture |
|----------|---------|
| Per-ingress dual-write | O(1); no full-history scans |
| Bounded in-process Evidence store | Cap 5000; archival-compatible versions |
| Soft-match limited (product/cart/purchase) | Recent 200 only |
| No merchant-request recomputation | Shadow path only |
| No mutable rewrite of prior Evidence meaning | Superseding versions only |
| BFSV not resumed | No experimental scan harness in production |

---

## 8. Production impact assessment

| Path | Flag OFF (default) | Flag ON |
|------|--------------------|---------|
| Product line snapshots | Observation shadow no-op + Evidence no-op | Ensure Observation + Product Evidence |
| Hesitation mapping hook | Same | Behaviour Observation + Evidence |
| Bundle `has_product_views` | Unchanged (still legacy false until Composer) | Unchanged |
| Findings / Home / UI | Untouched | Untouched |

**Production behaviour with defaults: unchanged.**

---

## 9. Rollback point (Stage 4)

1. Unset / set `CARTFLOW_EVIDENCE_DUAL_WRITE=0`.  
2. Optional: reset in-process Evidence/Observation stores in non-prod.  
3. Legacy ProductSignal / hesitation persistence unchanged.

---

## 10. Architectural deviations

**None.**

BFSV Exp 1 verification is implemented as a **synthetic class check** (`run_bfsv_exp1_class_check_persist_to_evidence_v1`) that proves persist→evidence volume and no ATC-as-view **without** resuming BFSV or Reality Validation (explicitly out of scope / forbidden by task governance).

Behaviour observation kind (`RAW_KIND_BEHAVIOUR`) is the Observation input required by C-15.

---

## 11. STOP

WP-ET-07 complete. **Do not begin WP-ET-08.** Do not resume BFSV or Reality Validation. Await architectural approval.
