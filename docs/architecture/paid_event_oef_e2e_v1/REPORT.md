# Paid Event → OEF E2E V1 — Report

**Date (UTC):** 2026-09-11  
**Fabricated webhook:** NO  
**Manual PT/OEF insert:** NO

## Phase 1 — registration

| Item | Evidence |
|------|----------|
| Store | `cartflow-42b491` / `3121837` CONNECTED_VERIFIED |
| `GET /v1/managers/webhooks` | HTTP 200, **count 0** |
| Health summary | healthy 0 / degraded 0 / broken 0 |
| Callback | none registered |
| CartFlow subscribe client | absent (probe POST `{}` → **422 Inputs**, write permitted) |
| OAuth env | `abandoned_carts.read orders.read` only |
| `ZID_WEBHOOK_SECRET` | absent |
| Auth documented by Zid | optional Basic Auth on create |
| Auth implemented (pre-fix) | HMAC `X-Zid-Signature` only |

## Phase 2 — delivery for `74389634`

| Check | Result |
|-------|--------|
| PT rows for order | 0 |
| `zid_webhook:platform_paid` anywhere | 0 |
| `recovery_events` Zid/order/payment | 0 of 16 |
| OEF for order | 0 |

Class **A**.

## Phase 4 — replay

Zid retries a failed delivery 3 times, then marks broken. Recover requires a **new** target URL. No API redelivers a historical paid event that was never subscribed. **NO**.

## Falsified alternatives

- Received/rejected: no RecoveryEvent; no subscription to reject  
- Tenant mapping / PT logic / OEF fetch: never reached  
- Predated a later subscription: list is empty now and history has 0 Zid events  

## Correction

`verify_webhook_signature` accepts documented Basic Auth (`username=cartflow`, password = `ZID_WEBHOOK_SECRET` or existing `ZID_CLIENT_SECRET`). HMAC path kept. Then create the paid-event subscription only after that SHA is live.
