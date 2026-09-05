# Commercial Decision Commitment V1 — Design Report

**Date (UTC):** 2026-09-05  
**Mode:** Implementation design only  
**Amendment:** `02_EXECUTION_TRUTH_CLOSURE_AMENDMENT.md` (normative)  
**Implementation authorized:** NO  
**Deploy:** NO  

---

## Design verdict

Accept creates ACTION_CHOSEN only. Measurement starts only with CartFlow execution success or allowlisted merchant execution confirmation. Baseline freezes at measurement start. RECHECK_DUE is derived and keeps the commitment open (no WON/LOST). Closure is explicit with a bounded `close_reason`. Scheduler still not required.

---

## FINAL SCORECARD

ACTION_CHOSEN STARTS MEASUREMENT AUTOMATICALLY:  
NO

MEASUREMENT START AUTHORITY:  
`cartflow_execution` (CartFlow execution success) OR allowlisted `merchant_execution_confirm`; external/unproven → refuse; never fabricate

ACTION_CHOSEN DERIVATION:  
open + `action_chosen_at` present + `measurement_started_at` null

UNDER_MEASUREMENT DERIVATION:  
open + `measurement_started_at` present + `now < measurement_due_at`

RECHECK_DUE DERIVATION:  
open + `measurement_started_at` present + `now >= measurement_due_at`

CLOSURE OWNER:  
Merchant (`merchant_cancel` / `merchant_abandon`) + commitment service explicit system closes (`opportunity_invalid` / `superseded` / `recheck_new_decision` / `store_invalidated`) — not purchase, not due clock, not COL paint alone

CLOSURE REASONS:  
`merchant_cancel` | `merchant_abandon` | `opportunity_invalid` | `superseded` | `recheck_new_decision` | `store_invalidated`

RECHECK RESOLUTION:  
Keep same commitment open (rule A); re-read COL; no auto WON/LOST; new decision version only via explicit close + new accept

BASELINE FREEZE POINT:  
Measurement start (`baseline_snapshot_json`); decision-time uses separate `decision_snapshot_json` at accept

BASELINE JSON VERSIONED:  
YES  
(`cdc_decision_snapshot_v1` / `cdc_measurement_baseline_v1`)

ACTIVE UNIQUENESS STILL SAFE:  
YES

IMPLEMENTATION READY:  
YES  
(design corrections applied; still not authorized to code)

IMPLEMENTATION AUTHORIZED:  
NO

DEPLOY:  
NO

STOP.
