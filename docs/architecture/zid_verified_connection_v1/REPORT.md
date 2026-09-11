# Zid Verified Connection V1 — Report

**Date (UTC):** 2026-09-11  
**Scope:** Merchant connection reliability. Zid Adapter verification only. Core UI consumes normalized capability.  
**General release:** NO  
**Ready for Level 3:** NO  

Parent live SHA at candidate base: `84065f745590822660099522d33881d0ca367d2d`

## What changed

Canonical server-owned connection state lives in `services/merchant_connection_capability_v1.py`.

`تم الربط` is painted only for `CONNECTED_VERIFIED`. Access-token presence is no longer authoritative.

Zid verification (`services/zid_connection_verification_v1.py` + `probe_zid_manager_store`):

- dual tokens on the same store row
- credentials not known-expired
- bounded GET `/v1/managers/account/store` (OAuth callback / `POST /api/merchant/store-connection/verify` only)
- authenticated numeric identity bound via `store_identity_aliases.zid_numeric_id`
- `connected_at` written only after success

CartFlow slug `stores.zid_store_id` is never overwritten by OAuth (`cartflow-42b491` stays CartFlow identity).

Merchant copy:

| State | Copy |
|---|---|
| CONNECTED_VERIFIED | تم الربط |
| RECONNECT_REQUIRED | إعادة الربط مطلوبة |
| AUTH_INCOMPLETE | لم يكتمل الربط |
| AUTH_REJECTED | تعذر التحقق من الربط |
| IDENTITY_MISMATCH | تعذر تأكيد هوية المتجر |
| VERIFICATION_PENDING | جارٍ التحقق من الربط |

Dashboard GET does not call Manager. Query delta +1 store-scoped alias read when identity is not already on the store bundle (instance cache). N+1 = 0. Verification does not enable Scheduler, recovery campaigns, WhatsApp, or storefront execution.

## Tests

`tests/test_zid_verified_connection_v1.py` (18):

- access token only → AUTH_INCOMPLETE
- Authorization only → AUTH_INCOMPLETE
- both tokens + Manager 200 + identity match → CONNECTED_VERIFIED
- both tokens + Manager 401 → AUTH_REJECTED
- identity mismatch → IDENTITY_MISMATCH
- expired credential → RECONNECT_REQUIRED
- OAuth without Authorization → not connected
- OAuth both tokens + probe unavailable → VERIFICATION_PENDING
- `zid_numeric_id` only after Manager proof
- `connected_at` only after CONNECTED_VERIFIED
- dashboard + onboarding same rule
- dashboard GET does not probe Manager
- stale snapshot without `verified` is not green
- cross-tenant header pair rejected
- persist does not overwrite CartFlow slug
- no Scheduler / recovery / WhatsApp activation on verify

Also green: merchant store connection, Zid persist, Zid dev OAuth, store identity, onboarding readiness/setup/journey/hardening, admin snapshot `store_connected`, session identity, dual-header restoration, integration health. Pre-existing phase1b widget-panel 200ms / failsafe-reason failures unchanged.

## Pre-deploy (re-observed)

| Item | Value |
|---|---|
| LIVE API SHA (HTTP `git_sha` + Railway) | `84065f745590822660099522d33881d0ca367d2d` |
| API deployment id | `deada12f-1ec5-4872-97c6-5566a8c79f4e` |
| Scheduler SHA | `f91e799d289c99f055ab7edb5cca2063dcd88c9e` |
| Scheduler deployment | `2b1e5665-ae6e-4e5b-9e8a-aa1b205fedf9` |
| Autodeploy API | OFF |
| Autodeploy Scheduler | OFF |
| API env name count | 53 |
| Scheduler env name count | 44 |
| Live SHA ancestor of candidate | YES (candidate commits on live SHA) |
| Env mutation | NO |
| Scheduler touched | NO |

`/ping` 200 · `/health` 200 · `/health?db=1` 200 · QueuePool `timeout_count=0`

## Deploy / live lab

Filled after exact-SHA API deploy (`serviceInstanceDeployV2`, never `railway up`) and lab verify on `cartflow-42b491`.
