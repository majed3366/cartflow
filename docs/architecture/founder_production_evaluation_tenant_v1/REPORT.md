# REPORT — Founder Production Evaluation Tenant V1
# Production Scope Hardening + Clean Candidate + Exact-SHA Gate

**Date (UTC):** 2026-09-06  
**Deploy:** NO  

## Hardening correction

Production evaluation eligibility is **only** `cf_founder_evaluation`.

`cf_fe_v1_*` remains test/local via `CARTFLOW_TEST_ALLOW_MERCHANDISING_SLICE` — **not** production allowlist.

Environment-global merchandising unlock removed from gate.

## Owner

`is_founder_production_evaluation_tenant(...)`  
Package: `services/founder_production_evaluation_tenant_v1/gate_v1.py`

## Scorecard

See `EXACT_SHA_DEPLOY_GATE.md` for Railway IDs and prepared mutation.

```
PRODUCTION EVALUATION ALLOWLIST:
cf_founder_evaluation

CF_FE_V1 PRODUCTION ELIGIBILITY:
NO

SERVER-SIDE GATE:
PASS

TEST / PRODUCTION SEPARATION:
PASS

SIDE EFFECT BLOCK:
PASS

NORMAL MERCHANT NEGATIVE PROOF:
PASS

FOUNDER POSITIVE PROOF:
PASS

BOOLEAN SANITIZE REGRESSION:
PASS

CURRENT LIVE SHA:
926739b511d1089668fe5542ef5abb521cf1db54

RUNTIME CANDIDATE SHA:
f8192e662615456677b6b65528d4bdfcdc62c6f4

BRANCH TIP:
(docs tip after gate fill)

CANDIDATE CLEAN:
YES

CURRENT-PRODUCTION-LINE SAFE:
YES

UNRELATED RUNTIME CHANGES:
0

SIMULATION LEAK:
0

FRONTEND HARDCODE:
0

AI CALLS:
0

EXTERNAL API CALL DELTA:
0

NEW SCHEDULER WORK:
0

QUERY DELTA:
0

CURRENT API SERVICE ID:
f3731fa1-43c5-4f72-b8e6-b39b0d028f15

CURRENT ENVIRONMENT ID:
1b684334-5b13-4d8e-9c3a-d5816d323850

AUTODEPLOY:
OFF

COL FLAG:
1

CURRENT SCHEDULER SHA:
f91e799d289c99f055ab7edb5cca2063dcd88c9e

CURRENT SCHEDULER DEPLOYMENT:
2b1e5665-ae6e-4e5b-9e8a-aa1b205fedf9

EXACT DEPLOY MUTATION:
prepared (see EXACT_SHA_DEPLOY_GATE.md)

READY FOR FOUNDER EVALUATION EXACT-SHA DEPLOY:
YES

DEPLOY:
NO
```
