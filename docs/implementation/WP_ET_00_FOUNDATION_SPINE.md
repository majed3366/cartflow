# WP-ET-00 — Evidence Truth Foundation Spine

**Status:** Implemented — await review / approval  
**Date (UTC):** 2026-07-23  
**Package:** WP-ET-00 (Foundation Spine)  
**Authority:** [`EVIDENCE_TRUTH_ARCHITECTURE_V1.md`](../architecture/EVIDENCE_TRUTH_ARCHITECTURE_V1.md), [`EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`](../architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md)  

**Out of scope (confirmed):** Visitor Truth publish · ProductSignalEvent reads · loaders · Bundle composition · Knowledge · Business Findings · Guidance · Dashboard · Simulator · Reality Validation · BFSV · UI  

---

## 1. Components introduced

| Blueprint ID | Component | Module | Role |
|--------------|-----------|--------|------|
| C-01 | Evidence Contract Kernel | `services/evidence_truth/kernel_v1.py` | Readiness, confidence, freshness, envelope, reject codes, forbidden payload keys |
| C-02 | Evidence Type Registry (technical) | `services/evidence_truth/type_registry_v1.py` | Declared types per family (status=`declared`; not publishing) |
| — | Evidence Family Registry | `services/evidence_truth/families_v1.py` | Seven canonical families + primary questions + owner modules |
| — | Evidence Ownership Registry | `services/evidence_truth/ownership_v1.py` | Exactly one owner per Architecture §4 question |
| — | Contract validation framework | `services/evidence_truth/validation_v1.py` | Envelope validation + readiness transition rules |
| — | Versioning primitives | `services/evidence_truth/versioning_v1.py` | `evidence_id`, monotonic version, integrity hash |
| Stage 0 | Feature-flag skeleton | `services/evidence_truth/flags_v1.py` | All flags default **OFF**; no consumer wiring |
| §9 | Gate declarations A–G | `services/evidence_truth/gates_v1.py` | Metadata only; F/G `execution_authorized=False` |
| — | Package surface | `services/evidence_truth/__init__.py` | Public exports; documents passive library |

**Not introduced in WP-ET-00 (deferred):** C-03 Eligibility engine · C-04 Accounting · C-05 Observability · C-07 Observation Normalizer · family authorities · Bundle Composer · any dual-write/read paths.

---

## 2. Contracts introduced

| Contract area | What landed |
|---------------|-------------|
| Readiness vocabulary | `unknown` / `unavailable` / `insufficient` / `conflicting` / `ready` / `trusted` |
| Confidence grades | PoV-compatible: `confirmed` / `high` / `medium` / `low` / `unknown` / `insufficient` |
| Evidence envelope | `EvidenceEnvelopeV1` matching Architecture §2.0 fields |
| Reject reason codes | Blueprint §7.1 minimum set |
| Forbidden payload keys | Guidance/finding/UI/routing fields rejected on validate |
| Readiness transitions | Architecture §6.1 transition table (Trusted→lower forbidden without supersession) |
| Type registration | One declared scaffold type per family; unknown types fail validation |
| Ownership | Visitor + Traffic → `visitor_truth_authority`; Bundle composition → Composer; freshness/eligibility/confidence → platform |
| Flags | Stable `CARTFLOW_EVIDENCE_*` names; fail-closed unknown flags |

**Merchant Evidence Registry** (`merchant_evidence_registry_v1`) remains presentation-only and was **not** modified.

---

## 3. Dependency graph impact

```text
stdlib only
    ↓
evidence_truth.kernel_v1
    ↓
evidence_truth.families_v1 ──► ownership_v1 ──► type_registry_v1
    ↓                              ↓
validation_v1 ◄────────────────────┘
versioning_v1 (standalone)
flags_v1 / gates_v1 (standalone)
```

- **No cycles** inside `services/evidence_truth/`.
- **No imports** of Business Findings, Knowledge, Bundle loaders, Decisions, Brief, or `main`.
- **No production module** imports `services.evidence_truth` yet (library idle).
- Future WPs may depend **downward** on this package; this package must not depend upward.

---

## 4. Files added

