# Merchant Recovery Policy Semantics & Configurability V6 — Report

**Base SHA:** `f03383647ed347bf143927b6176e956336a1b5fa`  
**Deployed SHA:** `90d919d850bef1c762bdb75ca80461b6b514c3d4`  
**Direct parent:** `f03383647ed347bf143927b6176e956336a1b5fa`  
**Deployment ID:** `4cfb6004-4689-4920-85ec-b952e7cdbc1d`  
**Deploy path:** `serviceInstanceDeployV2` + exact `commitSha`  
**Status:** CLOSED IN PRODUCTION (founder real-device review PENDING)

## Timing (proven)

| Field | Meaning |
|-------|---------|
| Global `Store.recovery_delay` | Fallback/quiet path only when templates do not supply schedule |
| Stage `messages[i].delay` | Absolute delay from cart abandon for stage *i* |

UI labels and summary updated to this truth. Production timing ambiguity: **0**.

## Reasons

`BLOCKED_BY_REASON_CONTRACT` for add/remove/rename.  
Safe: activate/deactivate (`enabled`), edit texts/delays/stage count.  
Hard delete: FORBIDDEN_BY_HISTORY.

## Other

CartFlow stage-count control; Tajawal typography on recovery; internal/dev copy removed from Merchant UI V2 surfaces. V5 visual identity preserved. Products unchanged.

## Closure

See `PRODUCTION_CLOSURE.md` · `PRODUCTION_DEPLOY_PROOF.json` · `production_evidence/`.
