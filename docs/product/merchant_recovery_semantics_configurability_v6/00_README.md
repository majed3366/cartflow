# Merchant Recovery Policy Semantics & Configurability V6

**Status:** CANDIDATE — deploy NOT authorized  
**Base:** `f03383647ed347bf143927b6176e956336a1b5fa`  
**Cache:** `recv6`

## Timing truth (proven)

- Stage `messages[i].delay` = absolute seconds from cart abandon (primary schedule).
- Store `recovery_delay` = fallback/quiet path only — not first-message when templates apply.
- UI labels aligned to that truth; summary first-message derived from enabled stage-0 delays.

## Reasons

`BLOCKED_BY_REASON_CONTRACT` for add/remove/rename. Safe: activate/deactivate + edit texts/delays/stage count.

## Evidence

`evidence/` — 390 RTL + 1280.
