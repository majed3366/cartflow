# Exact-SHA Deploy Gate — Live Reality Lab V1 + Priority Surface R7

**Date (UTC):** 2026-09-06  
**Status:** READY FOR EXACT-SHA DEPLOY  
**Scheduler:** UNTOUCHED  
**Env var mutation:** NO  
**General merchant release:** NO  

## Purpose

LIVE PRODUCT VALIDATION ONLY on `cf_live_reality_lab` using scenario
`R7_commercial_operational_coexistence` (commercial + operational coexistence).

## Pre-deploy live (re-observed)

| Field | Value |
|-------|--------|
| Live API SHA | `f8192e662615456677b6b65528d4bdfcdc62c6f4` |
| API service | `f3731fa1-43c5-4f72-b8e6-b39b0d028f15` |
| Environment | `1b684334-5b13-4d8e-9c3a-d5816d323850` |
| Autodeploy | OFF (required) |
| Scheduler | must remain `2b1e5665` / `f91e799d` |

Live SHA must be ancestor of runtime candidate. Branch tip must NOT replace
runtime candidate SHA.

## Clean runtime candidate class

| Class | Paths |
|-------|--------|
| Lab package | `services/live_reality_lab_v1/*` |
| Lab routes | `routes/live_reality_lab_v1.py`, `main.py` (router only) |
| Side effects / merch allow | `services/founder_production_evaluation_tenant_v1/{gate,side_effects}_v1.py` |
| HES lab no_phone | `services/home_executive_summary_v1/slim_transport_v1.py` |
| Priority Surface UI | `static/merchant_ui_v2_home.js`, `merchant_ui_v2_workspace.js/.css`, `templates/merchant_app_v2.html` |
| Tests | `tests/test_live_reality_lab_v1.py`, `test_priority_surface_contract_v1.py`, COL/OGL/mission_catalog_projection regressions |
| Docs | `docs/architecture/live_reality_lab_v1/**`, `docs/product/priority_surface_contract_v1/**`, `docs/SYSTEM_SUMMARY.md` §10 |

**EXCLUDED:** visual-identity labs, advisor packs, unrelated PRODUCTION_CLOSURE evidence, strategy-only packs.

## Required zeros

| Gate | Required |
|------|----------|
| FRONTEND RANKING LOGIC | 0 |
| LAB RANKING BYPASS | 0 |
| LAB LIFECYCLE BYPASS | 0 |
| SIMULATION LEAK | 0 |
| CROSS-TENANT MUTATION | 0 |
| EXTERNAL SIDE EFFECTS (lab) | 0 |

## Deploy law

`serviceInstanceDeployV2` + exact `commitSha` only. Not `railway up`. Not branch tip.
