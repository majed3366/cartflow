# Merchant Recovery Policy Semantics & Configurability V6

**Status:** DEPLOYED — exact SHA `90d919d850bef1c762bdb75ca80461b6b514c3d4`  
**Deployment ID:** `4cfb6004-4689-4920-85ec-b952e7cdbc1d`  
**Base:** `f03383647ed347bf143927b6176e956336a1b5fa`  
**Cache:** `recv6`  
**Founder review:** PENDING  

## Timing truth (proven)

- Stage `messages[i].delay` = absolute seconds from cart abandon (primary schedule).
- Store `recovery_delay` = fallback/quiet path only — not first-message when templates apply.
- UI labels aligned to that truth; summary first-message derived from enabled stage-0 delays.

## Reasons

`BLOCKED_BY_REASON_CONTRACT` for add/remove/rename. Safe: activate/deactivate + edit texts/delays/stage count.

## Evidence

`evidence/` — candidate review · `production_evidence/` — live production proof · `PRODUCTION_CLOSURE.md`
