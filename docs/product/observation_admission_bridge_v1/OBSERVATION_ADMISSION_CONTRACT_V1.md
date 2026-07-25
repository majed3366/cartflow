# Observation Admission Contract V1

## Flow (mandatory)

```
Product Signals
        ↓
Observation Foundation
        ↓
Observation Candidate
        ↓
Evidence Validation
        ↓
Confidence Validation
        ↓
Canonical Product Identity
        ↓
Reality Validation Admission
        ↓
Knowledge Routing
        ↓
Home Teaser / Decision Workspace
```

No surface may bypass this flow.

## Admit only when

| Requirement | Rule |
|-------------|------|
| Real canonical product identity | Resolves to a real display name (catalog / snapshot / mapping) |
| Clear observation type | `statement_capability` in the governed set |
| Sufficient evidence | Evidence refs and/or counts/compare/reasons |
| Valid confidence | Score ≥ 30 |
| Evidence references | Recorded on the finding diagnostics |
| Freshness | Correlation mass from current foundation assemble (Time Authority window) |
| No material contradiction | Capability marker already implies non-conflict at foundation |
| Merchant-safe wording | Template statements only — no technical IDs on Home |
| Surface eligibility | Home teaser always if admitted; Workspace only if actionable |
| Traceable admission | `admission` stamp + suppression registry for rejects |

## Home boundary

Short teaser only: product name + observation statement.  
CTA: View Details → Decision Workspace.  
No evidence dumps, correlation IDs, or recommendation reasoning on Home.

## Decision Workspace boundary

Admitted observation enters Workspace **only if** it supports a real merchant decision  
(`supports_decision=true`).  

`no_quality_issue_evidence` → Home only (observation, not a forced decision).

## Suppression

Every rejection records: observation ID, product key, stage, reason, missing evidence, confidence, may_become_eligible_later.
