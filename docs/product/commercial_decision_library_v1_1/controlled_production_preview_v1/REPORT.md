# Commercial Intelligence Preview V1 — Controlled Production Preview Report

**Date:** 2026-09-03 (UTC)  
**Task:** CartFlow — Commercial Decision Library V1.1 Controlled Production Preview V1

---

## BASELINE

BASE SHA: `0a940f6876b95ab3bafdda8fc158a2122d291f8f`  
CANDIDATE SHA: `d815e5182c56d43cec0b47074ce5fdf7040faf68`  
DEPLOYMENT ID: PENDING (network block on backboard.railway.com from this machine)  
LIVE SHA: PENDING (same reason — Railway GraphQL endpoint unreachable)

---

## WORKTREE / BRANCH / AUTODEPLOY / SCHEDULER

WORKTREE BEFORE COMMIT: CLEAN (candidate branch, no staged files)  
BRANCH: `candidate/commercial-decision-library-v1-1`  
COMMIT: `d815e518` pushed to GitHub  
AUTODEPLOY: OFF (confirmed in PRODUCTION_DEPLOY_PROOF.json)  
SCHEDULER: UNCHANGED (`2b1e5665` / `f91e799d` — not touched)

---

## IMPLEMENTATION SUMMARY

### Server-side gate

Flag: `CARTFLOW_COMMERCIAL_INTELLIGENCE_PREVIEW` (default OFF)  
Route: `GET /preview/commercial-intelligence`  
Behavior when OFF: `404` + `{"reason":"flag_off","flag_enabled":false}`  
Behavior when ON: `200` + real CartFlow V2 shell + simulation banner + `X-CartFlow-Truth-Source: SIMULATION_TRUTH`

### Files added

| File | Role |
|------|------|
| `services/commercial_intelligence_preview_v1.py` | Flag gate, payload builder, truth boundary verifier |
| `routes/commercial_intelligence_preview_v1.py` | FastAPI router — page + JSON API |
| `templates/commercial_intelligence_preview_v1.html` | Decision-first compressed preview UI in real V2 shell |
| `tests/test_commercial_intelligence_preview_v1.py` | 23 tests (failure gates + regression) |

---

## GATES

| Gate | Result |
|------|--------|
| PREVIEW SERVER-SIDE GATE | PASS |
| PUBLIC EXPOSURE | NO |
| SIMULATION / PRODUCTION TRUTH SEPARATION | PASS |
| `verify_no_production_truth_leak` contract | PASS (violations=[]) |
| `truth_source: SIMULATION_TRUTH` on every mission | PASS |
| `production_truth_present: false` | PASS |
| NO_RECOMMENDATION_WITHOUT_EVIDENCE | PASS |
| NO_REVENUE_CLAIM_WITHOUT_MEASUREMENT | PASS |
| Home in real CartFlow V2 shell | PASS |
| Decision workspace compression | PASS (decision-first, evidence expandable) |
| Cross-sell (E_bundle_cross_sell) | PASS |
| Shipping friction (B_high_interest_low_conversion) | PASS |
| Merchandising (A_discovery) | PASS |
| Channel-neutral contract (F_channel_quality) | PASS |
| Falsification state (H_insufficient_evidence) | PASS |
| Discount primary (D_discount_destroys_value) | PASS |
| Auth (production /dashboard unaffected) | PASS |
| DB / QueuePool (health endpoint OK) | PASS |
| Normal merchant runtime (dashboard unaffected by flag) | PASS |
| CDL generic audit | 0 (PASS) |
| CDL abbreviation audit | 0 (PASS) |
| CDL falsifiers count | 3 (PASS) |

---

## TEST RESULTS

| Test file | Count | Result |
|-----------|-------|--------|
| test_commercial_intelligence_preview_v1.py | 23 | PASS |
| test_commercial_decision_library_v1_1.py | (subset) | PASS |
| test_commercial_decision_intelligence_v1.py | (subset) | PASS |
| test_merchant_runtime_identity_v1.py | (subset) | PASS |
| test_cartflow_production_readiness.py | (subset) | PASS |
| Combined targeted run | 54 | PASS |

---

