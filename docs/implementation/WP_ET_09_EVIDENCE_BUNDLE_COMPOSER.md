# WP-ET-09 — Evidence Bundle Composer (Shadow Foundation)

**Status:** Implemented — await architectural review  
**Date (UTC):** 2026-07-23  
**Package:** WP-ET-09 (Blueprint §11 Stage 6 / C-16)  
**Dependencies:** WP-ET-00…08 closed; Evidence Truth Stage Review (`READY_WITH_MINOR_GAPS`); Architectural Exit Criteria EC-1…EC-10  
**Authority:** [`EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`](../architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md) C-16, EB-1…EB-8, Gate C  

**Rollback point:** Stage 6 — set `CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW` OFF; discard shadow Bundle projections; production consumers unchanged (still legacy).  

---

## 1. Scope

### In scope

| Item | Delivered |
|------|-----------|
| C-16 Evidence Bundle Composer shadow foundation | Yes |
| Bundle DTO preserving identity, provenance, ownership, confidence, readiness, traceability | Yes |
| Composition from Evidence Truth only (no Raw authority) | Yes |
| Feature flags default OFF | Yes |
| Gate C **partial** harness (composition invariants + visitor honesty) | Yes |
| Consumer Eligibility update (Composer shadow may read Evidence; KL/Findings prohibited) | Yes |

### Out of scope (explicit)

- Knowledge (WP-ET-10)  
- Business Findings (WP-ET-11)  
- Guidance / AI / merchant explanations / dashboard changes  
- Reality Validation / BFSV  
- Production cutover / `CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_CONSUME` wiring  
- Full Gate C legacy field-by-field parity soak  
- Visitor Bundle field enablement (`CARTFLOW_EVIDENCE_VISITOR_BUNDLE_FIELDS`)  

---

## 2. Components introduced

| Path | Change |
|------|--------|
| `services/evidence_truth/bundle_model_v1.py` | **Added** — `EvidenceBundleRecordV1`, family slices, evidence refs, constitutional validator |
| `services/evidence_truth/bundle_composition_rules_v1.py` | **Added** — EB-1…EB-8 helpers (projection, no zero-fill, has_* flags, demo provenance, EB-7 import scan) |
| `services/evidence_truth/bundle_composer_v1.py` | **Added** — C-16 compose from Evidence Truth store |
| `services/evidence_truth/bundle_store_v1.py` | **Added** — in-process shadow Bundle projection store (max 2000) |
| `services/evidence_truth/bundle_shadow_compose_v1.py` | **Added** — flag-gated `maybe_compose_evidence_bundle_v1` |
| `services/evidence_truth/gate_c_partial_harness_v1.py` | **Added** — Gate C partial synthetic harness |
| `services/evidence_truth/consumer_eligibility_v1.py` | **Modified** — Composer shadow permitted reader; Bundle producer row; KL/Findings still prohibited |
| `services/evidence_truth/flags_v1.py` | **Modified** — comments: SHADOW wired; CONSUME unwired |
| `services/evidence_truth/observability_v1.py` | **Modified** — `bundle_composer: shadow_idle` |
| `services/evidence_truth/__init__.py` | **Modified** — exports WP-ET-09 surface |
| `tests/test_evidence_truth_wp_et_09_bundle_composer_v1.py` | **Added** |

**Production call sites:** none. Composer is library + harness only. No `main.py` / Knowledge / Findings wiring.

---

## 3. Bundle model

`EvidenceBundleRecordV1` (`schema_version=evidence_bundle_v1`):

| Field group | Contents |
|-------------|----------|
| Identity | `bundle_id`, `bundle_version`, `store_slug`, `window_start` / `window_end`, `as_of` |
| Ownership | `composer_owner=evidence_bundle_composer` |
| Family slices | One slice per registered V1 family (`present`, `has_ready`, readiness, confidence, owner, evidence_ref, projected_facts) |
| Traceability | `evidence_refs[]` → evidence_id/version + source_observations / observation_refs |
| Visitor honesty | `has_visitor_truth`, `visitor_total` (never zero-fill), `visitor_bundle_fields_authorized` |
| Governance | `eligibility=shadow_only`, `lifecycle_state=shadow_composed`, **`consumable=False`** |
| Provenance | Explicit `provenance` (demo/synthetic cannot claim Trusted — EB-8) |

Missing family Evidence → slice with `present=False`, `readiness=unavailable` (EB-2). No business conclusions, recommendations, or finding titles.

---

## 4. Composition rules

