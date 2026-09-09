# Commercial Intervention Intelligence V1 — Simulation Gate Report

STATUS: SIMULATION / PROTOTYPE GATE. NO IMPLEMENTATION. NO DEPLOY.

Executable prototype: `simulation_v1.py` (non-production, imported by nothing).
Raw output: `SIMULATION_RESULTS.md`.

Run: `python docs/architecture/commercial_intervention_intelligence_v1/simulation_v1.py`
Result: **96 / 96 checks passed.**

The simulation imports the **real production owners** read-only rather than mocking
them, so the proofs are not self-referential:

| Real module used | What it proved |
| --- | --- |
| `commercial_opportunity_layer_v1.truth_gate_v1` | R17 classification is genuinely `PRODUCTION_TRUTH_READY` |
| `mission_portfolio_v1.conflict_v1` | Every conflict verdict came from Portfolio, not from the prototype |
| `commercial_action_language_v1.contract_v1` | The 5 existing merchant fields are reused, never re-authored |
| `commercial_decision_commitment_v1.snapshots_v1` | Snapshot budget and allowlist rejection are measured, not asserted |
| `models` | Column introspection of `purchase_truth_records` and `guidance_eligibility_evaluations` |

## VERDICT

`COMMERCIAL_INTERVENTION_SIMULATION_PASS`

## Corrections the gate forced

The first run passed 89/89, and three of those greens were wrong. The gate earned
its keep by making them visible:

1. **Capacity-occupied carried the wrong merchant meaning.** Portfolio's
   `CAPACITY_ONLY` was mapped to `INTERVENTION_NOT_JUSTIFIED`, which tells a
   merchant the intervention is not warranted when the truth is that the store is
   busy with an active mission. Remapped so `CAPACITY_ONLY` falls through to
   `WAIT_AND_RECHECK` (deferred); only `DUPLICATE_INTENT` is genuinely unjustified.
2. **Projection 8 never requested Level 3.** It was byte-identical to projection 1
   and proved nothing. It now issues an explicit Level 3 request and asserts the
   request itself resolves to `ECONOMIC_INPUTS_REQUIRED` with Level 2 offered
   instead.
3. **Blocked cards still rendered an executable instruction and the accept CTA.**
   A `CONFLICTING_SIGNALS` card showed «افتح أسباب التردد…» plus «اعتمد هذه المهمة»,
   which would have let a merchant execute a deferred intervention. Deferral text
   now prefixes the suggestion, the CTA is withheld unless the state is `ELIGIBLE`,
   and `cta_on_blocked_card` is a hard validation error.

## ARCHITECTURE FLOW

| Step | Input owner | Output owner | Authority | Derived field | Fail-closed |
| --- | --- | --- | --- | --- | --- |
| diagnosis | store truth bundle | COL | COL | `truth_class` / `family` / `evidence_refs` | `INSUFFICIENT` |
| priority | COL | Mission Catalog | Catalog | `role` / rank / suppression | `suppressed` |
| conflict | Catalog | Portfolio | Portfolio | `conflict_type` / `may_execute` | `CAPACITY_ONLY` |
| commitment | Portfolio | CDC | CDC | `phase` / baseline / window | no row |
| economics | Economic Input Manifest | CAL | Manifest (static) | `missing_inputs` | all missing |
| eligibility | CDC | CAL | CAL extension (derived) | `eligibility_state` | `WAIT_AND_RECHECK` |
| language | CAL | Decision Workspace | CAL | 8 merchant sections | no-action card |

**CIRCULAR OWNERSHIP: NO.** Depth-first cycle detection over the compose-time
dependency graph found no cycle, and the Decision Workspace has zero outgoing
edges (projection-only). The accept → measure → recheck loop is *temporal*,
mediated by CDC persistence across separate transactions; it is not a compose-time
data cycle.

**DUPLICATED AUTHORITY: NO.** Seven transitions, seven distinct authorities, no
derived field with two owners.

## ELIGIBILITY DERIVATION

All seven states reachable, derived first-match-wins from COL `truth_class`, CDC
phase, Portfolio `conflict_type`, Catalog role, and the economic manifest. Nothing
is persisted.

`ELIGIBLE` requires **positive recognition of every input**. Any unrecognized
token fails through to `WAIT_AND_RECHECK` rather than being ignored, which is why
all five unknown-input cases in the failure model land safely without a single
explicit "unknown" branch.

## LEVEL CEILING PROOF

| Family | family_max | inputs support | effective |
| --- | --- | --- | --- |
| `shipping_friction` | 3 | 2 | **2** |
| `price_hesitation` | 3 | 2 | **2** |
| `product_confidence` | 2 | 2 | **2** |
| complementary products | 4 | 1 | **1** |

Two controls prove the ceiling is input-driven rather than hardcoded: a complete
manifest *does* raise shipping to Level 3, and complementary products *cannot*
jump 1 → 4 even with a complete manifest, because levels 2–3 are undefined for
that family and the contiguity rule stops the ladder. Naming a product can never
be reached by acquiring economics alone.

## SCENARIO RESULTS

| Scenario | Result |
| --- | --- |
| R17 | `ELIGIBLE`, Level 2, diagnosis unchanged (12/20 preserved), Level 2 invariant clean, L3 blocked with 8 named missing inputs |
| PRICE | `ELIGIBLE`, Level 2, L3 discount blocked (6 missing inputs) |
| PRODUCT_CONFIDENCE | `ELIGIBLE`, Level 2, section 4 states no stronger level is defined |
| COMPLEMENTARY_PRODUCTS | `ELIGIBLE`, Level 1, no product named, `البيع المتقاطع` absent from the whole payload |
| INSUFFICIENT_EVIDENCE | `INSUFFICIENT_EVIDENCE`, Level 0, 8/8 sections populated, CTA withheld |
| CONFLICTING_SIGNALS | `CONFLICTING_SIGNALS` from Portfolio `MEASUREMENT_CONTAMINATION`, CTA withheld |
| ALREADY_UNDER_MEASUREMENT | `ALREADY_UNDER_MEASUREMENT`, no parallel intervention, CTA withheld |
| LEVEL_3_BLOCKED | Explicit L3 request → `ECONOMIC_INPUTS_REQUIRED`, Level 2 offered instead |

