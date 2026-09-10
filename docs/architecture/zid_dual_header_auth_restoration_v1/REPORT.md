# Zid Dual-Header Auth Restoration V1 — Report

**Date (UTC):** 2026-09-10  
**Scope:** Zid Adapter auth only  
**General release:** NO  

Parent live SHA at candidate base: `e5dfbce8397a31b72916203ebecc3e90bf62efd3`

## What changed

Manager request construction now binds both headers to one canonical `Store` row:

- `Authorization: Bearer <stores.zid_authorization_token>`
- `X-MANAGER-TOKEN: <stores.access_token>`

No `ZID_API_AUTHORIZATION` fallback on the Manager path. Missing either credential fails closed (`zid_manager_auth_incomplete`, HTTP 409 on Manager fetches). Cross-store pairs are rejected (`zid_manager_cross_store_rejected`).

OAuth persist is unchanged in mechanism: existing `persist_oauth_tokens_on_store_row` still writes `access_token`, `Authorization` → `zid_authorization_token`, `refresh_token`, expiry. Persist no longer issues Manager HTTP before the write (that would `release_before_wait` → rollback uncommitted tokens). Callers commit persist before identity-sync HTTP.

Partner scripts (`fetch_zid_app_scripts_manifest`) still read unused `ZID_API_AUTHORIZATION` if ever set. That env is not created.

## Tests

`tests/test_zid_dual_header_auth_restoration_v1.py`:

- same-store dual header
- missing Authorization → fail closed
- missing manager token → fail closed
- Store A Authorization + Store B manager token → reject
- OAuth with Authorization → persisted
- OAuth without Authorization → explicit missing authority
- no env fallback
- no token logging

Also green: persist, Zid dev OAuth, storefront widget install (29 tests).

## Deploy / reconnect

Filled after exact-SHA deploy and lab OAuth. See FINAL REPORT below.

==================================================
FINAL REPORT
==================================================

VERDICT: PENDING_DEPLOY_AND_RECONNECT

REQUEST BUILDER FIXED: YES

STORE-SCOPED AUTH SOURCE: stores.zid_authorization_token + stores.access_token (same row)

ENV FALLBACK REMOVED: YES

LAB OAUTH RECONNECTED: NO

LAB AUTHORIZATION PRESENT: NO (pre-reconnect)

LAB MANAGER TOKEN PRESENT: YES (pre-reconnect, presence-only from prior probe)

SAME-STORE BINDING PROVEN: YES (unit)

PROFILE/STORE CALL: not yet (await reconnect)

ABANDONED CART CALL: not yet

ORDERS CALL: not yet

REAL ORDER LIST INSPECTED: NO

REAL ORDER DETAIL INSPECTED: NO

PAYMENT_STATUS OBSERVED: n/a

SUBTOTAL OBSERVED: n/a

DISCOUNT OBSERVED: n/a

CUSTOMER SHIPPING CHARGE OBSERVED: n/a

TAX OBSERVED: n/a

ORDER TOTAL OBSERVED: n/a

TRANSACTION AMOUNT OBSERVED: n/a

CURRENCY OBSERVED: n/a

REFUND DATA OBSERVED: n/a

NEW OAUTH SCOPE: NO

NEW DB COLUMN: NO

ENV MUTATION: NO

DB MUTATION: existing OAuth persist only

SCHEDULER TOUCHED: NO

PLATFORM-NEUTRAL CORE PRESERVED: YES

NEW TECHNICAL DEBT: NONE required

PRE-DEPLOY LIVE SHA: e5dfbce8397a31b72916203ebecc3e90bf62efd3

CANDIDATE SHA: (pending commit)

DEPLOYMENT ID: (pending)

POST-DEPLOY LIVE SHA: (pending)

EXACT SHA MATCH: (pending)

PING: (pending)

HEALTH: (pending)

QUEUEPOOL: (pending)

READY FOR PAID ORDER MONETARY SOURCE CAPTURE: NO

READY FOR ORDER ECONOMIC FACT: NO

READY FOR LEVEL 3: NO

GENERAL RELEASE: NO

STOP.
