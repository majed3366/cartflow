# Commerce Intelligence Synthesis Foundation V1 — Production Closure Evidence

**Status:** PRODUCTION CLOSED + CLOSURE VALIDATION ADDENDUM  
**Date (UTC):** 2026-07-21 (foundation) / 2026-07-22 (validation addendum)  
**Runtime commit:** `b98bd7d` (PR #38 → `main`) + closure-validation patch (see §12)  
**Environment:** https://smartreplyai.net  
**Store:** `demo` only  

---

## 1. Architectural inventory & duplication review

| Existing layer | Relationship |
|----------------|--------------|
| Product Performance stack (Signals→…→Presentation) | **PRODUCTION CLOSED** — inputs reused via Knowledge + governed mappings; **not replaced** |
| Business Findings / Reasoning | Parallel research path — **not duplicated** as CIS SoT |
| Home Commercial Intelligence | Downstream consumer later — **not owned / not modified** |
| Commerce Signals V1 | Optional governed source adapter (`force` read) |
| Commerce Brain docs | Draft only — not runtime SoT |

**Decision:** NEW synthesis sublayer (`cisyn_v1`), not an extension or replacement of KF/CGF/MPF.

---

## 2. Final architectural position

```text
Canonical Domain Truth / Product Performance foundations
        ↓
Commerce Intelligence Synthesis  ← CLOSED HERE
        ↓
(Knowledge / Guidance / Presentation — future consumers; unchanged in V1)
```

---

## 3. Deployment

| Item | Value |
|------|--------|
| PR | https://github.com/majed3366/cartflow/pull/38 |
| Merge commit | `b98bd7da4d96d16976c882e6879b449b9b49a4b1` |
| Migration | Alembic `e4f5a6b7c8d9` (table also ensured via `create_all`) |
| Feature flag | `CARTFLOW_COMMERCE_INTELLIGENCE_SYNTHESIS_V1` (enabled / default on) |
| Registry version | `cisyn_v1` |
| Source contract registry | `cisrc_v1` |
| Output contract | `commerce_intelligence_synthesis_v1` |

---

## 4. Production probe

`GET /dev/commerce-intelligence-synthesis?store=demo&time_window_key=d7`

| Field | Result |
|-------|--------|
| `ok` | `true` |
| `deterministic` / `rerun_determinism` | `true` |
| `provider_independent` | `true` |
| `accounting_ok` | `true` |
| `unaccounted_count` | `0` |
| `candidate_count` | `14` |
| `qualified_count` | `5` |
| `observing_count` | `5` |
| `insufficient_evidence_count` | `1` |
| `conflicting_evidence_count` | `0` |
| `blocked_count` | `3` |
| `failed_count` | `0` |
| `active_rule_count` | `10` |
| `upserted` / `materialized_row_count` | `14` / `14` |
| `current_record_uniqueness` | `true` |
| `consumes_canonical_sources_only` | `true` |
| `no_guidance_generation` | `true` |
| `no_presentation_generation` | `true` |
| `no_page_integration` | `true` |

Verify script:

```bash
python scripts/_verify_commerce_intelligence_synthesis_v1.py --base https://smartreplyai.net --store demo
```

Exit code `0` (`ok: true`).

---

## 5. Candidate accounting (Demo)

| Rule | Count |
|------|------:|
| product_interest_without_purchase | 3 |
| high_traffic_weak_conversion | 1 |
| whatsapp_return_without_purchase | 1 |
| shipping_hesitation_recovery_outcome | 1 |
| repeated_interest_pattern | 3 |
| discount_message_weakness | 1 |
| vip_followup_outcome | 1 |
| insufficient_evidence_store | 1 |
| conflicting_evidence_store | 1 |
| recovery_influence_boundary | 1 |
| **Total** | **14** |

Expected = qualified + observing + insufficient + conflicting + blocked + expired + failed → **14 = 5+5+1+0+3+0+0**.

---

## 6. Example syntheses (Demo)

### Product interest without purchase
- State: `qualified`
- Subject: `product` / `c|demo_pmf_probe` (and peers)
- Known: cart interest trend observed; purchase mappings = 0
- Unknown: why completion is weak
- Prohibited: root_cause_known / price_is_the_cause

### High traffic, weak conversion
- State: `qualified`
- Known: `engagement_trend_observations=3`, `purchase_mappings=0`
- Prohibited: root_cause_known / funnel_stage_diagnosed

### Recovery influence boundary
- State: `qualified`
- Known: `purchase_confirmed_signals=4`; influence class counts preserved (not collapsed into recovered-revenue)
- Prohibited: all_purchases_are_recovered_revenue

### Insufficient / blocked (truthful abstention)
- `shipping_hesitation_recovery_outcome` → `blocked` (missing `product_hesitation` in window)
- `discount_message_weakness` → `blocked` (missing required sources / message strategy contract)
- `conflicting_evidence_store` → `insufficient_evidence` when no conflict flags (explicit, not silent)

---

## 7. Guarantees verified

- Deterministic rerun (same `as_of`)
- Source contribution accounting present on samples
- Temporal window exposed (`d7`)
- Failure isolation (rule failures do not erase other candidates — covered in unit tests)
- No silent candidate loss (`unaccounted_count=0`)
- Demo allowlist (non-demo → `store_not_allowlisted` / 403)
- No merchant UI / Guidance / Presentation / AI changes
- Purchase Truth remains authoritative via commerce_signals purchase_confirmed; attribution classes not collapsed

---

## 8. Tests

`pytest tests/test_commerce_intelligence_synthesis_v1.py` — **10 passed** (foundation)  
`pytest tests/test_commerce_intelligence_synthesis_closure_v1.py` — **18 passed** (validation addendum)  
**Combined: 28 passed**

---

## 9. Forbidden-scope confirmation

Not implemented / not changed:
- Surface Composition, Home UI, Decision Workspace UI, Carts/Communication/Settings UI
- New Commercial Guidance rules / Guidance Routing / Merchant Presentation
- Automatic actions, messaging, AI insights
- Parallel Knowledge system / parallel Commerce Intelligence SoT

---

# Closure Validation Addendum (2026-07-22)

## 1. Test Coverage Matrix

| test file | test name | scenario | input contracts | expected output | architectural boundary protected | failure detected if broken | production evidence equivalent | status |
|-----------|-----------|----------|-----------------|-----------------|----------------------------------|----------------------------|--------------------------------|--------|
| `test_commerce_intelligence_synthesis_v1.py` | `test_registries_exist_and_valid` | registries load | cisrc/cisyn code registries | valid=true, ≥8 rules | rule + source contract registries exist | invalid/empty registry | probe `rule_registry` / `source_registry` | PASS |
| same | `test_deterministic_rerun` | same as_of twice | mocked sources | identical fingerprints | deterministic synthesis + idempotent rerun | fingerprint drift | probe `deterministic` / `rerun_determinism` | PASS |
| same | `test_full_candidate_accounting_no_silent_loss` | full refresh | knowledge-only mock | expected=actual; WA blocked/insufficient | candidate accounting; no silent loss; blocked/insufficient explicit | unaccounted or missing rule | probe `unaccounted_count=0` | PASS |
| same | `test_known_unknown_prohibited_and_no_causal_inflation` | product interest | knowledge trends | known/unknown/prohibited; no “caused” | claim boundaries; no causal inflation | causal wording present | probe sample known/unknown/prohibited | PASS |
| same | `test_materialize_idempotent_and_current_unique` | double materialize | same inputs | unique current keys | no duplicate current; current vs historical | duplicate `is_current` | probe `current_record_uniqueness` | PASS |
| same | `test_flag_off_skips_writes` | flag=0 | any | skipped_disabled | feature-flag isolation | writes while off | flag env on probe | PASS |
| same | `test_rule_scoped_and_subject_scoped_refresh` | scoped refresh | rule/subject filters | only scoped candidates | rule/subject-scoped refresh | wrong subjects | N/A (dev API) | PASS |
| same | `test_failed_differs_from_insufficient` | injected exception | boom evaluator | failed ≠ blocked; others continue | rule failure isolation; failed≠blocked | cascade fail / misclass | probe `failed_count` | PASS |
| same | `test_no_main_py_business_logic_growth` | inspect main route | — | probe import only | main.py wiring-only | logic in main | route source review | PASS |
| same | `test_consumes_canonical_adapters_only` | inspect sources | — | knowledge/mappings/signals only | governed-contract-only; no provider reads | provider strings in adapter | probe `source_adapters` | PASS |
| `test_commerce_intelligence_synthesis_closure_v1.py` | `test_missing_required_source_blocked_reason` | shipping w/o hesitation | knowledge only | blocked + `required_source_data_unavailable` | blocked state + reason codes | vague/missing reason | probe `blocked_candidates[]` | PASS |
| same | `test_temporal_alignment_blocked_reason` | discount on d7 | all domains | `temporal_alignment_failed` | temporal alignment | wrong window allowed | probe blocked temporal status | PASS |
| same | `test_unsupported_source_version_blocked_reason` | classifier unit | unsupported version | defect classification | unsupported contract version | silent accept | classification registry | PASS |
| same | `test_unresolved_subject_identity_blocked_reason` | classifier unit | unresolved id | defect | subject identity | silent proceed | classification registry | PASS |
| same | `test_mapping_missing_with_evidence_flagged_defect` | evidence unmapped | flag true | defect | mapping defect detection | Category-3 miss | classification registry | PASS |
| same | `test_runtime_exception_is_failed_not_blocked` | boom evaluator | knowledge | `failed` not `blocked` | technical≠blocked | misclassified blocked | probe `blocked_runtime_misclassified` | PASS |
| same | `test_blocked_fully_accounted_with_source_details` | blocked set | knowledge | accounted + missing domains | blocked accounting + source contribution | silent drop | probe blocked details | PASS |
| same | `test_resolving_dependency_unblocks_deterministically` | add hesitation rows | then +hesitation | blocked→qualified/observing | dependency resolution path | stuck blocked | demo re-seed scenarios | PASS |
| same | `test_blocked_rerun_no_duplicate_current` | double mat blocked | same | unique current | idempotent blocked refresh | dup rows | probe uniqueness | PASS |
| same | `test_supersession_when_block_resolved` | resolve then mat | then sources | old superseded, new current | historical supersession | orphan currents | materialize superseded count | PASS |
| same | `test_vip_deferred_comparison_cohort` | vip on d14 | signals | deferred block | comparison governance | fabricated comparison | deferred deps doc | PASS |
| same | `test_discount_deferred_message_strategy` | discount on d14 | hes+signals | deferred upstream | deferred dependency honesty | fake strategy claims | deferred deps doc | PASS |
| same | `test_determinism_unchanged_inputs` | twin generate | fixed as_of | equal fps/states/facts | determinism + claim stability | drift | probe determinism | PASS |
| same | `test_controlled_input_change_supersedes_affected_only` | add conflict stmt | then conflict | conflict fp changes; discount key stable | isolated candidate churn | full-store churn | N/A | PASS |
| same | `test_no_provider_bypass_in_source_adapters` | source inspect | — | no raw provider strings | no provider-specific bypass | bypass introduced | `source_adapters` list | PASS |
| same | `test_purchase_attribution_not_collapsed` | influence signals | purchase_confirmed + classes | prohibited collapse claims | Purchase≠Attribution≠ROI | recovered-revenue collapse | recovery_influence sample | PASS |
| same | `test_demo_allowlist_blocks_non_demo_writes` | non-demo probe | store≠demo | allowlist error | demo-only writes; store isolation | cross-store write | 403 / errors | PASS |
| same | `test_main_py_wiring_only` | inspect route | — | probe wiring only | main.py boundary | logic in main | code review | PASS |

**Multi-boundary note:** Several foundation tests prove multiple columns (e.g. `test_deterministic_rerun` covers determinism + idempotent rerun; `test_full_candidate_accounting_no_silent_loss` covers accounting + blocked/insufficient). Coverage is by boundary evidence, not by inflating test count.

---

## 2. Critical Boundary Evidence

| Boundary | Evidence |
|----------|----------|
| Governed contracts only | Adapters call `generate_knowledge_v1`, hesitation/purchase mapping reads, `load_store_commerce_signals_v1(force=True)` only |
| No provider bypass | Source adapter source inspection + probe `provider_independent=true` |
| Determinism | Twin generate same fingerprint; probe `deterministic=true` |
| Candidate accounting | `expected_candidate_count == candidate_count`; `unaccounted=0` |
| Purchase/Attribution/ROI | `recovery_influence_boundary` preserves class counts; prohibits collapsed recovered-revenue |
| main.py wiring only | Route only calls probe builder |

---

## 3. Blocked Candidate Investigation (Demo `d7`)

Production baseline (pre-patch probe samples) and post-patch classification use the same three rules. Live IDs rotate with `as_of`; rule keys and reasons are stable.

### Blocked #1 — `discount_message_weakness`

| Field | Value |
|-------|--------|
| Rule / subject | `discount_message_weakness` / `recovery_strategy`:`discount` (post-patch; was store on window path) |
| Window | `d7` |
| Required domains | `commerce_signals`, `product_hesitation` |
| Available (store) | `knowledge`, `commerce_signals` |
| Missing | `temporal_window_compatible_inputs` (d7 ∉ allowed_windows) |
| Reason code | `temporal_alignment_failed` |
| Phase | before_evaluation |
| Upstream evidence | N/A for d7; on d14+ would require `message_strategy_classification` (absent) |
| Expected? | Yes (temporal). Deferred aspect tracked as D-CISYN-01 for d14+ |
| Category | **1 — Expected Truthful Block** (on d7). Deferred on d14+ → Category 2 |
| Owner | `commerce_intelligence_synthesis` (temporal) / `message_strategy_classification` (deferred) |
| Remediation | None for d7. Future: D-CISYN-01 |

### Blocked #2 — `shipping_hesitation_recovery_outcome`

| Field | Value |
|-------|--------|
| Rule / subject | `shipping_hesitation_recovery_outcome` / `hesitation_reason`:`shipping` |
| Window | `d7` |
| Required | `product_hesitation` |
| Available | `knowledge`, `commerce_signals` |
| Missing | `product_hesitation` |
| Reason code | `required_source_data_unavailable` |
| Phase | before_evaluation |
| Mapping status | `no_in_window_hesitation_mappings` / unsupported `no_mappings` |
| Canonical evidence upstream? | No shipping hesitation rows in Demo window |
| Expected? | **Yes** |
| Category | **1 — Expected Truthful Block** |
| Owner | `product_hesitation_mapping` |
| Remediation | None (truthful empty). Seed Demo hesitation only if product wants a qualified sample |

### Blocked #3 — `vip_followup_outcome`

| Field | Value |
|-------|--------|
| Rule / subject | `vip_followup_outcome` / `vip_cohort`:`vip` |
| Window | `d7` |
| Required | `commerce_signals` |
| Available | `knowledge`, `commerce_signals` |
| Missing | `temporal_window_compatible_inputs` |
| Reason code | `temporal_alignment_failed` |
| Phase | before_evaluation |
| On d14+ | `comparison_cohort_unavailable` (deferred) |
| Expected? | Yes on d7; deferred comparison on d14+ |
| Category | **1** (d7) / **2** (d14+, D-CISYN-02) |
| Owner | CISYN temporal / `vip_followup_comparison_cohorts` |
| Remediation | None for d7. Future: D-CISYN-02 |

---

## 4. Blocked Classification

| Candidate | Category | Approval impact |
|-----------|----------|-----------------|
| discount @ d7 | Expected truthful | APPROVABLE |
| shipping | Expected truthful | APPROVABLE |
| vip @ d7 | Expected truthful | APPROVABLE |
| discount @ d14+ (no message strategy) | Deferred upstream | APPROVABLE WITH TRACKED DEFERRED |
| vip @ d14+ (no cohorts) | Deferred upstream | APPROVABLE WITH TRACKED DEFERRED |

**Targets:** `blocked_defect=0`, `blocked_runtime_misclassified=0`.

---

## 5. Determinism and Idempotency

- Twin generate (fixed `as_of`): identical candidate counts, states, input/synthesis fingerprints, known/unknown/prohibited.
- Double materialize: no duplicate current `synthesis_key`.
- Controlled knowledge conflict injection: only conflict candidate fingerprint changes; temporal-blocked discount `synthesis_key` retained.
- Non-demo probe: no writes (`store_not_allowlisted`).

---

## 6. Source Contract Verification

| Domain | Contract key | Version |
|--------|--------------|---------|
| knowledge | `generate_knowledge_v1` | `kf_v1` |
| product_hesitation | `product_hesitation_mapping_read_v1` | `phm_v1` |
| product_purchase | `product_purchase_mapping_read_v1` | `ppm_v1` |
| commerce_signals | `load_store_commerce_signals_v1` | `commerce_signals_v1` |

Forbidden: provider tables, raw Meta/Twilio, frontend state, page APIs, ungoverned JSON.

---

## 7. Purchase / Attribution / ROI Boundary

`recovery_influence_boundary` Demo sample:

- Emits `purchase_confirmed_signals` count separately from influence class counts.
- Prohibits `all_purchases_are_recovered_revenue` and `collapsed_influence_claim`.
- Does not emit ROI proof fields.
- Classes preserved: confirmed_recovery / high_confidence / possible_influence / unattributed_purchase.

---

## 8. Claim Boundary Verification

| State | Example rule | Known | Unknown | Prohibited |
|-------|--------------|-------|---------|------------|
| qualified | high_traffic_weak_conversion | engagement present, purchases weak | root cause | root_cause_known |
| observing | repeated_interest_pattern | cart_interest flags | why unresolved | intent_to_purchase_confirmed |
| insufficient | conflicting_evidence_store (no flags) | no conflict flags | single explanation | single_explanation_reliable |
| blocked | shipping… | reason code + phase | pattern not established | shipping_price_is_confirmed_cause |

No causal / guaranteed-outcome / unsupported revenue wording in known facts.

---

## 9. Failure Isolation

- Injected rule exception → that rule `failed`; other rules still accounted.
- Missing `product_hesitation` blocks only dependent rules (shipping, discount when evaluated); knowledge-based rules continue.
- Blocked candidates do not abort the refresh run.

---

## 10. Demo and Store Isolation

- Probe allowlist: `demo` only.
- Non-demo → error, no materialize.
- Materialize filters by `store_slug`; no cross-store writes in refresh path.

---

## 11. Deferred Dependencies

See `docs/product/COMMERCE_INTELLIGENCE_SYNTHESIS_V1_DEFERRED_DEPENDENCIES.md`:

- **D-CISYN-01** message strategy classification
- **D-CISYN-02** VIP comparison cohorts

---

## 12. Final Review Recommendation

**Narrow corrective patch included in this addendum (not a rebuild):**

- Governed blocked reason codes + classification module
- Probe exposes `blocked_candidates`, reason codes, classification counters
- Focused closure tests (18)
- Discount/VIP deferred paths use explicit blocked reasons (not silent insufficient)

**Final recommendation:**

```text
APPROVE WITH DOCUMENTED DEFERRED DEPENDENCIES
```

Conditions met: critical boundaries evidenced; all blocked candidates classified; `blocked_defect=0`; `blocked_runtime_misclassified=0`; unaccounted=0; determinism ok; Purchase/Attribution/ROI separated; no provider bypass; deferred items tracked.

---

## STOP

After closure validation:

**STOP.** Do not begin Knowledge integration, new Commercial Guidance, Merchant Presentation, Surface Composition, Home UI, Decision Workspace / Carts / Communication / Settings UI, automatic actions, or AI until the review decision is issued.
