# Commercial Intervention Intelligence V1 — Contract Design

STATUS: CONTRACT DESIGN ONLY. NO IMPLEMENTATION. NO DEPLOY.

## Objective

Move the merchant answer from `ما المشكلة؟` to:

> ما التدخل التجاري الآمن الذي يمكن اختباره الآن، ولماذا، وما الذي يمنع تدخلًا أقوى،
> وماذا سنقيس، ومتى نغيّر رأينا؟

The answer must stay evidence-governed and economically bounded. A stronger
intervention is never produced by writing stronger copy; it is produced only by
acquiring authoritative economic truth that CartFlow does not have today.

## Core finding

The layers this contract needs already exist and already run in production. This
design is therefore **an extension of existing owners, not a new layer**:

| Concern | Existing owner | Status for this contract |
| --- | --- | --- |
| Evidence / diagnosis | `services/commercial_opportunity_layer_v1` | Reused unchanged |
| Priority | `services/mission_catalog_v1` | Reused unchanged |
| Conflict / capacity | `services/mission_portfolio_v1` | Reused unchanged for Level ≤ 2 |
| Commitment / measurement lifecycle | `services/commercial_decision_commitment_v1` | Bounded snapshot-schema extension |
| Merchant intervention language | `services/commercial_action_language_v1` | Extended: this is the intervention owner |

`commercial_action_language_v1.contract_for_family_v1()` already returns eight
merchant fields (`situation_ar`, `evidence_ar`, `diagnosis_ar`, `mission_ar`,
`action_ar`, `dont_ar`, `measure_ar`, `recheck_ar`, `cta_ar`). Five of the eight
UI sections this task asks for are therefore already satisfied by an existing
owner. The real delta is three merchant fields plus governance metadata.

## Core flow

```
Evidence      → COL (truth_class, family, evidence_refs)
Problem       → Mission Catalog (role, priority, suppression)
Eligible      → CAL extension (level ceiling + eligibility_state)   ← new logic, existing owner
Safety Level  → CAL extension (recommendation_level)                ← new logic, existing owner
Economic pre  → Economic Input Manifest (static, all-missing today) ← new, read-only registry
Conflict      → Mission Portfolio (conflict_type, may_execute)
Merchant      → "اعتمد هذه المهمة" (unchanged CTA)
Measurement   → CDC (baseline snapshot, metric_key, window)
Recheck       → CDC (measurement_due_at, recheck_condition_frozen)
```

No second lifecycle. No second ranker. No new commitment table.

## Documents

| File | Contents |
| --- | --- |
| `INTERVENTION_CONTRACT.md` | Intervention object, recommendation levels, eligibility states, family ceilings, terminology |
| `ECONOMIC_INPUT_CONTRACT.md` | Required Level 3/4 inputs with authority, freshness, scope, missing-state behavior |
| `MEASUREMENT_CONTRACT.md` | Baseline, primary/guardrail metrics, windows, success/failure, causality boundary |
| `INTEGRATION_MAP.md` | Seams into COL / Catalog / Portfolio / CDC / Workspace, conflict groups, UI contract, query budget |
| `PROJECTIONS.md` | R17 projection, insufficient-evidence projection, future Level 3 projection |
| `REPORT.md` | Final verdict report |

## Verdict

`COMMERCIAL_INTERVENTION_CONTRACT_READY_FOR_IMPLEMENTATION`

See `REPORT.md` for the full report.
