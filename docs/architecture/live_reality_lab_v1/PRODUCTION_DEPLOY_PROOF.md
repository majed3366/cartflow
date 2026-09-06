# Live Reality Lab V1 + Priority Surface R7 — Exact-SHA Production Deploy Proof

**Date (UTC):** 2026-09-06  
**Mode:** LIVE PRODUCT VALIDATION ONLY  
**General release:** **NO**  
**Founder Product PASS:** **NOT YET** (manual live `/dashboard` review required)

## Identities

| Field | Value |
|-------|--------|
| PRE-DEPLOY LIVE SHA | `f8192e662615456677b6b65528d4bdfcdc62c6f4` |
| RUNTIME CANDIDATE SHA | `4a8d7e89e9e0a512a31951354b8297f43f30220a` |
| Intermediate deploy | `f2fdd4ce329ab38b969ec16efa63617254308edd` (pre-snapshot-rebuild) |
| BRANCH TIP (at proof) | record after docs tip commit |
| Deploy path | `serviceInstanceDeployV2` + exact `commitSha` (not `railway up`) |
| Final deployment ID | `cec41e2b-9632-4ab9-bd40-178d1cd52739` |
| Status | **SUCCESS** |
| Lab store | `cf_live_reality_lab` |
| Lab email | `reality.lab@cartflow.local` |
| Scenario | `R7_commercial_operational_coexistence` |

## Post-deploy identity

| Check | Result |
|-------|--------|
| Live `/dev/merchant-runtime-identity` | `4a8d7e89e9e0a512a31951354b8297f43f30220a` |
| EXACT SHA MATCH | YES |
| `/ping` | 200 |
| `/health` | 200 · QueuePool · `timeout_count=0` |
| Autodeploy | OFF (`ignoreWatchPatterns`) |
| Scheduler | UNCHANGED `2b1e5665` / `f91e799d` |
| Env mutation | NO |

## Lab workflow (production)

1. `POST /api/live-reality-lab/v1/ensure` → store_id **573**
2. Login `reality.lab@cartflow.local` (session cookie; no query-param override)
3. `POST …/reset` → lab-owned rows only
4. `POST …/apply` `{scenario_id: R7_…}` → snapshot rebuild **ok** (~6.5s)
5. `POST …/verify` → **ok** (ops=`communication_followup`, catalog primary=`product_opportunity_focus`, portfolio active=0)

## R7 Home/Workspace truth

| Lane | Evidence |
|------|----------|
| Operational | OGL `communication_followup` · UI **إجراء تشغيلي مطلوب** |
| Commercial | Catalog primary `product_opportunity_focus` mission_ready · UI **المهمة التجارية الحالية** |
| Ops consume mission capacity | **NO** (active_count=0) |
| Lab-specific ranker | **0** |

## Negative / safety

| Proof | Result |
|-------|--------|
| Founder eval lab apply | **403** `live_reality_lab_unauthorized_tenant` |
| Founder summary | `cf_founder_evaluation` · no lab identity/dataset leak |
| Unauth lab scenarios | **401** |
| Demo storefront `/demo/store` | **200** (unchanged path) |
| Lab WhatsApp recovery | **false** |
| External side effects | **0** (blocked) |

## Supporting screenshots (not Founder PASS)

Canonical: `docs/architecture/live_reality_lab_v1/founder_review_r7_v1/`

```
FOUNDER DESKTOP PATH:
C:\Users\Toshiba\Desktop\CartFlow_Founder_Review\Live_Reality_Lab_R7

SCREENSHOT COUNT:
4

DESKTOP COPY READY:
YES
```

## STOP laws

- Do **not** start Merchandising Mission Distinctness Audit V1 until founder manually reviews R7 live.
- General merchant release remains **NO**.