| Path | Purpose |
|------|---------|
| `services/evidence_truth/__init__.py` | Package exports |
| `services/evidence_truth/kernel_v1.py` | C-01 kernel |
| `services/evidence_truth/families_v1.py` | Family registry |
| `services/evidence_truth/ownership_v1.py` | Ownership constitution registry |
| `services/evidence_truth/type_registry_v1.py` | C-02 type registry |
| `services/evidence_truth/validation_v1.py` | Validation framework |
| `services/evidence_truth/versioning_v1.py` | Versioning helpers |
| `services/evidence_truth/flags_v1.py` | Flag skeleton |
| `services/evidence_truth/gates_v1.py` | Gate A–G declarations |
| `tests/test_evidence_truth_foundation_spine_v1.py` | Spine unit tests |
| `docs/implementation/WP_ET_00_FOUNDATION_SPINE.md` | This report |

---

## 5. Files intentionally untouched

| Area | Examples |
|------|----------|
| EvidenceBundle / Findings loaders | `services/business_findings_evidence_v1.py`, `business_findings_engine_v1.py`, `business_findings_families_v1.py` |
| Knowledge | `services/knowledge_layer_v1.py`, `knowledge_metrics_v1.py`, `routes/knowledge.py` |
| Merchant presentation registry | `services/merchant_evidence_registry_v1.py`, `merchant_claim_evidence_v1.py` |
| Purchase / Recovery / Delivery truth | `services/purchase_truth.py`, `recovery_truth_timeline_v1.py`, WhatsApp delivery modules |
| Product data / signals | `services/product_data/*` |
| Widget / WhatsApp / Dashboard / Home | `static/*`, dashboard services, `main.py` |
| Simulator / Reality Validation / BFSV | architecture sim docs and harnesses |
| Guidance / Decision / Routing | decision layer, daily brief, knowledge routing |

---

## 6. Verification results

| Check | Result |
|-------|--------|
| Spine unit tests | **15 passed** (`tests/test_evidence_truth_foundation_spine_v1.py`) |
| Import smoke | Package imports; 7 families; all flags `False` by default |
| Forbidden import DAG test | Pass (AST scan of package) |
| Business Findings engine tests | **Passed** (regression subset) |
| Merchant Evidence Registry tests | **Passed** (regression subset) |
| Production wiring | **None** — no consumer imports |
| Runtime warnings from spine | **None** observed on import/test |
| Merchant-visible behaviour | **Unchanged** (no UI/API path attached) |

---

## 7. Backward compatibility confirmation

| Surface | Confirmation |
|---------|--------------|
| Merchant-visible behaviour | **NO CHANGE** |
| Business Findings | **NO CHANGE** |
| Knowledge | **NO CHANGE** |
| EvidenceBundle | **NO CHANGE** |
| Existing production paths | Do not call Evidence Truth APIs |
| Feature flags | Default OFF; even if set, **no code path reads them yet** |

---

## 8. Known deferred responsibilities (next WP references)

| Next | Blueprint package | Deferred work |
|------|-------------------|---------------|
| **WP-ET-01** | Contract Kernel + Type Registry *expansion* / hardening as publishers prepare | Note: WP-ET-00 already landed C-01/C-02 spine; WP-ET-01 should not re-create kernel — extend types/schemas only when authorities prepare |
| **WP-ET-02** | C-04 Accounting + C-05 Observability stubs; Gate A harness |
| **WP-ET-03** | C-07 Observation Normalizer shadow dual-write |
| **WP-ET-04** | C-03 Eligibility & Freshness Engine |
| **WP-ET-05+** | Family Evidence publishers (Purchase/Communication first) |
| **WP-ET-08** | Visitor Truth Authority (explicitly **not** this package) |
| **WP-ET-09+** | Bundle Composer shadow / consumer switches |
| **WP-ET-13** | Gate F/G — BFSV / Reality Validation (**not authorized**) |

---

## 9. STOP

Foundation spine is in place as a **passive architectural skeleton**.

- No migration started  
- No behaviour changed  
- Do **not** begin WP-ET-01 until this package is reviewed and approved  

---

*End of WP-ET-00 Foundation Spine report.*
