# CartFlow Merchant Decision Implementation V1

**Date (UTC):** 2026-07-04  
**Status:** Implemented — decision execution layer  
**Governance:** [`merchant_decision_foundation_v1.md`](merchant_decision_foundation_v1.md), [`merchant_decision_governance_v1.md`](merchant_decision_governance_v1.md)

---

## Purpose

The **Merchant Decision Layer** transforms governed **Proof** into governed **Decisions**. It is the single execution engine between Proof and Merchant Action.

Presentation layers **consume** `merchant_decisions_v1` — they never mint or modify decisions.

---

## Architecture

```
Truth → Evidence → Proof → Merchant Decision Layer → Consumers
```

| Input | Module |
|-------|--------|
| Proof bundle | `merchant_proof_surface_v1` |
| Lifecycle / intervention context | LT-C1 row fields, `merchant_decision_key` |
| Decision templates | `merchant_decision_registry_v1` |
| KL insights | `/api/knowledge/report` insights |

| Output | Payload key |
|--------|-------------|
| Cart row decisions | `merchant_decisions_v1` on normal-carts rows |
| KL observation decisions | `merchant_decisions_v1` on knowledge report |

---

## Modules

| File | Role |
|------|------|
| `services/merchant_decision_registry_v1.py` | Stable `decision_id` templates (registry pattern) |
| `services/merchant_decision_layer_v1.py` | Execution engine + V1-A key resolver |
| `main.py` | `attach_merchant_decisions_v1` after proof surface |
| `routes/knowledge.py` | `enrich_knowledge_report_merchant_decisions_v1` |

---

## Decision contract (required fields)

Every published decision includes:

- `decision_id`, `decision_class`, `evidence_ids`, `proof_sources`
- `confidence`, `commercial_goal`, `merchant_action`, `priority`
- `expiration`, `suppression_state`, `verification_status`
- `decision_explanation`, `decision_timestamp`, `lifecycle_state`
- `owner`, `verification_method`

Validated by `validate_merchant_decision_contract_v1()`.

---

## Lifecycle

```
Candidate → Eligible → Published → (Consumed → Resolved | Expired | Archived)
```

Suppression reasons: `already_addressed`, `silent`, `not_eligible`, `merged`, `duplicate`, `expired`.

---

## Priority (governance-defined only)

| Class | Priority |
|-------|----------|
| `critical_action` | 400 |
| `suggested_action` | 300 |
| `needs_attention` | 200 |
| `observation` | 100 |

No AI ranking. Class demotion follows confidence + eligible-action caps (MD-C-2, MD-C-3).

---

## Observability

`get_merchant_decision_observability_v1()` — operational metrics:

- generated / published / suppressed decisions
- class, commercial goal, confidence distribution
- average decision latency (ms)

Not merchant-visible.

---

## Regression

- V1-A `resolve_merchant_decision_key_v1` behavior unchanged
- Proof Surface unchanged
- Truth layers unchanged
- Presentation unchanged (consumers opt-in to payload)

Tests: `tests/test_merchant_decision_execution_v1.py`, `tests/test_merchant_decision_layer_v1.py`
