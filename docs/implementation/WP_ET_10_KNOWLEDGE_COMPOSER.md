# WP-ET-10 — Knowledge Composer (Shadow Foundation)

**Status:** Implemented — await architectural review  
**Date (UTC):** 2026-07-24  
**Package:** WP-ET-10 (Blueprint §11 Stage 7 / C-18 shadow)  
**Dependencies:** WP-ET-09 Bundle Composer; Evidence Bundle Constitution V1; Evidence Truth Stage Review  
**Authority:** [`EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md`](../architecture/EVIDENCE_TRUTH_IMPLEMENTATION_BLUEPRINT_V1.md) C-18, BK-1…BK-5, Gate D; [`EVIDENCE_BUNDLE_CONSTITUTION_V1.md`](../architecture/EVIDENCE_BUNDLE_CONSTITUTION_V1.md)  

**Rollback point:** Stage 7 — set `CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_SHADOW` OFF; discard shadow Knowledge records; production Knowledge Layer / Home / Findings unchanged.

---

## 1. Scope

### In scope

| Item | Delivered |
|------|-----------|
| C-18 Knowledge Composer shadow foundation | Yes |
| Knowledge Records from Evidence Bundle only | Yes |
| Pattern kinds (presence / ready-family set) — no commercial meaning | Yes |
| BK-1…BK-5 enforcement helpers | Yes |
| Feature flags default OFF; INPUT unwired | Yes |
| Gate D **partial** harness | Yes |
| Consumer Eligibility (Knowledge shadow; Home/Findings prohibited) | Yes |

### Out of scope (explicit)

- Business Findings (WP-ET-11)  
- Guidance / recommendations / ranking / AI  
- Home / dashboard / Daily Brief wiring  
- `CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_INPUT` consumer cutover  
- Production Knowledge Layer migration  
- Full Gate D KL parity soak  

---

## 2. Knowledge model

`KnowledgeRecordV1` (`schema_version=knowledge_record_v1`):

| Field group | Contents |
|-------------|----------|
| Identity | `knowledge_id`, `knowledge_version`, `knowledge_type`, `store_slug`, window, `as_of` |
| Ownership | `composer_owner=knowledge_composer` |
| Traceability | `bundle_refs[]` → Bundle; `evidence_refs[]` → Evidence Truth (via Bundle); `claims[]` with `evidence_ids` (BK-3) |
| Pattern | `pattern_summary` — presence / ready-family aggregation only |
| Governance | `eligibility=shadow_only`, `lifecycle_state=shadow_composed`, **`consumable=False`** |
| Certainty | `readiness` / `confidence` conservatively derived (never upgraded) |

**Allowed knowledge types (WP-ET-10):**

| Type | Meaning |
|------|---------|
| `family_presence_pattern_v1` | Which families are present in Bundle(s) |
| `ready_family_set_pattern_v1` | Which families have `has_ready` in Bundle(s) |

**Forbidden:** finding titles, business meaning, recommendations, ranking, ROI, cause, interventions, UI guidance keys.

---

## 3. Composition rules

| Rule | Enforcement |
|------|-------------|
| BK-1 required families | Knowledge type registry; unknown types rejected |
| BK-2 readiness gate | Conservative min readiness/confidence; never above supporting Evidence |
| BK-3 claim evidence_id | Every claim requires ≥1 Evidence id |
| BK-4 no Evidence write | Composer imports Bundle store only; harness scans import lines |
| BK-5 routing after produce | `routing_authorized_v1() → False` in WP-ET-10 |

**Input law:** Evidence Bundle **only**. Never Raw, Observation, or Evidence Truth stores.

**Fail closed:** no Bundle for store → `missing_sources` / `no_evidence_bundle_for_store`.

---

## 4. Explainability

```text
Knowledge Record
    ↓ bundle_refs
Evidence Bundle
    ↓ evidence_refs
Evidence Truth
    ↓ source_observations / observation_refs
Observation
    ↓ raw_ref
Raw Event
```

