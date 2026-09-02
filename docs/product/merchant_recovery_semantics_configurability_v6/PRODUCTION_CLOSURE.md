# Merchant Recovery Policy Semantics & Configurability V6 — Exact Production Closure

**Date (UTC):** 2026-09-02  
**DEPLOYED SHA:** `90d919d850bef1c762bdb75ca80461b6b514c3d4`  
**BASELINE:** `f03383647ed347bf143927b6176e956336a1b5fa`  
**DEPLOYMENT ID:** `4cfb6004-4689-4920-85ec-b952e7cdbc1d`  
**Path:** `serviceInstanceDeployV2` + exact `commitSha` (not `railway up`)  
**Autodeploy:** OFF  
**Scheduler:** `2b1e5665` / `f91e799d` UNCHANGED  

## Production identity

| Field | Value |
|-------|-------|
| SERVER SHA | `90d919d850bef1c762bdb75ca80461b6b514c3d4` |
| Renderer | `merchant_ui_v2` |
| Template | `merchant_app_v2.html` |
| Semantic model | `semantic-visual-model-v1` |
| Config parity | PASS |
| Old dashboard silent return | NO |

## V6 founder-visible proof

| Check | Result |
|-------|--------|
| Global timing = fallback/quiet only | PASS |
| Stage timing = absolute from abandon | PASS |
| Timing ambiguity | 0 |
| Historical reason integrity (7 picker) | PASS |
| Reason add | BLOCKED |
| Reason edit (text/delay/stage) | PASS |
| Reason deactivate (enable checkbox) | PASS |
| Reason hard delete | FORBIDDEN_BY_HISTORY |
| CartFlow stage-count control | PASS |
| Native stage-count select visible | 0 |
| Tajawal typography | PASS |
| Internal/developer copy («لا تفتح واجهة قديمة» / V2 jargon) | 0 |
| V5 visual identity (continuum / message surface / restore) | PASS |
| Packages compose v5 / 3 cards | PASS |
| Home / Workspace / Carts / Comms / Settings / WhatsApp / Widget / Account / VIP | PASS |
| Products | UNCHANGED |

## Operational

| Check | Result |
|-------|--------|
| `/dashboard` | 200 |
| QueuePool `timeout_count` | 0 |
| Autodeploy | OFF |
| Scheduler | UNCHANGED |

## Founder review

**FOUNDER REVIEW: PENDING** (real-device).  
Successful deploy ≠ founder visual closure.

**DEPLOYMENT CLOSED: YES**

Evidence: `production_evidence/` · `PRODUCTION_DEPLOY_PROOF.json`

STOP.
