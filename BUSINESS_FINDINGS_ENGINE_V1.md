# Business Findings Engine V1

**Status:** Implemented — await Product review before Home wiring  
**Type:** Foundational product intelligence (not UI, not Home redesign)  
**Date (UTC):** 2026-07-17  

## Mission

Convert existing CartFlow evidence into **deterministic, explainable, merchant-worthy commercial findings**.

Raw facts are not findings. Findings state what store behaviour **means commercially**.

## Pipeline

```
Existing Truth
  → Evidence Aggregation
    → Commercial Pattern Detection
      → Business Finding
        → Merchant Guidance
          → Confidence
            → Ranking + Deduplication
              → Knowledge Routing candidates
                → Merchant Surfaces (consume only)
```

Home and other surfaces **must not** independently construct commercial conclusions.

## Modules

| Module | Role |
|--------|------|
| `services/business_findings_contract_v1.py` | `BusinessFindingV1` contract |
| `services/business_findings_evidence_v1.py` | EvidenceBundle + DB/fixture loaders |
| `services/business_findings_families_v1.py` | Finding families F1–F10 (+ contact dedupe type) |
| `services/business_findings_engine_v1.py` | Rank, dedupe, package, Home candidates, KL projection |

## Non-negotiables

1. Truth before intelligence  
2. Evidence before advice  
3. No guessing confirmed causes  
4. Deterministic first — **no AI authority**  
5. Insufficient evidence is a valid result  
6. One finding, one meaning  
7. Merchant-worthy output  
8. Explainability preserved on every finding  

## Home integration rule

This phase provides `home_candidates_v1`:

- one most important finding  
- one strongest opportunity  
- one highest-value action  
- one meaningful new understanding  

**Do not redesign Home in this phase.** Await Product approval before connecting.

## Reports

- Demo findings: `docs/business_findings/BUSINESS_FINDINGS_DEMO_REPORT_V1.md`  
- Coverage gaps: `docs/business_findings/BUSINESS_FINDINGS_COVERAGE_GAP_V1.md`  
- Runner: `scripts/run_business_findings_demo_v1.py`  

## Tests

`tests/test_business_findings_engine_v1.py`

## Product Review Lab

Merchant-facing acceptance surface (not Home):

**`/dev/business-findings-review`**

See `MERCHANT_FINDINGS_REVIEW_LAB_V1.md`.

## Downstream

Approved findings are the only valid input to **Business Reasoning Engine V1**  
(`BUSINESS_REASONING_ENGINE_V1.md`). Reasoning must not bypass Findings.

## STOP

Await Product review on the Review Lab. Do not wire findings into Home UI until approved.