- No orphan Knowledge (requires Bundle + Evidence refs + claims).  
- Reconstructable from selected Bundle versions for `(store, type, as_of)`.  
- Pattern summary carries family presence facts only — not merchant “why” speech.

---

## 5. Ownership

| Layer | Owner |
|-------|-------|
| Family facts | Evidence Truth family authorities |
| Composition of facts | Evidence Bundle Composer |
| Pattern Knowledge | `knowledge_composer` (this package) |
| Commercial meaning | Business Findings — **not** WP-ET-10 |
| Merchant speech | Guidance / Presentation — **not** WP-ET-10 |

Knowledge owns pattern records only. It does not re-own Evidence or Bundle facts.

---

## 6. Constitutional compliance

| Source | Status |
|--------|--------|
| Bundle Constitution EB-C1…EB-C12 (Bundle remains composition-only; Knowledge interprets patterns without inventing truth) | Preserved |
| Evidence Truth EC-1…EC-10 (sole Evidence producer; no UI direct consume; explainability chain) | Preserved |
| Knowledge consumes Bundle only | Enforced |
| No Findings / Guidance / Home | Enforced |
| Truth Before Intelligence | Enforced — no fabricated evidence; fail closed |

---

## 7. Production safety

| Check | Result |
|-------|--------|
| `CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_SHADOW` default OFF | Pass |
| `CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_INPUT` default OFF + unwired | Pass (`knowledge_consume_wired_v1() → False`) |
| Findings / Home not connected | Pass |
| No production ingress hooks | Pass |
| Rollback | Unset SHADOW flag; shadow store disposable |
| Prior Gate C | Still green |

**Components:**

| Path | Change |
|------|--------|
| `knowledge_model_v1.py` | **Added** |
| `knowledge_composition_rules_v1.py` | **Added** |
| `knowledge_composer_v1.py` | **Added** |
| `knowledge_store_v1.py` | **Added** |
| `knowledge_shadow_compose_v1.py` | **Added** |
| `gate_d_partial_harness_v1.py` | **Added** |
| `flags_v1.py` | **Modified** — `CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_SHADOW` |
| `accounting_v1.py` | **Modified** — `knowledge_out` stage + invariant |
| `consumer_eligibility_v1.py` | **Modified** — Bundle→Knowledge shadow; Knowledge producer row |
| `observability_v1.py` / `__init__.py` | **Modified** |
| `tests/test_evidence_truth_wp_et_10_knowledge_composer_v1.py` | **Added** |

---

## 8. Tests

| Suite | Result |
|-------|--------|
| `tests/test_evidence_truth_wp_et_10_knowledge_composer_v1.py` | Flags, fail-closed, Bundle→Knowledge trace, eligibility, BK-4, Gate D, prior Gate C |
| Full Evidence Truth suite WP-ET-00…10 | **99 passed** |

---

## 9. Remaining gaps

| Gap | Class | Notes |
|-----|-------|-------|
| Full Gate D production KL consumer parity | Major (soak) | Partial harness only |
| Durable Knowledge / Bundle / Evidence stores | Major (soak) | Still process-local |
| Richer pattern library | Minor | Only presence / ready-set in V1 shadow |
| INPUT cutover to existing `knowledge_layer` | Intentionally deferred | Flag unwired |
| Findings connection | Intentionally deferred | WP-ET-11 |
| Home / Brief routing (BK-5) | Intentionally deferred | `routing_authorized=false` |

---

## 10. Stop point

**WP-ET-10 complete as Knowledge Composer shadow foundation.**

Do **not** begin WP-ET-11.  
Do **not** connect Home.  
Do **not** enable Knowledge consumers (`CARTFLOW_EVIDENCE_KNOWLEDGE_COMPOSER_INPUT` remains OFF and unwired).  
Do **not** enable Findings.

**STOP — await architectural review.**
