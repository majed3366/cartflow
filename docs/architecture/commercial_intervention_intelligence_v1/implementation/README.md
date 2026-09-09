# Commercial Intervention Intelligence V1 — Implementation Evidence

STATUS: IMPLEMENTED. NOT DEPLOYED. NOT WIRED TO ANY MERCHANT SURFACE.

Branch: `candidate/commercial-intervention-intelligence-v1`

## 1. Runtime delta

Four files. Two modified (49 added lines, 0 removed), two added.

| File | Change |
| --- | --- |
| `services/commercial_action_language_v1/intervention_v1.py` | **New** (631 lines) — the entire intervention layer |
| `services/commercial_action_language_v1/__init__.py` | +14 — exports only |
| `services/commercial_decision_commitment_v1/snapshots_v1.py` | +35 — snapshot allowlist + 5 optional build kwargs + level bound |
| `tests/test_commercial_intervention_intelligence_v1.py` | **New** (529 lines) — 52 tests |

No new service. No new lifecycle. No new ranker. No new table. No new column. No
migration. No scheduler work. No merchant surface is wired: the layer is a
library, and live UI composition is a separate authorized task.

## 2. Ownership proof

`intervention_v1.py` imports four leaf `contract_v1` modules and consumes their
vocabulary read-only. It never re-derives, overrides, or persists any of them:

| Owner | Consumed as | Overridden? |
| --- | --- | --- |
| COL | `truth_class` | No |
| Mission Catalog | `role` | No |
| Mission Portfolio | `conflict_type` | No |
| CDC | `phase`, `resolve_measurement_window_days()` | No |
| CAL `contract_for_family_v1()` | situation / evidence / action / dont / measure / recheck | No — merged, never re-authored |

No import cycle: CDC imports nothing from CAL, COL, Catalog, or Portfolio, and
all four imported `contract_v1` modules depend only on `typing`.

The four delta fields (`why_this_is_safe_ar`, `guardrail_metric`,
`mind_change_condition`, `blocked_candidates`) are authored **only** here.
`compose_merchant_intervention_card_v1()` is the single place base and delta are
merged, which is why no field has two authors.

`guidance_eligibility_evaluations` is not imported, read, written, adapted, or
migrated. A test asserts the string does not appear in the module.

## 3. Eligibility precedence

Derived by `derive_eligibility_v1()`. Never persisted; there is no eligibility
row, column, or cache.

```
1. INSUFFICIENT_EVIDENCE        COL truth INSUFFICIENT / absent
2. ALREADY_UNDER_MEASUREMENT    own CDC phase ACTION_CHOSEN | UNDER_MEASUREMENT
3. CONFLICTING_SIGNALS          Portfolio MUTUALLY_EXCLUSIVE | MEASUREMENT_CONTAMINATION
4. INTERVENTION_NOT_JUSTIFIED   Catalog suppressed | Portfolio DUPLICATE_INTENT
5. ECONOMIC_INPUTS_REQUIRED     requested level >= 3 and missing inputs
6. WAIT_AND_RECHECK             anything not positively recognised
7. ELIGIBLE                     every input positively recognised
```

Two precedence decisions carried over from the simulation gate:

- **`CAPACITY_ONLY` → `WAIT_AND_RECHECK`.** Portfolio's capacity verdict is a
  defer, not a rejection. The intervention is justified; the store is busy.
- **`DUPLICATE_INTENT` → `INTERVENTION_NOT_JUSTIFIED`.** Same intent already
  covered, so the intervention genuinely is not warranted.

`ELIGIBLE` requires positive recognition of every input, so unknown tokens fall
through to `WAIT_AND_RECHECK` without needing an explicit unknown branch. This is
what makes Portfolio's execution deny structurally incapable of producing an
executable CTA.

## 4. Level model

```
effective_level = min(family_max_level, level_supported_by_available_inputs)
```

`level_supported_by_inputs_v1()` walks the ladder contiguously and stops at the
first gap, so a level can never be skipped.

| Family | max | supported today | effective |
| --- | --- | --- | --- |
| `shipping_friction` | 3 | 2 | **2** |
| `price_hesitation` | 3 | 2 | **2** |
| `product_confidence` | 2 | 2 | **2** |
| `product_opportunity_focus` (منتجات مكملة) | 4 | 1 | **1** |

Levels 2–3 are undefined for complementary products, so the contiguity rule keeps
that family at 1 **even with a complete economic manifest**. Naming a product B
can never be unlocked by acquiring money facts alone.

`economic_manifest_v1()` is a static registry returning `None` for all twelve
fields. It performs no database read and substitutes no default.

## 5. Level 2 hard boundary

