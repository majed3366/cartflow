# Business Reasoning Engine V1

**Status:** Implemented — await Product approval before surface consumption  
**Type:** Foundational product layer (not AI, not Home, not text generation)  
**Date (UTC):** 2026-07-18  

## Mission

Transform multiple validated **Business Findings** into merchant-ready **business guidance**.

| Layer | Answers |
|-------|---------|
| Business Findings | What did we discover? |
| Business Reasoning | What does it mean? What should the merchant prioritize? |

## Pipeline

```
Merchant Truth
  → Evidence
    → Business Findings
      → Business Reasoning
        → Merchant Guidance
          → Knowledge Routing
            → All Merchant Surfaces
```

Reasoning **never bypasses** Truth → Evidence → Finding.

## Core principle

Reasoning never creates facts.  
Reasoning only connects existing validated findings.  
Every sentence must be explainable.  
If reasoning cannot be supported by findings, it must not exist.

## Modules

| Module | Role |
|--------|------|
| `services/business_reasoning_contract_v1.py` | `BusinessReasoningV1` contract, quality gates, approved-findings filter |
| `services/business_reasoning_rules_v1.py` | Deterministic rules for 5 categories |
| `services/business_reasoning_engine_v1.py` | Package, ranking, guidance/knowledge candidates |

## Reasoning categories (deterministic)

1. **Finding relationships** — combine related discoveries into one business meaning  
2. **Priority detection** — “If you improve only one thing this week…”  
3. **Conflict detection** — when evidence cannot choose between explanations  
4. **Constraint detection** — what blocks action before other improvements matter  
5. **Opportunity detection** — where faster gains are supported by findings  

## Reasoning rules

- May combine multiple Findings  
- May **not** invent evidence  
- May **not** assume causation  
- Must distinguish **Observed / Likely / Unknown**  

## Output card

Every card contains:

1. Headline  
2. Business meaning  
3. Recommended priority  
4. Expected impact  
5. Confidence  
6. Supporting findings (merchant labels)  

## Quality gates (all required)

1. Multiple findings contributed  
2. Creates a business decision  
3. Merchant could act today  
4. Removing the card would reduce product value  

## Merchant language

Never expose: Finding, Pattern, Correlation, BusinessFinding, Engine, Reasoning, Registry, Confidence Model.

## Non-goals

- Do not redesign Home / Products  
- Do not introduce LLM advice or predictive AI  
- Do not generate recommendations without deterministic evidence  
- Do not wire surfaces until Product approval  

## Consume feed (later)

`guidance_candidates_v1`:

- `weekly_priority`  
- `primary_relationship`  
- `top_constraint`  
- `top_opportunity`  
- `open_conflict`  

## Reports / tests

- Demo: `docs/business_findings/BUSINESS_REASONING_DEMO_REPORT_V1.md`  
- Runner: `scripts/run_business_reasoning_demo_v1.py`  
- Tests: `tests/test_business_reasoning_engine_v1.py`  

## Product Review Lab

- Route: `/dev/business-reasoning-review` (not in merchant navigation)  
- Spec: `BUSINESS_REASONING_REVIEW_LAB_V1.md`  
- Service: `services/business_reasoning_review_lab_v1.py`  
- Template: `templates/business_reasoning_review_lab_v1.html`  
- Standalone host: `scripts/_serve_business_reasoning_review_lab_v1.py`  
- Tests: `tests/test_business_reasoning_review_lab_v1.py`  

## STOP

Await Product approval via the Review Lab.  
Do not connect Home / Products / Customers / WhatsApp / Knowledge / Reports to this layer until approved.
