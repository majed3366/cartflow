# WP-ET-08 — Visitor Truth Authority

**Status:** Implemented — await architectural approval  
**Date (UTC):** 2026-07-23  
**Package:** WP-ET-08 (Blueprint §11)  
**Dependencies:** WP-ET-03, WP-ET-04 (prior packages WP-ET-00…07 approved / closed)  
**Authority:** [`EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`](../architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md) C-09, Stage 5, Gate B, WP-ET-08  

**Rollback point:** Stage 5 — set `CARTFLOW_EVIDENCE_DUAL_WRITE` OFF; stop Visitor publisher; consumers unchanged. Evidence versions retained. `CARTFLOW_EVIDENCE_VISITOR_BUNDLE_FIELDS` remains OFF.

---

## 1. Blueprint responsibilities completed

| Blueprint item | Status |
|----------------|--------|
| **Objective** | C-09 dual-write; Gate B |
| **Expected output** | Visitor Evidence; Unavailable when no channel |
| **Verification** | Gate B; proxy-detection tests |
| **Unchanged** | Bundle `visitor_total` / `has_visitor_truth` remain Unavailable/None for consumers (**critical**) |
| **Not in scope** | WP-ET-09 Bundle Composer, consumer cutover, BFSV, Reality Validation |

Closes INV-008 ownership gap at the Evidence Truth layer (publish ownership live; Bundle consumption deferred).

---

## 2. Components implemented

| Path | Change |
|------|--------|
| `services/evidence_truth/visitor_proxy_detection_v1.py` | **Added** — cart/recovery proxy detector + channel availability |
| `services/evidence_truth/visitor_evidence_publisher_v1.py` | **Added** — C-09 publisher |
| `services/evidence_truth/gate_b_visitor_truth_harness_v1.py` | **Added** — Gate B synthetic harness |
| `services/evidence_truth/evidence_publisher_core_v1.py` | **Modified** — `channel_available` / `force_conflict` stamp inputs |
| `services/evidence_truth/evidence_dual_write_v1.py` | **Modified** — traffic → Visitor Evidence; proxy reject |
| `services/evidence_truth/observation_normalizer_v1.py` | **Modified** — visitor channel fields in payload slice |
| `services/evidence_truth/consumer_eligibility_v1.py` | **Modified** — C-09 row |
| `services/evidence_truth/__init__.py` / flags / observability | **Modified** |
| `tests/test_evidence_truth_wp_et_08_visitor_truth_authority_v1.py` | **Added** |

**Production call site:** none — `maybe_publish_visitor_evidence_v1` / traffic observation helpers remain ready for attach when a durable traffic/presence Raw ingress owner exists (same posture as WP-ET-03 traffic helper).

---

## 3. Truth ownership verification

| Check | Result |
|-------|--------|
| Sole owner `visitor_truth_authority` | **PASS** |
| Carts never proxy Visitor Evidence | **PASS** — proxy detector + dual-write reject |
| Abandoned-cart / recovery count fields rejected | **PASS** |
| Non-traffic raw cannot publish Visitor Evidence | **PASS** |
| No purchase/cart invention in Visitor payload | **PASS** |
| Bundle visitor fields unauthorized | **PASS** — `bundle_visitor_fields_authorized=false`; flag OFF |

---

## 4. Lifecycle verification

| Step | Behaviour |
|------|-----------|
| Produced | C-09 publisher from traffic Observations |
| Accounted | C-04 `evidence_out` / audited proxy rejects |
| Observable | ops_visible + observability identity |
| Verified | Envelope + constitutional metadata |
| Eligible | C-03 stamp; Ready when channel+presence; **Unavailable when no channel** |
| Consumable | **Not authorized** |

---

## 5. Accounting verification

| Check | Result |
|-------|--------|
| Gate B harness | **PASS** |
| Proxy rejects audited (`conflict_unresolved`) | **PASS** |
| Prior Gate A Raw≈Observation / Observation→Evidence | **PASS** |
| BFSV Exp 1 class check (not resumed) | **PASS** (`bfsv_resumed=false`) |
| Flag default OFF | **PASS** |

---

## 6. Observability verification

| Signal | Status |
|--------|--------|
| Family authorities label | `stage3_5_dual_write_idle` |
| `visitor_truth_authority` component | `dual_write_idle` |
| Merchant-visible claims | `merchant_visible=false` (unchanged) |
| Bundle visitor fields | Not enabled |

---

## 7. Scalability assessment

| Decision | Posture |
|----------|---------|
| Per-event dual-write when ingress attached | O(1); no historical scans |
| Bounded Evidence store | Cap 5000; versioned append |
| Proxy detection | O(1) field checks; no table scans |
| No merchant-request recomputation | Helper/flag path only |
| Hot/cold ready | Versions immutable; Bundle projection deferred |

---

## 8. Production impact assessment

| Path | Default (flags OFF) |
|------|---------------------|
| Traffic ingress | No call site attached — zero runtime impact |
| Bundle / KL / Findings / UI | Untouched; visitor fields remain Unavailable/None |
| Other Stage-3/4 publishers | Unchanged |

**Production behaviour with defaults: unchanged.**

---

## 9. Rollback point (Stage 5)

1. Unset / set `CARTFLOW_EVIDENCE_DUAL_WRITE=0`.  
2. Keep `CARTFLOW_EVIDENCE_VISITOR_BUNDLE_FIELDS` OFF.  
3. Optional: reset in-process Evidence/Observation stores in non-prod.  
4. Consumers remain on legacy Bundle visitor Unavailable semantics.

---

## 10. Architectural deviations

**None.**

Traffic Raw production call site remains intentionally unattached (no durable traffic ingress owner). Publisher + Gate B are complete; attach is a wiring task when ingress ownership exists — not a redesign and not WP-ET-09.

---

## 11. STOP

WP-ET-08 complete. **Do not begin WP-ET-09.** Do not resume BFSV or Reality Validation. Await architectural approval.
