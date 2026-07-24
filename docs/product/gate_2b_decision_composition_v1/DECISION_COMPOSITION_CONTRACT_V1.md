# Decision Composition Contract V1

**Gate:** 2B — Decision Composition Engine  
**Version:** `decision_composition_engine_v1`  
**Flag:** `CARTFLOW_DECISION_COMPOSITION_ENGINE_V1` (default ON)

---

## Purpose

Transform Operational Truth + Evidence + Observations + Existing Findings + Merchant Context into a **Prioritised Business Decision** with explanation and recommended action.

Counters alone are never decisions.

---

## Pipeline (sole path)

```text
Truth Inputs
  → Decision Candidate
  → Evidence Sufficiency Validation
  → Business Meaning Composition
  → Priority Calculation
  → Recommended Action Selection
  → Decision Contract Validation
  → Cart Workspace
```

No alternate composition path when the flag is ON.

---

## Required publish fields

| Field | Meaning |
|-------|---------|
| `decision_id` | Stable id (`dce:…`) |
| `store_slug` | Merchant store |
| `decision_type` | recoverability_gap / waiting_recovery_work / verified_existing_finding |
| `decision_subject_type` | store \| product |
| `decision_subject_id` | Required for product |
| `title` / `merchant_decision` | What to decide/change |
| `why` | Why raised |
| `why_now` | Why it matters now |
| `evidence_summary` + `evidence_refs` | Supporting evidence |
| `ignore_consequence` | If ignored |
| `recommended_action` | Practical action |
| `first_step` | First concrete step |
| `expected_outcome` | Expected result |
| `confidence` | high \| medium \| low |
| `priority` | Deterministic score 0–100 |
| `source_truth_types` | Provenance |
| `generated_at` / `valid_until` | Freshness |
| `composition_version` | Engine version |

Product decisions must name a real product — never «هذا المنتج».

---

## Suppression (never silent)

| Reason code | When |
|-------------|------|
| `insufficient_evidence` | Missing/weak evidence |
| `conflicting_evidence` | Material conflict |
| `subject_unidentified` | Product/subject missing |
| `action_unsupported` | No safe action |
| `stale_finding` | Lifecycle stale/expired |
| `duplicate_decision` | Same type+subject |
| `normal_state_no_merchant_action` | Automation-handled wait / zero gap |
| `generic_product_language` | Banned wording |
| `contract_incomplete` | Required field missing |

Every suppression is recorded in `suppression_registry`.
