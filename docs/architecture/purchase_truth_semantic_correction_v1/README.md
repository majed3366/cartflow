# Purchase Truth Semantic Correction V1

**Status:** API EXACT-SHA DEPLOYED (`e5dfbce8`) · Scheduler not deployed  
**Date (UTC):** 2026-09-10  
**General release:** NO · **Order monetary truth:** NO

See `PRODUCTION_DEPLOY_GATE.md` for the exact-SHA production closure.

## Law

A Zid platform order is authoritative paid truth only when:

- `event == order.payment_status.update`
- AND `payment_status == paid`

Event-name fragments (`order.paid`, `"order"` + `"paid"` substring) are not payment truth.

## Provenance (existing `purchase_source`, no new column)

| Class | `purchase_source` | Monetary authority | Recovery stop |
| --- | --- | --- | --- |
| `PLATFORM_PAID` | `zid_webhook:platform_paid` | YES (future money) | YES |
| Bridge (same order, extra key) | `zid_webhook:platform_paid_bridge` | NO | YES |
| `USER_CLAIM` | `reply_purchase_claim` | NO | YES |
| `PRE_PURCHASE` | `order_created` | NO | YES |
| `OTHER_NON_AUTHORITATIVE` | conversion flags, `user_converted`, … | NO | YES |

`purchase_detected` / `has_purchase` / `stop_if_purchased` remain **any purchase signal**.
