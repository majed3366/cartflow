# Evidence Expansion Framework V1

**Status:** Foundations implemented · **FROZEN** under [Decision Intelligence Framework V1](../decision_intelligence_framework_v1/).  
**Scope:** Internal engineering framework only.  
**Home:** Unchanged. Home consumes published diagnoses only.

## Core principle

Every time CartFlow publishes **"Current evidence is insufficient"** (or conflicting evidence that cannot select a cause), that event **must** create an internal **Evidence Gap**.

An Evidence Gap is an **engineering task**, not a merchant message.

It answers:

> What evidence is missing that would allow this diagnosis to become confident?

## Diagnostic pipeline (unchanged)

```
Observation → Candidate Causes → Evidence Comparison
→ Best Supported Cause → Confidence → Recommendation
```

If evidence cannot distinguish causes:

`Diagnosis Status = INSUFFICIENT_EVIDENCE` (or `CONFLICTING_EVIDENCE`)

**Never guess.**

## What this package does

| Layer | Responsibility |
|-------|----------------|
| Contract | `evidence_gap_v1` schema; `merchant_safe=false`, `internal_only=true` |
| Observable registry | Catalog of future observables keyed to diagnosis families |
| Gap compose | From insufficient/conflicting diagnostic contracts |
| Gap store | Persist `evidence_gaps` (idempotent upsert) |
| Orchestrator | Register gaps after diagnostic materialize (background) |

## What this package does NOT do

- Redesign Home / UI
- Add dashboard pages
- Expose gaps to merchants
- Collect new widget signals yet (await architecture approval)
- Guess causes when evidence is thin

## Performance contract

| Stage | Path |
|-------|------|
| Collection | Background (future) |
| Processing | Background |
| Comparison | Background |
| Publishing diagnoses | Snapshot |
| Home read | Snapshot only |
| Evidence Gap registry | Background write; **never** on Home hot path |

Evidence Expansion must never slow merchant requests.

## Flags

| Flag | Default | Meaning |
|------|---------|---------|
| `CARTFLOW_EVIDENCE_EXPANSION_V1` | OFF (setdefault ON in snapshot builder) | Master enable |
| `CARTFLOW_EVIDENCE_EXPANSION_EXECUTE` | OFF (setdefault ON in snapshot builder) | Persist gaps |

## Success criteria

CartFlow gradually replaces **"Insufficient evidence"** with **supported diagnoses** because new evidence was **intentionally** collected — not because the system became more willing to guess.

## STOP

Stop after foundations + registry + docs.  
Do **not** begin collecting large numbers of new observables until this architecture is reviewed and approved.
