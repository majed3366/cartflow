# Commercial Advisor Production Integration V1.1 — Exact-SHA Deploy Gate

**Date (UTC):** 2026-09-04  
**Status:** READY FOR EXACT-SHA DEPLOY — **NOT EXECUTED**  
**Public release:** NO  
**Flag enable:** NOT YET (wait until runtime SHA verified live)  
**Visual reopen:** NO (founder gates closed)

## Governing law applied

Observe → Evidence → Reproduce → Define Invariants → Controlled Snapshot → Regression → Production Identity Proof → Exact-SHA Readiness → **STOP**

---

## Phase 1 — Worktree classification (at gate time)

Branch: `candidate/commercial-opportunity-layer-v1`  
Parent tip before runtime commit: `2514c5c8`  
Frozen COL logic baseline: `b1867d2c9dadfc6580bf889648093ef90e9d38b3`

### Classification legend

| Class | Meaning |
|-------|---------|
| A | Required production runtime |
| B | Required tests |
| C | Canonical docs / evidence |
| D | Lab / dev-only visual exploration |
| E | Unrelated preserved work |
| F | Generated / disposable |
| G | Unknown — BLOCK |

### A — Required production runtime (committed in RUNTIME CANDIDATE)

- `static/commercial_decision_arc_production_v1.js`
- `static/commercial_decision_arc_production_v1.css`
- `static/merchant_ui_v2_home.js` / `.css`
- `static/merchant_ui_v2_workspace.js` / `.css`
- `templates/merchant_app_v2.html`
- Plus COL package already on `b1867d2c` (`services/commercial_opportunity_layer_v1/*` + Home attach wiring)

### B — Required tests (committed in RUNTIME CANDIDATE)

- `tests/test_commercial_advisor_production_integration_v1.py`
- `tests/test_commercial_advisor_production_integration_v1_1.py`
- `tests/test_commercial_opportunity_layer_v1.py` (CDA wiring assertions)

### C — Canonical docs / evidence (may trail runtime SHA)

- `docs/product/commercial_advisor_production_integration_v1/`
- `docs/product/commercial_advisor_production_integration_v1_1/` (incl. this gate)
- `docs/SYSTEM_SUMMARY.md` §10

### D — Lab / dev-only (NOT in candidate; left dirty)

- `main.py` lab router includes for visual-identity labs
- `routes/services/static/templates/tests` for `commercial_advisor_visual_identity_v1*`
- `.cursor/rules/founder-visual-review-desktop.mdc`
- `docs/product/commercial_advisor_visual_identity_v1*` packs

### E — Unrelated preserved work (NOT in candidate; left dirty)

- Operational guidance / merchant composition PRODUCTION_CLOSURE packs and evidence
- Controlled production preview PNGs / manifests under CDL V1.1
- Capture scripts and other unrelated docs

### F / G

- F: none material for this gate  
- G: **0** (all dirty paths classified)

---

## Phase 2 — Runtime snapshot boundary

| Proof | Result |
|-------|--------|
| Production Home uses real COL truth | YES — compose from `merchant_reason_counts_*` + teasers; flag-gated attach |
| Production Decision Workspace uses real COL truth | YES — `sessionStorage` focus + COL contract |
| `cf-cda` production assets self-contained | YES — `commercial_decision_arc_production_v1.{js,css}` |
| No dev lab route required at runtime | YES — lab routes excluded from candidate `main.py` |
| No simulation module imported by Merchant UI | YES — leak scan clean |
| No static lab mission copied into runtime | YES |
| No hardcoded screenshot/evidence values | YES |
| No development-only CSS/JS dependency | YES |
| No founder-review asset dependency | YES |
| **SIMULATION LEAK** | **0** |
| **LAB RUNTIME DEPENDENCY** | **0** |

---

## Phase 3 — Clean runtime candidate

| Field | Value |
|-------|--------|
| **RUNTIME CANDIDATE SHA** | `0f2ebc5a5730cc015988d47446501170ce0b815f` |
| Verified base (COL + lineage) | `b1867d2c` (contains live `033cdd48` as ancestor) |
| Live production SHA (re-observed) | `033cdd482960c6b66f5f22c1027ce3b9ba9f485e` |
| Branch tip (docs after freeze) | docs-only commits after `0f2ebc5a` (tip may advance; **never deploy tip — deploy runtime SHA only**) |

Includes: COL V1 + composition refinement + `cf-cda` production integration + Composition Fit V1.1 + required tests/assets.  
Excludes: visual-identity labs, unrelated closures, dirty `main.py` lab wiring.

---

## Phase 4 — Clean snapshot proof

```
git show --stat 0f2ebc5a5730cc015988d47446501170ce0b815f
git diff b1867d2c9dadfc6580bf889648093ef90e9d38b3..0f2ebc5a5730cc015988d47446501170ce0b815f --stat
```

Runtime commit file set = 10 paths (7 runtime + 3 test).  
**UNRELATED RUNTIME CHANGES:** 0  
**UNKNOWN FILES:** 0

---

## Phase 5 — Regression

| Suite | Result |
|-------|--------|
| COL + Production Integration V1 + Fit V1.1 | **28 passed** |
| Operational Guidance Layer | **11 passed** |
| CartFlow production readiness | **12 passed** |
| Merchant home experience activation (2 cases) | **FAIL — pre-existing on parent `2514c5c8`** |

