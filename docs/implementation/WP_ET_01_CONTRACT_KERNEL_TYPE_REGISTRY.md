# WP-ET-01 — Contract Kernel + Type Registry

**Status:** Implemented — await review / approval  
**Date (UTC):** 2026-07-23  
**Package:** WP-ET-01 (Blueprint §11)  
**Dependencies:** WP-ET-00 Foundation Spine (approved / closed)  
**Authority:** [`EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`](../architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md) §1.1 C-01/C-02, §11 WP-ET-01  

**Rollback point:** Stage 1 (library-only; disable / unused modules — no data migration)

---

## 1. Exact Blueprint scope implemented

| Blueprint item | Implemented |
|----------------|-------------|
| **Objective** | C-01 Evidence Contract Kernel + C-02 Evidence Type Registry |
| **Expected output** | Shared types + registry; unit tests |
| **Verification** | Enum/schema tests |
| **Not in scope** | C-03, C-04, C-05, Observation Normalizer, family publishers, Bundle Composer, consumer cutover, BFSV, Reality Validation |

---

## 2. Components added or modified

| Component | Change |
|-----------|--------|
| `services/evidence_truth/contracts_v1.py` | **Added** — OE/EB/BK/KF/FG rule-ID vocabulary (29 rules) |
| `services/evidence_truth/schema_registry_v1.py` | **Added** — documented envelope + 7 family evidence schema versions |
| `services/evidence_truth/type_registry_v1.py` | **Modified** — public `register_evidence_type_v1`; fail-closed `require_evidence_type_for_publish_v1`; schema registry coupling |
| `services/evidence_truth/kernel_v1.py` | **Modified** — `EvidenceValidationError` relocated here (break import cycle) |
| `services/evidence_truth/validation_v1.py` | **Modified** — re-export error from kernel; OE-2 period helper |
| `services/evidence_truth/__init__.py` | **Modified** — export WP-ET-01 surfaces |
| Pre-existing C-01/C-02 spine modules | Retained (families, ownership, flags, gates, versioning) |

---

## 3. Contracts exercised

| Contract | How exercised (library only) |
|----------|------------------------------|
| C-01 readiness / confidence enums | Schema tests assert vocabulary |
| C-01 envelope schema version | `EVIDENCE_KERNEL_SCHEMA_VERSION` registered in schema registry |
| C-01 OE/EB/BK/KF/FG vocabulary | `CONTRACT_RULE_IDS_V1` (29 IDs) |
| C-02 type catalog | Lookup + list APIs |
| C-02 register-before-publish | `register_evidence_type_v1` + `require_evidence_type_for_publish_v1` |
| C-02 fail-closed unknown type | Publish guard raises `unknown_type` |
| C-02 owner uniqueness | Registration rejects owner mismatch |
| OE-2 period helper | `validate_observed_at_in_period_v1` (unwired) |
| OE-1 / OE-7 | Existing envelope validator (sources required; forbidden guidance keys) |

**Not exercised (deferred):** OE-3/4 publish paths, EB/BK/KF/FG runtime consumers, C-03 stamping.

---

## 4. Runtime paths touched

| Path | Status |
|------|--------|
| Production ingress / Widget / WhatsApp | **Untouched** |
| EvidenceBundle loaders | **Untouched** (remain authoritative) |
| Knowledge / Business Findings / Guidance | **Untouched** |
| Dashboard / Simulator / Reality Validation | **Untouched** |
| Evidence Truth package | Library APIs only — **no production import** |

**Shadow path:** None authorized by WP-ET-01; none added.

---

## 5. Flags and default states

| Flag | Default | Wired? |
|------|---------|--------|
| All `CARTFLOW_EVIDENCE_*` (WP-ET-00 skeleton) | **OFF** | **No** |

No new flags introduced in WP-ET-01 (Blueprint package does not require consumer flags).

Gate F / Gate G: `execution_authorized=False` unchanged. **Not executed.**

---

## 6. Persistence impact

| Class | Impact |
|-------|--------|
| Canonical / derived / projection / rollup / snapshot / cache | **None** |
| Schema / type registries | **Code-versioned only** (Blueprint C-01/C-02 engineering choice) |
| DB migrations | **None** |

---

## 7. Observability added

| Item | Status |
|------|--------|
| C-04 Accounting / C-05 Observability | **Not in WP-ET-01** (deferred to WP-ET-02) |
| Reject reason codes on validation errors | Available on `EvidenceValidationError.reason_code` for future publishers |

---

## 8. Tests and results

| Suite | Result |
|-------|--------|
| `tests/test_evidence_truth_wp_et_01_contract_registry_v1.py` | **10 passed** (enum/schema + registry + publish-guard) |
| `tests/test_evidence_truth_foundation_spine_v1.py` | **15 passed** (WP-ET-00 spine regression) |
| `tests/test_business_findings_engine_v1.py` + `test_merchant_evidence_registry_v1.py` | **25 passed** (Findings + presentation registry) |
| Combined verification run | **50 passed** |
| Production-path import scan | No `services.evidence_truth` outside package |
| Circular / forbidden upward imports | Pass |
---

## 9. Backward compatibility evidence

| Guarantee | Evidence |
|-----------|----------|
| Merchant-visible behaviour | No UI/API/route changes |
| EvidenceBundle output | Loader files untouched |
| Knowledge / Findings / Guidance | Untouched; regression suites green |
| Flags default OFF | Snapshot test with empty environ |
| No Gate F/G | Gate metadata + no harness invocation |
| Existing event meaning | No ingress or truth-module edits |

---

## 10. Rollback point

**Stage 1 / WP-ET-01:** Remove or ignore new library modules (`contracts_v1`, `schema_registry_v1`) and revert type-registry API additions. No DB rollback. No consumer flag to toggle (nothing wired).

---

## 11. Explicitly deferred work packages

| Package | Deferred content |
|---------|------------------|
| **WP-ET-02** | C-04 Accounting + C-05 Observability stubs; Gate A harness |
| **WP-ET-03** | Observation Normalizer shadow dual-write |
| **WP-ET-04** | C-03 Eligibility & Freshness Engine |
| **WP-ET-05+** | Family Evidence publishers |
| **WP-ET-08** | Visitor Truth Authority |
| **WP-ET-09+** | Bundle Composer / consumer switches |
| **WP-ET-13** | Gate F/G execution (**not authorized**) |

---

## 12. Architectural deviations

### DEV-ET-01 — Packaging overlap with authorized WP-ET-00 Foundation Spine

| | |
|--|--|
| **Blueprint wrote** | WP-ET-00 = flag/docs skeleton only; WP-ET-01 = introduce C-01 + C-02 |
| **Authorized WP-ET-00 delivered** | Foundation Spine including initial C-01/C-02 modules |
| **This package** | Completes Blueprint WP-ET-01 **exit criteria** (shared types + registry + enum/schema tests + registration/publish-guard APIs + schema documentation) without re-creating the spine or absorbing WP-ET-02 |
| **Impact** | No ownership move; no alternate truth; no consumer cutover |
| **Improvisation** | **None** — remaining C-01/C-02 contract surface only |

No other deviations. Blueprint could be completed as written for WP-ET-01 objectives given the closed WP-ET-00 spine.

---

## 13. STOP

WP-ET-01 complete pending review.

**Do not begin WP-ET-02** until this package is approved.

---

*End of WP-ET-01 implementation report.*
