# Paid Event → OEF E2E V1 — Deploy + subscription

**Date (UTC):** 2026-09-11  
**Env mutation:** NO  
**Scheduler:** UNCHANGED  
**Migrations:** UNTOUCHED

| Item | Value |
|------|--------|
| PRE API SHA | `d2f07ce0170a1fd9a33247be2aeefdd4b5726680` |
| CANDIDATE | `4ebfcf2665811fbf0dc485bd840d223d92b15b8a` |
| Deploy | `2c52d3db-dfd9-4feb-a26f-c6c6ab52f60a` SUCCESS |
| POST API SHA | `4ebfcf2665811fbf0dc485bd840d223d92b15b8a` |
| Scheduler | `f91e799d` / `2b1e5665` |
| Subscription | `POST /v1/managers/webhooks` HTTP 200 |
| Event | `order.payment_status.update` **active** |
| Target | `https://smartreplyai.net/webhook/zid` |
| List after | count 1 |

Next: one cheap real paid order on store `3121837` via Zid merchant UI. Do not fabricate `74389634`.
