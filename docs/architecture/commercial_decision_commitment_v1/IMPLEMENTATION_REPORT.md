# Commercial Decision Commitment V1 — Implementation Report

**Date (UTC):** 2026-09-05  
**Implementation:** AUTHORIZED (this task) · **Deploy:** NO  

## Delivered

| Piece | Path |
|-------|------|
| Model | `models.CommercialDecisionCommitment` → `commercial_decision_commitments` |
| Schema guard | `schema_commercial_decision_commitment_v1.py` |
| Service | `services/commercial_decision_commitment_v1/` |
| Routes | `routes/commercial_decision_commitment_v1.py` (wired in `main.py`) |
| Attach | After COL in `home_executive_summary_v1/compose_v1.py` + snapshot passthrough |
| Console | Reads `commitment.console_mode` from backend (`merchant_ui_v2_workspace.js`) |
| Tests | `tests/test_commercial_decision_commitment_v1.py` (15) |

## Laws preserved

- COL = evidence; Commitment = lifecycle; Console = paint  
- Accept ≠ measurement start  
- Baseline freezes at measurement start  
- RECHECK_DUE keeps commitment open  
- No WON/LOST/LEARNED/DISCOVERED  
- Scheduler work: 0  

## Active uniqueness

Portable: `active_opportunity_key` (= `opportunity_key` when open, NULL when closed) + UNIQUE(`store_slug`, `active_opportunity_key`). Concurrent accept test: one active row.

## Query delta

Shared `attach_commitment_truth`: **+1** list-open by `store_slug` per dashboard summary (Home and Workspace share the summary).

---

## FINAL SCORECARD

MIGRATION:  
PASS  
(additive model + create_all / schema ensure)

TABLE:  
commercial_decision_commitments

ACTIVE UNIQUENESS:  
PASS

SERVICE OWNER:  
`services/commercial_decision_commitment_v1/`

ACCEPT IDEMPOTENCY:  
PASS

ACTION_CHOSEN TRUTH:  
PASS  
(measurement_started_at NULL; baseline NULL)

MEASUREMENT AUTHORITY:  
PASS  
(`cartflow_execution` + ref, or allowlisted `merchant_execution_confirm`; else refuse)

BASELINE FREEZE:  
PASS  
(at start only; versioned `cdc_measurement_baseline_v1`)

UNDER_MEASUREMENT DERIVATION:  
PASS

RECHECK_DUE DERIVATION:  
PASS

CLOSURE OWNERSHIP:  
PASS  
(bounded reasons; no purchase/due auto-close)

RECHECK KEEPS COMMITMENT OPEN:  
PASS

WON/LOST/LEARNED IMPLEMENTED:  
NO

SCHEDULER WORK:  
0

AI CALLS:  
0

EXTERNAL API CALLS:  
0

HOME QUERY DELTA:  
+1  
(shared attach)

WORKSPACE QUERY DELTA:  
+0  
(incremental; same summary attach)

BACKWARD COMPATIBLE:  
YES

FRONTEND HARDCODE:  
0  
(lifecycle phases; Console maps server `console_mode` only)

SIMULATION LEAK:  
0

EVAL STATES PROVEN:  
actionable, accepted (ACTION_CHOSEN), measuring (UNDER_MEASUREMENT), recheck (RECHECK_DUE), insufficient

TESTS:  
PASS  
(15)

PRODUCTION DEPLOY AUTHORIZED:  
NO

DEPLOY:  
NO

STOP.