All eight projections render all eight merchant sections and pass structural
validation.

## EVENT TRANSITIONS

All eight sequences pass against a CDC phase machine, plus a fail-closed check
that an unknown event never advances phase.

- **A** accept → `ACTION_CHOSEN`
- **B** execution surface opened, no proof → stays `ACTION_CHOSEN`
- **C** execution confirmed → `UNDER_MEASUREMENT`, baseline frozen at measurement start
- **D** stronger same-family candidate while measuring → `ALREADY_UNDER_MEASUREMENT`
- **E** window elapsed → `RECHECK_DUE`; observational delta only, `close_reason` outside `FORBIDDEN_CLOSE_REASONS`
- **F** shipping measuring + price strengthens → Portfolio `MEASUREMENT_CONTAMINATION` → `CONFLICTING_SIGNALS`
- **G** L3 candidate with missing economics → `ECONOMIC_INPUTS_REQUIRED`, safe downgrade to Level 2
- **H** insufficient evidence → explanatory no-action card, 8/8 sections

## ECONOMIC INPUT FAILURE

Eight fields removed independently from an otherwise complete manifest. Each
produced `ECONOMIC_INPUTS_REQUIRED`, listed exactly the one missing field, and
downgraded to Level 2. No default was substituted in any case.

## REVENUE CLAIM SAFETY

`purchase_truth_records` columns were introspected directly: no `amount`,
`value`, `total`, `price`, or `revenue` column exists. Revenue-based success
verdicts are therefore **BLOCKED** by absence of truth, not by policy alone.
`abandoned_carts.cart_value` exists but is cart value at abandonment, not order
value at purchase. Merchant language carries no revenue claim.

## PORTFOLIO CONFLICT OWNERSHIP

All five conflict cases were decided by the real `evaluate_conflict_v1`; the
prototype consumed `conflict_type` verbatim and never overrode it.

| Case | Portfolio verdict | Eligibility |
| --- | --- | --- |
| shipping disclosure + price clarification | `CAPACITY_ONLY` | `WAIT_AND_RECHECK` |
| shipping economic change + price discount | `MEASUREMENT_CONTAMINATION` | `CONFLICTING_SIGNALS` |
| bundle + direct discount | `MEASUREMENT_CONTAMINATION` | `CONFLICTING_SIGNALS` |
| product-confidence content + price change | `MUTUALLY_EXCLUSIVE` | `CONFLICTING_SIGNALS` |
| active measurement + new economic lever | `CAPACITY_ONLY` | `WAIT_AND_RECHECK` |

`may_execute` was `False` in every case. `MAX_ACTIVE_MISSIONS == 1` honoured.

## CDC SNAPSHOT SIZE

Realistic extended snapshot with all five proposed keys: **607 bytes** against a
4096-byte budget, leaving 3489 bytes of headroom.

`parse_and_validate_decision_snapshot` rejects it today with
`decision_snapshot_unknown_keys`, which proves the allowlist edit in
`snapshots_v1.py` is the **only** change required. No result or causal-verdict key
is present. No new table, no new column.

## GUIDANCE_ELIGIBILITY_EVALUATIONS RELATION

**DISTINCT** (overlapping only at the level of purpose — both are permission gates).

| Dimension | GEF | Intervention eligibility |
| --- | --- | --- |
| Grain | `subject_type` / `subject_id` (product) | family / mission |
| Inputs | knowledge count, quality, trend, expiry, conflict flags | COL truth, CDC phase, Portfolio conflict, Catalog role, economics |
| Vocabulary | 6 states | 7 states — only `ELIGIBLE` is shared |
| Persistence | materialized rows | derived, never stored |
| Consumer | `services/product_data` lineage; explicitly "not merchant UI copy" | Decision Workspace |

**REUSE GUIDANCE_ELIGIBILITY_EVALUATIONS: NO.** Semantics and authority are not
equivalent. Boundary documented; table untouched; no technical debt from the
decision.

## COST

| Item | Value |
| --- | --- |
| QUERY DELTA | **+0** |
| AI CALLS | 0 |
| EXTERNAL API CALLS | 0 |
| SCHEDULER WORK | 0 |
| NEW DB TABLE | NO |
| NEW COLUMN | NO |

Every eligibility input is already present in the composed store bundle; the
remaining two are static registry constants. `derive_eligibility` was verified to
be a pure function over primitives with no session or db argument.

## FAILURE MODEL

Fourteen cases, all fail closed: unknown COL truth, unknown Catalog role,
Portfolio conflict unavailable, stale CDC state, unsupported family, missing
economic manifest, partial economic manifest, merchant already measuring, unknown
intervention id, malformed blocked candidate, recommendation level jump, missing
guardrail metric, missing mind-change condition, and a Level 2 card carrying an
economic instruction (`اختبر الشحن المجاني فوق 199 ر.س.` → rejected by the
Level 2 invariant).

## FINAL FLAGS

| Flag | Value |
| --- | --- |
| NEW TECHNICAL DEBT | NONE required |
| NEW LIFECYCLE | NO |
| NEW RANKER | NO |
| READY FOR IMPLEMENTATION | **YES** |
| READY FOR LIVE UI COMPOSITION | NO |
| DEPLOY | NO |