| Rule | Enforcement |
|------|-------------|
| EB-1 projection only | Facts copied from Evidence payload minus forbidden guidance keys |
| EB-2 no zero-fill | Missing families → Unavailable; `visitor_total` stays `None` without truth |
| EB-3 has_* flags | `has_ready` / `has_visitor_truth` only when readiness ≥ Ready **and** visitor fields authorized |
| EB-4 evidence_refs | Bundle rejected if no refs; each ref requires observation trace |
| EB-5 schema_version | Fixed `evidence_bundle_v1`; validator fail-closed |
| EB-6 cache invalidation | Version bump when store latest content identity changes; store eviction bounded |
| EB-7 no Raw authority | Composer imports Evidence Truth only; harness scans import lines |
| EB-8 demo provenance | Demo/synthetic must not retain Trusted at Bundle layer |

**Fail closed:** compose with no Evidence for store → `missing_sources` / `no_evidence_truth_for_store`.

**Visitor:** even when Visitor Evidence exists and is Ready, Bundle root `has_visitor_truth` remains **false** and `visitor_total` remains **None** while `CARTFLOW_EVIDENCE_VISITOR_BUNDLE_FIELDS` is OFF.

---

## 5. Traceability guarantees

```text
Evidence Bundle
    ↓ evidence_refs[]
Evidence Truth (evidence_id + version)
    ↓ source_observations / observation_refs
Observation
    ↓ raw_ref (on Observation — not read by Composer)
Raw Event
```

- No Bundle without ≥1 Evidence ref.  
- No present family slice without observation trace on its ref.  
- Composer never reads Raw stores.  
- Reconstructability: Bundle is a projection of selected Evidence Truth versions for `(store, window, as_of)`.

---

## 6. Constitutional compliance

| Exit criterion / principle | Status |
|----------------------------|--------|
| EC-1 Sole Evidence producer | Preserved — Composer does not mint Evidence |
| EC-2 Observation origin | Preserved — only Evidence with observation traces compose |
| EC-3 No direct merchant-UI Evidence/Bundle consume | Preserved — no UI wiring; eligibility prohibits UI |
| EC-4 Bundle sole composition layer | Established — C-16 is the composition owner |
| EC-5 Ownership Constitution | Preserved — family owners carried on slices/refs |
| EC-6 Visitor never from cart/recovery/product | Preserved — visitor fields unauthorized; no proxy |
| EC-7 Eligible ≠ Consumable | Preserved — Bundle `consumable=False`; CONSUME unwired |
| EC-8 Explainability chain | Preserved — refs required |
| EC-9 Competing explanations | Preserved — no hypothesis collapse / no findings text |
| EC-10 Truth Before Intelligence | Preserved — no fabricated facts; fail closed without Evidence |

---

## 7. Production safety

| Check | Result |
|-------|--------|
| `CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_SHADOW` default OFF | Pass |
| `CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_CONSUME` default OFF + unwired | Pass (`bundle_consume_wired_v1() → False`) |
| Knowledge / Findings not connected | Pass |
| No production ingress hooks | Pass |
| Rollback | Unset SHADOW flag; shadow store disposable |
| Prior Gate A / Gate B | Still green |

---

## 8. Test summary

| Suite | Result |
|-------|--------|
| `tests/test_evidence_truth_wp_et_09_bundle_composer_v1.py` | Added — flags, fail-closed, compose+trace, eligibility, EB-7, Gate C partial, prior gates |
| Full Evidence Truth suite WP-ET-00…09 | **89 passed** |

Gate C partial checks: shadow/consume/visitor flags OFF; seed Evidence; compose; never more certain; observation trace; persist; EB-7 import scan; visitor dual-read honesty; fail-closed without Evidence.

---

## 9. Remaining gaps

| Gap | Class | Notes |
|-----|-------|-------|
| Full Gate C legacy Bundle field-by-field parity | Major (for soak) | Partial harness only; C-17 dual-read baseline stub for visitor honesty |
| Durable Evidence / Bundle stores | Major (soak) | Still process-local |
| Traffic attach for Visitor production volume | Major (Visitor claims) | Unchanged from WP-ET-08 |
| CONSUME / KL / Findings wiring | Intentionally deferred | WP-ET-10/11 |
| Visitor Bundle fields | Intentionally deferred | Flag OFF |
| Production dual-read in Findings path | Intentionally deferred | No consumer activation |

---

## 10. Stop point

**WP-ET-09 complete as shadow foundation.**

Do **not** begin WP-ET-10.  
Do **not** connect Bundle to Knowledge.  
Do **not** enable Bundle consumers (`CARTFLOW_EVIDENCE_BUNDLE_COMPOSER_CONSUME` remains OFF and unwired).

**STOP — await architectural review.**
