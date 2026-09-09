# Commercial Intervention Intelligence V1 — Final Report

STATUS: CONTRACT DESIGN ONLY. NO IMPLEMENTATION. NO DEPLOY.

## VERDICT

`COMMERCIAL_INTERVENTION_CONTRACT_READY_FOR_IMPLEMENTATION`

Not blocked by ownership conflict: every concern maps to exactly one existing
owner, and `eligibility_state` is a derived projection rather than a competing
authority. Not blocked by measurement contract: baseline, primary, guardrail,
window, recheck, success, failure, and mind-change are all definable today from
existing hesitation and purchase truth. No redesign needed: the required lifecycle
already exists and runs in production.

## OWNERSHIP

| Role | Owner |
| --- | --- |
| INTERVENTION OWNER | `services/commercial_action_language_v1` (extended) — no new module |
| DIAGNOSIS OWNER | `services/commercial_opportunity_layer_v1` |
| PRIORITY OWNER | `services/mission_catalog_v1` |
| CONFLICT OWNER | `services/mission_portfolio_v1` |
| COMMITMENT OWNER | `services/commercial_decision_commitment_v1` |

## RECOMMENDATION LEVELS

`0 FACT`, `1 INTERVENTION_CANDIDATE`, `2 BOUNDED_SAFE_TEST`,
`3 ECONOMICALLY_PARAMETERIZED`, `4 PRODUCT_SPECIFIC`. No level skipping. Ceiling =
`min(family_max_level, max_level_supported_by_available_inputs)`.

Level 2 boundary: an action may change what the customer is **told**, never what
the merchant **charges, pays, or gives away**.

## ELIGIBILITY STATES

`ELIGIBLE`, `INSUFFICIENT_EVIDENCE`, `ECONOMIC_INPUTS_REQUIRED`,
`CONFLICTING_SIGNALS`, `ALREADY_UNDER_MEASUREMENT`, `INTERVENTION_NOT_JUSTIFIED`,
`WAIT_AND_RECHECK`.

Derived, first-match-wins, from COL `truth_class`, CDC phase, Portfolio
`conflict_type`, Catalog role, and the Economic Input Manifest. Unknown input
resolves to `WAIT_AND_RECHECK`, never to `ELIGIBLE`.

Fail-safe: no eligible intervention → no recommendation escalation.

## LEVELS TODAY

| Family | Level today | Ceiling reason |
| --- | --- | --- |
| SHIPPING | **2** | `shipping_cost` / `shipping_subsidy` / margin truth absent |
| PRICE | **2** | `product_cost` / `gross_margin` / `margin_floor` absent |
| PRODUCT_CONFIDENCE | **2** | Level 3 not defined for this family |
| COMPLEMENTARY_PRODUCTS | **1** | Product-pair economics, inventory, compatibility absent |

## LEVEL 3 ECONOMIC INPUTS

`shipping_cost`, `shipping_subsidy`, `product_cost`/COGS, `gross_margin`,
`margin_floor`, `payment_fees`, `platform_commission`, `AOV`.

Observed status: eight of ten manifest fields fully missing, `AOV` partial
(`purchase_truth_records` carries no monetary amount, so order value is not
authoritative), `product_pair_counts` derivable from `cart_line_snapshots` but
evidence rather than economics.

Each field declares authority, freshness, scope, and missing-state behavior in
`ECONOMIC_INPUT_CONTRACT.md`. No fallback defaults: a missing input blocks the
level and never degrades into an estimate. A stale declaration is treated as
missing, not approximate.

## LEVEL 4 ADDITIONAL INPUTS

`product_pair_counts` with sufficiency threshold, `inventory_quantity` fresh
within 24 hours, per-product economics for both products, shipping impact of the
added product, and compatibility evidence.

## NO-ACTION CONTRACT

`INSUFFICIENT_EVIDENCE` and `WAIT_AND_RECHECK` produce a full eight-section card
stating what is being waited for, why waiting is the correct decision, and what
ends the wait. `guardrail_metric` is null because nothing changes. Never an empty
card, never a degraded recommendation.

## CONFLICT CONTRACT

Groups: `disclosure_only`, `product_confidence_content`, `shipping_economics`,
`price_economics`, `bundle_economics`, `active_measurement`.

Rule: one economic lever per subject per measurement window unless Portfolio
proves non-conflict. Intervention Intelligence declares `conflict_group`;
Portfolio decides `may_execute`. No parallel conflict engine.

Portfolio change required for V1: **none** — every emittable intervention today is
`disclosure_only` or `product_confidence_content`, already covered by the existing
family-pair matrix and `MAX_ACTIVE_MISSIONS = 1`.

## MEASUREMENT CONTRACT

Every Level 2+ intervention defines baseline, primary metric, guardrail metric,
window, recheck, success, failure, and mind-change. Baseline freezes at
measurement start, not accept, since accept is not evidence of execution. Failure
must be reachable.

Revenue alone is never sufficient, and today is not even measurable: purchase
count truth is authoritative, purchase value truth does not exist.

## CAUSALITY CONTRACT

