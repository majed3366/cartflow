# Exact-SHA Deploy Gate — Founder Production Evaluation Tenant V1

**Date (UTC):** 2026-09-06  
**Status:** READY FOR EXACT-SHA DEPLOY — **NOT EXECUTED**  
**Scheduler:** UNTOUCHED  
**Env var mutation:** NO  

## Governing law

Observe → Harden production allowlist → Evidence → Freeze runtime SHA → Prove line safety → Prepare mutation → **STOP**

## Production evaluation allowlist (count = 1)

| Identity | Production eligible |
|----------|---------------------|
| `cf_founder_evaluation` | YES |
| `cf_fe_v1_*` | **NO** |
| demo / normal merchants | NO |
| env-global merchandising unlock | **NO** |

Owner: `is_founder_production_evaluation_tenant` in `services/founder_production_evaluation_tenant_v1/gate_v1.py`

## Worktree classification (at freeze)

| Class | Paths |
|-------|--------|
| **A — Founder eval gate** | `services/founder_production_evaluation_tenant_v1/*` |
| **B — Side effects** | `services/whatsapp_send.py`, `services/whatsapp_provider.py` |
| **C — Merchandising + COL** | `services/commercial_opportunity_layer_v1/*`, `services/commercial_mission_v1/*`, `services/commercial_decision_commitment_v1/contract_v1.py` |
| **D — Catalog / Portfolio** | `services/mission_catalog_v1/*`, `services/mission_portfolio_v1/*` |
| **E — Dashboard wiring** | `services/home_executive_summary_v1/compose_v1.py`, `services/merchant_home_experience_activation_v1.py`, `services/dashboard_summary_json_safe_v1.py` |
| **F — Merchant UI projection** | `static/merchant_ui_v2_home.js`, `static/merchant_ui_v2_home.css`, `static/merchant_ui_v2_workspace.js`, `static/merchant_ui_v2_workspace.css`, `templates/merchant_app_v2.html` |
| **G — Routes** | `routes/commercial_mission_v1.py`, `main.py` (mission router only) |
| **H — Fixtures (test/local)** | `services/founder_evaluation_reality_v1/*` (not production allowlist) |
| **I — Tests** | `tests/test_founder_production_evaluation_tenant_v1.py`, `tests/test_merchandising_mission_slice_v1.py`, `tests/test_mission_catalog_*.py`, `tests/test_mission_portfolio_v1.py`, `tests/test_commercial_mission_v*.py`, `tests/test_dashboard_summary_json_safe_v1.py` |
| **J — Gate docs** | `docs/architecture/founder_production_evaluation_tenant_v1/**`, `docs/SYSTEM_SUMMARY.md` §10 |
| **K — EXCLUDED** | visual-identity labs, advisor labs, screenshots, strategy packs, unrelated PRODUCTION_CLOSURE evidence, observe scripts |

**UNRELATED RUNTIME CHANGES IN CANDIDATE:** **0**  
**SIMULATION LEAK:** **0**  
**FRONTEND HARDCODE:** **0**

## Frozen SHAs

| | SHA |
|--|-----|
| **RUNTIME CANDIDATE SHA** | _(filled at commit)_ |
| **BRANCH TIP** | _(may equal runtime or docs tip)_ |
| **CURRENT LIVE SHA** | `926739b511d1089668fe5542ef5abb521cf1db54` |

Deploy target = **RUNTIME CANDIDATE SHA only**.

## Line safety

```
git merge-base --is-ancestor 926739b511d1089668fe5542ef5abb521cf1db54 <RUNTIME_CANDIDATE_SHA>
→ required 0
```

CURRENT-PRODUCTION-LINE SAFE: **YES** (CDC V1 + live production runtime included)

## Railway control-plane (re-observed 2026-09-06)

| Field | Value | Trust |
|-------|--------|-------|
| Project | `authentic-motivation` / `565c6a84-52db-4e8b-9709-c3801570297a` | Railway CLI linked |
| Environment | `production` / `1b684334-5b13-4d8e-9c3a-d5816d323850` | Railway CLI linked |
| API service | `smart-reply-ai` / `f3731fa1-43c5-4f72-b8e6-b39b0d028f15` | Railway CLI linked |
| API deployment | `a0d7e9f9-75d9-4b9d-a6fa-702ac96b811e` SUCCESS | `railway deployment list --json` |
| Live API SHA | `926739b511d1089668fe5542ef5abb521cf1db54` | `/dev/merchant-runtime-identity` + deployment meta |
| COL flag | `CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1=1` | `railway variables` |
| Autodeploy | **OFF** (exact-SHA path; do not enable) | Prior gate + no auto push |
| Scheduler service | `cartflow` / `882d9906-f7c6-4b29-9180-892be385fbb1` | Linked |
| Scheduler deployment | `2b1e5665-ae6e-4e5b-9e8a-aa1b205fedf9` SUCCESS | CLI list |
| Scheduler SHA | `f91e799d289c99f055ab7edb5cca2063dcd88c9e` | deployment meta |
| GraphQL backboard | 403 this session | CLI path used instead |

## Prepared mutation (DO NOT EXECUTE)

```graphql
mutation DeployCartFlowApiExactSha {
  serviceInstanceDeployV2(
    serviceId: "f3731fa1-43c5-4f72-b8e6-b39b0d028f15"
    environmentId: "1b684334-5b13-4d8e-9c3a-d5816d323850"
    commitSha: "<RUNTIME_CANDIDATE_SHA>"
  )
}
```

DO NOT use `railway up`.  
DO NOT mutate env vars.  
DO NOT touch Scheduler.  
DO NOT set any merchandising global release flag.

## Post-deploy review plan

1. Exact-SHA deploy  
2. Prove live SHA  
3. Prove Scheduler unchanged  
4. Ensure + login `cf_founder_evaluation` on smartreplyai.net  
5. Open real `/dashboard`  
6. Verify merchandising missions  
7. Capture real mobile + desktop evidence  
8. Founder reviews real production  
9. General merchants remain unchanged  

## DEPLOY

**NO**
