# 03 — State → Merchant Responsibility Map

Existing states only. No new lifecycle values.

| Existing signal | Typical primary | Responsibility | يحتاجني? |
|-----------------|-----------------|----------------|----------|
| `waiting_first_send`, `waiting_next_scheduled`, `active` | wait | WAITING_ON_CARTFLOW | No |
| `waiting_customer_reply`, `customer_reply`, `customer_engaged`, `return_to_site`, `waiting_purchase_window` | wait | WAITING_ON_CUSTOMER_OR_DATA if sent/nophone tab, else WAITING_ON_CARTFLOW | No |
| `needs_intervention` + بانتظار الجاهزية / `monitor` | wait | WAITING_ON_CARTFLOW | **No** |
| `needs_intervention` + executable contact + phone | contact_customer | NEEDS_MERCHANT_ACTION_NOW | Yes |
| `needs_intervention` + no phone / obtain_contact | follow_up_manually | NEEDS_MERCHANT_ACTION_NOW | Yes |
| `needs_intervention` + channel/setup fail | follow_up_manually | NEEDS_MERCHANT_ACTION_NOW | Yes |
| `needs_intervention` + needed but not executable | review_cart | NEEDS_MERCHANT_ACTION_NOW | Yes |
| VIP needs_intervention (not already contacted) | follow_up_manually | NEEDS_MERCHANT_ACTION_NOW | Yes |
| `recovery_followup_complete`, `completed`, purchased | no_action_required | COMPLETED_OR_TERMINAL | No |
| archived | reopen / no_action | COMPLETED_OR_TERMINAL | No |
| lifecycle unavailable | review_cart | NEEDS_MERCHANT_ACTION_NOW | Yes |

## Living Store Raven

| Field | Value |
|-------|--------|
| Title | Raven — حزام جلد للساعة |
| Lifecycle | `needs_intervention` |
| Label | بانتظار الجاهزية |
| Tabs | all, attention |
| Primary | wait — انتظر — CartFlow يتابع |
| Ownership | **WAITING_ON_CARTFLOW** |
| يحتاجني | **No** |
