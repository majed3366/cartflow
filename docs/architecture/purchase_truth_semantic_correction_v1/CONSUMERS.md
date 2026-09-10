# Purchase Truth consumers — signal class

| Consumer | Requires | Notes |
| --- | --- | --- |
| `has_purchase` / `bulk_has_purchase` | ANY PURCHASE SIGNAL | Recovery stop + dashboard purchased flag |
| `stop_if_purchased` | ANY | Unchanged |
| Recovery schedule cancellation | ANY | `_cancel_pending_recovery` after any PT write |
| Return / continuation suppression | ANY | Lifecycle closure still fires on any ingest |
| `ProductPurchaseMapping` | ANY write via `record_purchase` | Dedup hash uses `order_id` when present — bridge does not duplicate mappings |
| WhatsApp «تم الطلب» / `reply_purchase_claim` | USER_CLAIM | Operational stop only. Must never authorize paid amount / AOV / revenue |
| `order_created` | PRE_PURCHASE | Conversion API + platform gateway `EVENT_ORDER_CREATED`. Zid webhook builder does not treat it as paid |
| `/api/conversion` flags | OTHER_NON_AUTHORITATIVE | Still stops recovery. Not Zid platform paid |
| Commercial measurement / AOV / revenue | AUTHORITATIVE PLATFORM PAID | No money fields exist yet |

ANY purchase signal may still stop recovery. Only PLATFORM_PAID is authoritative paid.
