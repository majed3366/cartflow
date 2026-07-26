# Merchant Understanding Repair V1

**Status:** Implemented (await production Living Store CEO verification)  
**Gate 2:** remains OPEN until certified review passes the five understanding questions  
**Product Intelligence / Gate 3:** LOCKED  

## Problem

Reality Validation identity was certified `CONSISTENT`, but merchant surfaces independently interpreted that reality — producing calm vs attention, duplicate P1/P2 actions, communication “normal” vs missing-contact urgency, and cart “no action” vs Workspace “act now.”

## Repair (no new engine)

Extended Decision Composition with a shared publication envelope:

`summary["merchant_publication_v1"]` / Workspace `projection["merchant_publication_v1"]`

Fields:

- `store_condition`
- `highest_priority_situation_id`
- `highest_priority_decision_id`
- `primary_business_action`
- `secondary_decision_ids`
- `communication_condition`
- `cart_operational_action`
- `systemic_business_action`
- `suppressed_duplicate_decisions`
- `truth_version`
- `simulation_run_id`

### Failure → fix map

| ID | Fix |
|----|-----|
| F1 | Store condition derived from admitted priority / actionable situations — calm forbidden when `needs_action_now` or actionable situation exists |
| F2 | Exactly one `highest_priority_decision_id`; Home shows one primary decision teaser; Workspace marks primary first |
| F3 | Recovery vs operations titles distinct; post-title action dedupe (`duplicate_recommended_action`) |
| F4 | Communication condition = contact constraint when missing contact; never “normal” when constrained |
| F5 | Cart-level `لا يحتاج إجراءً فردياً الآن.` vs systemic business action linked to Workspace |

## Key modules

- `services/decision_composition_engine_v1/merchant_publication_v1.py`
- `services/decision_composition_engine_v1/compose_v1.py` (stamps envelope)
- `services/decision_composition_engine_v1/store_executive_understanding_v1.py` (distinct titles)
- `services/decision_composition_engine_v1/dedupe_v1.py` (`dedupe_published_by_action_v1`)
- `services/merchant_home_experience_activation_v1.py` (attach before HES)
- `services/home_executive_summary_v1/compose_v1.py` + `slim_transport_v1.py`
- `services/cart_workspace/business_findings_enrichment_v1.py`
- `services/merchant_explanation_v1.py` (cart-level wording)
- `static/commerce_situations_surfaces_v1.js` / `static/cart_workspace_decision_card_v1.js`

## Tests

`tests/test_merchant_understanding_repair_v1.py`  
`tests/test_gate_2x_merchant_understanding_v1.py` (updated expectations)

## Required production validation (after deploy)

1. Reality Validation Console → Run Living Store → Bind → Identity: `CONSISTENT` + `CEO_REVIEW_SAFE=TRUE`
2. Prove Home condition agrees with active priority
3. Exactly one highest-priority decision across Home + Workspace
4. P1 and P2 meaningfully different (or duplicates suppressed)
5. Home and Communication agree on communication condition
6. Carts and Workspace show cart-level vs business-level distinction (not contradiction)
7. Same `simulation_run_id`, `highest_priority_situation_id`, `truth_version` on every surface
8. Desktop and Mobile identical meaning
9. Pass the five 30-second merchant-understanding questions

**STOP on first remaining contradiction after certified review.**