Pre-existing proof: same 2 failures on detached `2514c5c8` worktree; candidate delta does not touch `services/merchant_home_experience_activation_v1.py` / those test paths. Causal overlap with changed runtime: **none**.

---

## Phase 6 — Feature flag

Flag: `CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1`

| State | Required | Proof |
|-------|----------|-------|
| OFF | Existing approved Merchant UI | Unit/attach tests: no COL without flag |
| ON | COL + `cf-cda` Production Integration V1.1 | Attach + CDA markers + Fit cachebust `cda1-fit1` |

**Live Railway API:** flag **absent** (correct). **NOT set** in this task.

---

## Phase 7 — Economic / scale

| Metric | Value |
|--------|--------|
| AI calls on page load | **0** |
| External API calls | **0** |
| New DB scans | **0** |
| New scheduler work | **0** |
| DB queries added per Home request | **0** (serialize existing counts) |
| DB queries added per Workspace request | **0** |
| New client runtime dependencies (npm/CDN) | **0** |
| JS payload delta | **+8774 bytes** (`commercial_decision_arc_production_v1.js`) |
| CSS payload delta | **+7074 bytes** (`commercial_decision_arc_production_v1.css`) |
| Storage growth | **NONE** |
| Canvas / WebGL / heavy charts / AI graphics | **NONE** |

---

## Phase 8 — Production identity (re-observed 2026-09-04)

| Field | Verified value |
|-------|----------------|
| Project | `authentic-motivation` / `565c6a84-52db-4e8b-9709-c3801570297a` |
| Environment | `production` / `1b684334-5b13-4d8e-9c3a-d5816d323850` |
| API service | `smart-reply-ai` / `f3731fa1-43c5-4f72-b8e6-b39b0d028f15` |
| API instance | `dd9597c9-4074-4158-a42c-1ae347df75c5` |
| Live API deploy | `4ea7b2f0-9cfb-47fa-a754-419a1dec36fb` SUCCESS |
| **CURRENT LIVE API SHA** | `033cdd482960c6b66f5f22c1027ce3b9ba9f485e` |
| Scheduler service | `cartflow` / `882d9906-f7c6-4b29-9180-892be385fbb1` |
| Scheduler deploy | `2b1e5665-ae6e-4e5b-9e8a-aa1b205fedf9` |
| Scheduler SHA | `f91e799d289c99f055ab7edb5cca2063dcd88c9e` |
| Public domain | `https://smartreplyai.net` |
| `/ping` `/health` | 200 / 200 |
| API config path | `railway.api.toml` |
| Scheduler config path | `railway.scheduler.toml` |
| Start command (API) | `sh -c 'exec python -m uvicorn cartflow_api:app ...'` |
| Watch patterns | `[]` (empty) |
| Autodeploy | **OFF** (manual exact-SHA path; toml: stay disabled) |
| Preview flag | `CARTFLOW_COMMERCIAL_INTELLIGENCE_PREVIEW=1` (unchanged) |
| COL flag | **absent** |

---

## Phase 9 — Production safety delta

`git merge-base --is-ancestor 033cdd48 0f2ebc5a` → **0** (ancestor).  
Candidate contains live production lineage + COL + CDA Fit. No rollback of live runtime.

**CURRENT-PRODUCTION-LINE SAFE:** **YES**

---

## Phase 10 — Prepared mutation (DO NOT EXECUTE)

```graphql
mutation DeployCartFlowApiExactSha {
  serviceInstanceDeployV2(
    serviceId: "f3731fa1-43c5-4f72-b8e6-b39b0d028f15"
    environmentId: "1b684334-5b13-4d8e-9c3a-d5816d323850"
    commitSha: "0f2ebc5a5730cc015988d47446501170ce0b815f"
  )
}
```

Transport: `curl.exe -4` → Railway GraphQL.  
**Not** `railway up`. Do not invent GraphQL args. Do not expose tokens.

---

## Phase 11 — Flag enablement safety plan

1. **STEP A** — Deploy exact runtime candidate SHA with flag still **OFF**.  
2. **STEP B** — Verify deploy SUCCESS, live SHA = candidate, `/ping` `/health` 200, `/dashboard` + Merchant UI normal, auth/store intact, Scheduler untouched.  
3. **STEP C** — Only then evaluate config-only / skip-deploy env mutation; if unproven, assume upsert may redeploy.  
4. **STEP D** — Enable `CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1=1` on **API service only**.  
5. **STEP E** — Immediately re-prove live SHA remains exact candidate; if redeploy, must still be candidate SHA; branch-tip drift → **BLOCK / RECOVER**.

**Not executed in this task.**

---

## Phase 12 — Scheduler immutability

Before-state recorded above. **SCHEDULER TOUCHED: NO**

---

## Phase 13 — No visual reopen

No geometry/spacing/typography/composition changes in this gate. Defects (if any) reported only — none opened for fix.

---

## Absolute stop

DO NOT DEPLOY. DO NOT ENABLE THE FLAG. DO NOT MODIFY RAILWAY ENV VARS. DO NOT TOUCH SCHEDULER. DO NOT REOPEN VISUAL DESIGN.
