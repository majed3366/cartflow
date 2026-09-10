# Purchase Truth Semantic Correction V1 — Exact-SHA Production Closure

**Date (UTC):** 2026-09-10  
**Method:** Railway GraphQL `serviceInstanceDeployV2(serviceId, environmentId, commitSha)`  
**Not used:** `railway up`, branch-tip deploy, env mutation, Scheduler deploy  
**General release:** NO  
**New technical debt:** NONE

## Pre-deploy (re-observed, not assumed)

| Item | Value |
|------|--------|
| Live API SHA | `16387dd7f40e343d52d6a50dd3ca566a7710f54e` |
| Live API deployment | `e08961c3-9d52-4f79-8bfa-05828a01dbc1` SUCCESS |
| API service | `smart-reply-ai` `f3731fa1-43c5-4f72-b8e6-b39b0d028f15` |
| Live Scheduler SHA | `f91e799d289c99f055ab7edb5cca2063dcd88c9e` |
| Live Scheduler deployment | `2b1e5665-ae6e-4e5b-9e8a-aa1b205fedf9` SUCCESS |
| Autodeploy | OFF (0 deployment triggers) |
| API env var name count | 53 |
| Scheduler env var name count | 44 |
| `/ping` `/health` `/health?db=1` | 200 / 200 / 200 `database: ok` |
| QueuePool `timeout_count` | 0 |

Dirty primary tree was **not** deployed.

## Candidate

| Item | Value |
|------|--------|
| Worktree | `C:\Users\Toshiba\Desktop\cartflow-purchase-truth-semantic-correction-v1` |
| Branch | `candidate/purchase-truth-semantic-correction-v1` |
| Runtime SHA | `e5dfbce8397a31b72916203ebecc3e90bf62efd3` |
| Parent | `16387dd7` (live API) |
| Live SHA ancestor | YES |
| Working tree | clean |
| Diff vs live API | 7 files / +777 / −77 — paid-state semantics + tests only |
| Docs-only SHA | NO (runtime commit deployed; docs committed after) |
| Money / schema | none |

## Deploy

| Item | Value |
|------|--------|
| Executed | YES |
| Deployment ID | `0aa05d32-74ed-4c7c-80f3-e4f7c627ca6e` SUCCESS |
| Post-deploy SHA | `e5dfbce8397a31b72916203ebecc3e90bf62efd3` |
| Exact SHA match | YES (`X-CartFlow-Git-Sha` + `/dev/merchant-runtime-identity` `git_sha` + Railway meta) |
| `/ping` | 200 `{"ok": true}` |
| `/health` | 200 |
| `/health?db=1` | 200 `database: ok` |
| QueuePool `timeout_count` | 0 |
| Autodeploy after | still OFF (0 triggers) |
| API env names after | 53 (unchanged) |
| Scheduler after | `f91e799d` / `2b1e5665` (unchanged) |
| Scheduler env names after | 44 (unchanged) |

## Semantic runtime proof (exact candidate SHA)

| Case | Result |
|------|--------|
| `order.payment_status.update` + `paid` + order id | PLATFORM_PAID accepted |
| same event + `pending` | not authoritative paid |
| same event + `refunded` | not authoritative paid |
| synthetic `order.paid` without `payment_status` | not authoritative Zid paid |
| `order_created` | PRE_PURCHASE only |
| `reply_purchase_claim` | USER_CLAIM only |
| duplicate same-order paid webhook | one PLATFORM_PAID row |
| same order on second recovery_key | bridge, not second canonical paid |

Tests at `e5dfbce8`: `test_purchase_truth_semantic_correction_v1.py` + mapping + foundation **30 passed**.

ANY purchase signal still stops recovery. Only PLATFORM_PAID is authoritative paid.

## FINAL REPORT

PRE-DEPLOY LIVE SHA: `16387dd7f40e343d52d6a50dd3ca566a7710f54e`  
CANDIDATE SHA: `e5dfbce8397a31b72916203ebecc3e90bf62efd3`  
LIVE SHA ANCESTOR: YES  
CANDIDATE CLEAN: YES  
DEPLOYMENT ID: `0aa05d32-74ed-4c7c-80f3-e4f7c627ca6e`  
POST-DEPLOY LIVE SHA: `e5dfbce8397a31b72916203ebecc3e90bf62efd3`  
EXACT SHA MATCH: YES  
PING: 200  
HEALTH: 200 (`/health` and `/health?db=1`)  
QUEUEPOOL: `timeout_count=0`  
PLATFORM_PAID RUNTIME PROOF: PASS  
PENDING REJECTED: PASS  
REFUNDED REJECTED: PASS  
SYNTHETIC order.paid REJECTED: PASS  
ORDER_CREATED CLASS: PRE_PURCHASE  
WHATSAPP CLAIM CLASS: USER_CLAIM  
CANONICAL ORDER DEDUPE: PASS  
BRIDGE BEHAVIOR: PASS  
PURCHASE SUPPRESSION: preserved (any signal)  
SCHEDULE CANCELLATION: preserved  
PRODUCT PURCHASE MAPPING: preserved  
TENANT ISOLATION: preserved (cross-tenant PLATFORM_PAID fail-closed)  
DB CHANGED: NO  
SCHEDULER TOUCHED: NO  
AUTODEPLOY: OFF  
NEW TECHNICAL DEBT: NONE  
READY FOR PAID ORDER MONETARY TRUTH: NO  
GENERAL RELEASE: NO  

STOP.