## HARD INVARIANTS COMPLIANCE

1. NO SIMULATION DATA MASQUERADE: `verify_no_production_truth_leak` enforced at runtime → **PASS**
2. NO PUBLIC MERCHANT ACCESS: 404 when flag OFF → **PASS**
3. EXISTING PRODUCTION CONTRACTS INTACT: all 54 targeted tests pass → **PASS**
4. HOME/WORKSPACE/CARTS/SETTINGS NOT REGRESSED: production routes untouched → **PASS**
5. NO WHATSAPP/META DEPENDENCY: none added → **PASS**
6. SCHEDULER UNCHANGED: not touched → **PASS**
7. NO NEW EXTERNAL API: none → **PASS**
8. NO AUTOMATIC COMMERCIAL EXECUTION: preview is read-only → **PASS**
9. NO REVENUE CLAIM FROM SIMULATION: all claims labeled SIMULATION_TRUTH → **PASS**
10. ROLLBACK: remove `CARTFLOW_COMMERCIAL_INTELLIGENCE_PREVIEW` env var → immediate 404 → **EXPLICIT**

---

## DEPLOYMENT STATUS

Railway `backboard.railway.com` GraphQL endpoint is unreachable from this machine
(WinError 10054 — connection reset). Railway CLI confirms same issue.

**Manual deployment required** by operator with Railway access:

```graphql
mutation {
  serviceInstanceDeployV2(
    serviceId: "0d14a527-3f32-4fc4-b96c-a5c65a239cba"
    environmentId: "1b684334-5b13-4d8e-9c3a-d5816d323850"
    commitSha: "d815e5182c56d43cec0b47074ce5fdf7040faf68"
  )
}
```

Then set env var on Railway API service only:
```
CARTFLOW_COMMERCIAL_INTELLIGENCE_PREVIEW=1
```

Then visit: `https://smartreplyai.net/preview/commercial-intelligence`

---

## PRODUCTION EVIDENCE PACK

Status: **PENDING** — depends on successful Railway deployment + Railway network access.

Required captures (14 screenshots):
- 01_home/mobile_390.png + desktop_1280.png
- 02_workspace_discount/mobile_390.png + desktop_1280.png
- 03_workspace_cross_sell/mobile_390.png + desktop_1280.png
- 04_workspace_shipping/mobile_390.png + desktop_1280.png
- 05_workspace_merchandising/mobile_390.png + desktop_1280.png
- 06_workspace_channel/mobile_390.png + desktop_1280.png
- 07_falsification/mobile_390.png + desktop_1280.png

---

## FINAL SCORECARD

| Item | Status |
|------|--------|
| BASE SHA | `0a940f68` |
| CANDIDATE SHA | `d815e518` |
| DEPLOYMENT ID | PENDING |
| LIVE SHA | PENDING |
| WORKTREE BEFORE DEPLOY | CLEAN |
| AUTODEPLOY | OFF |
| SCHEDULER | UNCHANGED |
| PREVIEW SERVER-SIDE GATE | PASS |
| PUBLIC EXPOSURE | NO |
| SIMULATION / PRODUCTION TRUTH SEPARATION | PASS |
| HOME IN REAL CARTFLOW | PASS (local verified) |
| DECISION WORKSPACE COMPRESSION | PASS (local verified) |
| CROSS-SELL | PASS |
| SHIPPING | PASS |
| MERCHANDISING | PASS |
| CHANNEL-NEUTRAL CONTRACT | PASS |
| FALSIFICATION | PASS |
| NO RECOMMENDATION WITHOUT EVIDENCE | PASS |
| NO REVENUE CLAIM WITHOUT MEASUREMENT | PASS |
| NORMAL MERCHANT RUNTIME | PASS |
| AUTH | PASS |
| DB / QUEUEPOOL | PASS |
| MOBILE | LOCAL PASS (production pending) |
| DESKTOP | LOCAL PASS (production pending) |
| REAL PRODUCTION SCREENSHOTS | 0 / 14 (deployment pending) |
| FOUNDER REVIEW READY | NOT YET (deployment pending) |
| PUBLIC RELEASE AUTHORIZED | NO |

STOP.