Observational and causal results stay separate. Allowed:
`بعد التدخل تحسن المؤشر خلال نافذة القياس.` Forbidden: `التدخل سبب التحسن.`

Already partly enforced in schema:
`FORBIDDEN_CLOSE_REASONS = {"won","lost","learned","purchase","measurement_expired"}`.
No measurement-result column is proposed; the observational delta is derived at
read time from the baseline snapshot plus live evidence.

## CDC EXTENSION NEEDED

**YES — bounded, snapshot-schema only. No DB change.**

Five optional keys added to the `cdc_decision_snapshot_v1` allowlist in
`snapshots_v1.py`: `intervention_id`, `recommendation_level`, `eligibility_state`,
`conflict_group`, `economic_inputs_state`. All fit inside the existing
`decision_snapshot_json` column and the `SNAPSHOT_MAX_BYTES = 4096` budget.
Additive and optional on read, so existing rows remain parseable.

No new table. No new column. No migration.

## STRUCTURAL ANSWERS

| Question | Answer |
| --- | --- |
| NEW LIFECYCLE | NO required |
| NEW RANKER | NO required |
| AI REQUIRED | NO |
| EXTERNAL API REQUIRED | NO |
| NEW SCHEDULER WORK | NO |

## EXPECTED QUERY DELTA

**+0 page queries.** All inputs already exist in the composed store bundle; the
level ceiling is a static registry constant and the Economic Input Manifest
resolves to "no authority registered" without a database read.

Maximum +1 store-scoped snapshot, and only when a real economic source is later
registered. No per-intervention query, no per-product loop, zero AI calls, zero
external API calls, zero scheduler work for eligibility.

## PROJECTIONS

- **R17**: shipping 12/20 = 60%, `ELIGIBLE`, Level 2, `disclosure_only`. Diagnosis unchanged from production. No monetary value, threshold, or direction in any merchant-facing field. Level 3 retained as a blocked candidate with five named missing inputs.
- **INSUFFICIENT-EVIDENCE**: `hesitation_total = 4`, no dominant reason → Level 0, `INSUFFICIENT_EVIDENCE`, full explanatory card, null guardrail.
- **LEVEL 3 DESIGN**: free-shipping-threshold shape with placeholder notation only (`<SHIPPING_COST>`, `<THRESHOLD>`, `<MERCHANT_DECLARED_MARGIN_FLOOR>`), explicit `margin_after_intervention >= margin_floor` assertion and stop-loss. No invented numbers.

Full shapes in `PROJECTIONS.md`.

## TERMINOLOGY

| Item | Value |
| --- | --- |
| MERCHANT-FACING `البيع المتقاطع` | 0 required — 0 present on merchant dashboard today |
| MERCHANT-FACING TERM | `منتجات مكملة` |
| INTERNAL IDENTIFIER | `cross_sell` retained |

Existing `cross_sell` strings live only in simulation/lab lineages
(`revenue_reality_validation_v1`, `commercial_decision_library_v1_1`) that COL
already blocks from `/dashboard` via `FORBIDDEN_SIM_MARKERS`. Implementation note:
`mission_composer_v1.py` carries `فرصة حزمة / بيع متقاطع`, which must become
`منتجات مكملة` before any lab surface becomes merchant-visible.

## NEW TECHNICAL DEBT

**NONE required.** No duplicated ownership, no compatibility shim, no parallel
lifecycle. `eligibility_state` derives from existing owners instead of storing a
competing authority.

Recorded boundary: `guidance_eligibility_evaluations` / `commercial_guidance_records`
belong to the `services/product_data` knowledge lineage, are subject-scoped, are
documented as "not merchant UI copy", and are not read by the dashboard path. They
are not the owner of intervention eligibility. Consolidating the two eligibility
concepts would be a separate design task, not a silent reuse.

## UI CONTRACT

Eight merchant sections, five already produced by CAL. Real delta is three fields:
`why_this_is_safe_ar`, `guardrail_metric`, `mind_change_condition`, plus the
blocked-candidates block behind section 4. `اعتمد هذه المهمة` and
`ACCEPTED_STATE_AR` preserved unchanged. Workspace not redesigned; no visuals in
this task.

## FINAL FLAGS

| Flag | Value |
| --- | --- |
| READY FOR IMPLEMENTATION | **YES** |
| READY FOR LIVE UI COMPOSITION | NO |
| DEPLOY | NO |

## OBSERVATION NOTE

This design re-observed the five commercial layers directly in the tree rather
than relying on working assumptions carried over from the Commercial Guidance
Economic Safety Closure V1 session, during which COL was at one point described
as a design identity without a runtime module. That description was wrong, and it
never entered the written record — the safety closure report's ownership table is
correct.

Confirmed implemented and running in production:
`services/commercial_opportunity_layer_v1`, `services/mission_catalog_v1`,
`services/mission_portfolio_v1`, `services/commercial_decision_commitment_v1`,
`services/commercial_action_language_v1`.

This is the finding that makes the verdict `READY_FOR_IMPLEMENTATION` rather than
`NEEDS_REDESIGN`: the lifecycle this contract needs is already built, so the work
is an extension of existing owners rather than a new layer.
