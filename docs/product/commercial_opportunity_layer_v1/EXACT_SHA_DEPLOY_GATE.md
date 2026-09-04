# Commercial Opportunity Layer V1 — Exact-SHA Deploy Gate

**Date (UTC):** 2026-09-04  
**Status:** READY FOR EXACT-SHA DEPLOY — **NOT EXECUTED**  
**Public release:** NO  
**Flag enable:** NOT YET (wait until runtime SHA verified)

## Identity

| Field | Value |
|--------|--------|
| BASE LIVE SHA | `033cdd482960c6b66f5f22c1027ce3b9ba9f485e` |
| CANDIDATE SHA | `b1867d2c9dadfc6580bf889648093ef90e9d38b3` |
| Branch | `candidate/commercial-opportunity-layer-v1` (pushed) |
| Project | `565c6a84-52db-4e8b-9709-c3801570297a` |
| Environment | `1b684334-5b13-4d8e-9c3a-d5816d323850` (production) |
| Live API | `f3731fa1-43c5-4f72-b8e6-b39b0d028f15` (`smart-reply-ai`) |
| Live domain | `smartreplyai.net` |
| Live scheduler | `882d9906-f7c6-4b29-9180-892be385fbb1` (`cartflow`) @ `f91e799d…` / deploy `2b1e5665…` |
| Autodeploy | OFF (manual deploy path; `ignoreWatchPatterns=true`) |
| COL flag on API | **absent** (correct — do not enable before exact SHA) |
| Preview flag on API | present |

## Prepared mutation (DO NOT RUN until authorized)

```graphql
mutation DeployCartFlowApiExactSha {
  serviceInstanceDeployV2(
    serviceId: "f3731fa1-43c5-4f72-b8e6-b39b0d028f15"
    environmentId: "1b684334-5b13-4d8e-9c3a-d5816d323850"
    commitSha: "b1867d2c9dadfc6580bf889648093ef90e9d38b3"
  )
}
```

Transport: `curl.exe -4` to Railway GraphQL. Not `railway up`. Scheduler untouched.

## Economics

- AI calls on page load: **0**
- External API calls: **0**
- New DB scans: **0**
- DB queries added per Home request: **0** (counts already queried; only serialized)
- New scheduler work: **0**
- Storage growth: **NONE**

## Flag law after deploy

1. Deploy exact SHA first and prove live commit = candidate.
2. Only then set `CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1=1` on **API service only**.
3. Prefer config-only / skip-deploy; if upsert redeploys tip, restore exact SHA immediately.

STOP — no deploy in this gate task.
