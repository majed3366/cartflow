# WP-ET-04 — Eligibility & Freshness Engine + Observation Governance

**Status:** Implemented — await review / approval  
**Date (UTC):** 2026-07-23  
**Package:** WP-ET-04 (Blueprint §11)  
**Dependencies:** WP-ET-00…03 (approved / closed)  
**Authority:** [`EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`](../architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md) C-03, WP-ET-04; Architecture §6  

**Rollback point:** Stage 1/3 — remove/ignore C-03 library; Observations without new metadata cannot be stored (fail closed). No consumer flags changed.

---

## 1. Implemented Blueprint scope

| Blueprint item | Status |
|----------------|--------|
| **Objective** | C-03 Eligibility & Freshness Engine |
| **Expected output** | Readiness stamping library |
| **Verification** | Transition rule tests (Architecture §6) |
| **Not in scope** | WP-ET-05 family Evidence publishers, Bundle Composer, consumer cutover, BFSV, Reality Validation |

**Task addendum (Observation Governance):** Every produced Observation must carry constitutional metadata (owner, family, timestamp authority, version, confidence, readiness, accounting, observability). Enforced in normalizer + store.

---

## 2. Components added / modified

| Path | Change |
|------|--------|
| `services/evidence_truth/eligibility_freshness_v1.py` | **Added** — C-03 stamp engine |
| `services/evidence_truth/observation_model_v1.py` | **Modified** — constitutional fields + validator |
| `services/evidence_truth/observation_types_v1.py` | **Modified** — raw→family map; governance vocab |
| `services/evidence_truth/observation_normalizer_v1.py` | **Modified** — attach governance on produce |
| `services/evidence_truth/observation_store_v1.py` | **Modified** — reject incomplete metadata |
| `services/evidence_truth/observation_shadow_dual_write_v1.py` | **Modified** — `accounting_status=recorded` on success |
| `services/evidence_truth/__init__.py` | **Modified** — exports |
| `tests/test_evidence_truth_wp_et_04_eligibility_freshness_v1.py` | **Added** |

---

## 3. Observations introduced / governed

No new Raw kinds. All existing shadow Observations (cart, purchase, communication, product, traffic helper) now **must** include:

| Field | WP-ET-04 value for new Observations |
|-------|-------------------------------------|
| owner | Family authority module (e.g. `cart_truth_authority`) |
| canonical_family | Mapped from raw kind (cart/purchase/…) |
| timestamp_authority | `wall_clock_utc` (QTC reserved) |
| version | `1` (`OBSERVATION_GOVERNANCE_VERSION`) |
| confidence_state | `unknown` (not Evidence) |
| readiness_state | `unknown` (Architecture: Observation ≠ Evidence Ready) |
| accounting_status | `pending` → `recorded` after successful dual-write |
| observability_status | `ops_visible` |

**Hard rule:** Observation readiness/confidence remain `unknown` until a Family Authority publishes Evidence (WP-ET-05+). Store rejects otherwise.

---

## 4. Ownership verification

| Check | Result |
|-------|--------|
| Raw kind → family map | cart→cart, purchase→purchase, communication→communication, product→product, traffic→visitor |
| Family → owner via ownership registry | Required at normalize time; fail closed if missing |
| Dual ownership | Forbidden — single `owner_for_family` |

---

## 5. Accounting verification

| Check | Result |
|-------|--------|
| Gate A partial after governance | Still passes (synthetic) |
| Successful dual-write | `accounting_status=recorded` |
| Reject path | No Observation stored; reject reason audited (unchanged) |
| Duplicate production truth | Not introduced — shadow only; legacy Raw authoritative |

---

## 6. Observability verification

| Check | Result |
|-------|--------|
| Observation `observability_status` | `ops_visible` when stored |
| C-05 stubs | Unchanged (freshness/latency still stub for Evidence stage) |
| Merchant chrome | No claims (`merchant_visible=false` remains) |

---

## 7. Consumer eligibility confirmation

| Artifact | Consumers |
|----------|-----------|
| `CanonicalObservationV1` | Unchanged matrix — Family authorities **future**; Bundle/KL/Findings **prohibited** |
| C-03 stamp results | Call-in by future Family Authorities + Composer; **not wired** in WP-ET-04 |
| Consumer cutover | **None** |

---

## 8. C-03 contracts exercised

| Rule | Behaviour |
|------|-----------|
| OE-5 readiness enum | Stamp emits only Architecture readiness vocabulary |
| Stale → not Ready | TTL expiry forces `insufficient` (never Ready/Trusted) |
| Channel unavailable | `unavailable` |
| Eligibility fail | `insufficient` |
| Transition rules | Validated via `validate_readiness_transition_v1`; stale supersession uses UNKNOWN basis |
| Never fabricate Ready | `assert_never_fabricate_ready_when_stale_v1` |

---

## 9. Persistence impact

| Class | Impact |
|-------|--------|
| Evidence versions | None published (library only) |
| Observation store | Same in-process store; richer required fields |
| DB migrations | None |

---

## 10. Verification

| Suite | Result |
|-------|--------|
| WP-ET-04 tests | **8 passed** |
| WP-ET-00…03 | **39 passed** (15+10+8+6) |
| Findings + registry | **25 passed** |
| Combined verification run | **72 passed** |
| No consumer activation | Confirmed |
| Flags | Observation dual-write still default OFF; no new consumer flags |
---

## 11. Rollback point

**Stage 1/3:**

1. Stop calling `stamp_evidence_eligibility_v1` (unused in production publishers yet).  
2. Revert observation model fields only with coordinated store/normalizer revert.  
3. No Bundle/Knowledge/Findings rollback required.  

---

## 12. Deferred work

| Package | Content |
|---------|---------|
| **WP-ET-05** | Purchase + Communication Evidence publishers (use C-03 stamps) |
| QTC timestamp authority | Switch Observations to `platform_time_authority_qtc` when Time Authority wired |
| Family-specific eligibility predicates | Register via `register_family_eligibility_predicate_v1` in publisher WPs |

---

## 13. Architectural deviations

**None.**

Observation readiness/confidence forced to `unknown` preserves Architecture §1.3 (Observation does not assert readiness for findings) while satisfying the task’s constitutional metadata requirement. C-03 stamps apply to **Evidence candidates**, not to Observation→Findings shortcuts.

---

## 14. STOP

WP-ET-04 complete pending review.

**Do not begin WP-ET-05. Do not resume BFSV. Do not resume Reality Validation.**

---

*End of WP-ET-04 implementation report.*