`validate_intervention_card_v1()` scans `what_we_suggest_ar` and
`why_this_is_safe_ar` for economic-lever markers (خصم, خفّض, شحن مجاني, ر.س, ٪,
حد أدنى, دعم الشحن) and rejects the card with `level2_invariant_violation`.

The scan is negation-aware: `لا تخفّض الشحن ولا تجعله مجانياً` is a guardrail, not
an instruction, and must not trip the check. Only `dont_do_ar`-style negated
usage survives; a positive instruction like `اختبر الشحن المجاني فوق 199 ر.س.` is
rejected (tested).

## 6. CTA safety

`cta_ar` is emitted **only** when `eligibility_state == ELIGIBLE`; every other
state yields `None`. `cta_on_blocked_card` is a hard validation error.

Blocked cards are not empty and not imperative. `DEFERRAL_AR` prefixes the
suggestion with what is blocked, why, and what CartFlow is waiting for — e.g.
`مؤجّل الآن: لديك مهمة نشطة قد يفسد قياسها هذا التدخل. ما ننتظره هو إغلاق المهمة الحالية.`

## 7. CDC snapshot allowlist

Five additive keys in `_DECISION_ALLOWED`: `intervention_id`,
`recommendation_level`, `eligibility_state`, `conflict_group`,
`economic_inputs_state`. All optional on read, so pre-existing rows still parse
(tested). `recommendation_level` is bounded to 0–4 on both build and parse.

Everything lives inside the existing `decision_snapshot_json` Text column within
the existing `SNAPSHOT_MAX_BYTES = 4096` budget. Unknown keys — including
`causal_verdict` — are still rejected (tested). No result or causal verdict is
persisted.

CDC does not import CAL, so no cycle is introduced by the bound check.

## 8. Query proof

`derive_eligibility_v1()` takes primitives only; the test asserts no `session` or
`db` parameter exists. `economic_manifest_v1()` is a constant. Every other input
(`truth_class`, `role`, `conflict_type`, `phase`) already exists in the composed
store bundle.

| Item | Value |
| --- | --- |
| Page query delta | **+0** |
| Per-intervention query | 0 |
| Per-product loop | 0 (N+1: none) |
| AI calls | 0 |
| External API calls | 0 |
| Scheduler work | 0 |

## 9. Simulation parity

`implementation/parity_check_v1.py` imports `simulation_v1.py` and the real
runtime side by side and compares level, eligibility state, CTA presence, blocked
reason, and section count across all 8 governed projections.

**Result: 8/8 in parity** (`implementation/PARITY.md`). Not a mock-only green —
the runtime path is exercised, and the runtime card is additionally re-validated
by `validate_intervention_card_v1()` inside the parity run.

## 10. Tests

`tests/test_commercial_intervention_intelligence_v1.py` — **52 passed**.

Covers every required case: R17 shipping Level 2, price Level 2, product
confidence Level 2, complementary products Level 1, insufficient evidence,
capacity-only, duplicate intent, conflicting signals (via the real
`evaluate_conflict_v1`), already under measurement, recheck-due still eligible,
explicit Level 3 request blocked by economics, each of the 8 economic inputs
blocking independently, complete economics unlocking Level 3, no level skipping,
unknown input → wait, CTA eligible, CTA blocked, blocked-card copy, CDC snapshot
accepted, snapshot ≤ 4096 bytes, unknown CDC keys still rejected, bad level
rejected, legacy snapshot still parses, revenue verdict blocked by column
introspection, merchant-facing `البيع المتقاطع` = 0, query purity, and the 8-way
simulation parity.

## 11. Regressions

Impacted set: 38 suites referencing CAL, CDC, COL, Catalog, Portfolio, or the
Decision Workspace.

| Run | Result |
| --- | --- |
| Candidate | **8 failed, 478 passed** |
| Baseline (same 38 files, changes stashed) | **10 failed, 476 passed** |

The same 8 failures appear in both and are pre-existing (`test_business_themes_v1`,
`test_commerce_situations_v1`, `test_decision_workspace_v2_budget`,
`test_gate_2a_decision_workspace_v1`, `test_merchandising_mission_slice_v1`,
`test_merchant_ui_v2`, `test_mission_catalog_projection_v1`,
`test_products_commercial_truth_v1`).

**Zero new regressions.** The 2 extra baseline failures are the new CDC snapshot
tests, which fail without the allowlist change — a control confirming those tests
exercise real runtime behaviour rather than passing vacuously.

COL, Mission Catalog priority, Portfolio conflicts, CDC lifecycle, Products,
Carts, Home, Product Exposure, and Scheduler are untouched.

## 12. Technical debt

**NONE.** No duplicate authority, no compatibility shim, no temporary second
path, no TODO debt. Eligibility is derived rather than stored, so no layer gained
a second opinion about its own domain.
