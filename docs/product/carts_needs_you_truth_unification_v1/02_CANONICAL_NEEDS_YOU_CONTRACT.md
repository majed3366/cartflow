# 02 — Canonical Needs-You Contract

**Definition (merchant Arabic):**  
يحتاجني = **السلال التي تتطلب إجراءً بشريًا من التاجر الآن**

This is **action-based**, not attention-tab-based.

## Classifier (single)

`needsMerchantActionNow(row)` in `static/merchant_ui_v2_carts.js`:

1. Not archived / purchased / completed  
2. `resolvePrimary(row).key` ∈ `{ contact_customer, follow_up_manually, review_cart }`

Primary-action mappings are **unchanged** (`cart_page_primary_action_v1`).

## Four ownership buckets (presentation only)

No new lifecycle states.

| Bucket | Primary key(s) | Carts meaning |
|--------|----------------|---------------|
| `NEEDS_MERCHANT_ACTION_NOW` | contact / follow_up / review | يحتاجني |
| `WAITING_ON_CARTFLOW` | `wait` (system still owns the next step) | الكل only; not يحتاجني |
| `WAITING_ON_CUSTOMER_OR_DATA` | `wait` + nophone/sent tabs | بانتظار رقم / بانتظار الرد |
| `COMPLETED_OR_TERMINAL` | `no_action_required`, purchased, archived/`reopen` | اكتمل |

## Surfaces that must use the same classifier

- Orientation count and headline  
- Filter chip يحتاجني  
- Queue membership for filter `attention`  
- Selected-cart primary (already the same `resolvePrimary`)

## Explicit rule — بانتظار الجاهزية

If primary is `wait` / «انتظر — CartFlow يتابع», merchant action is **not** required now.

**بانتظار الجاهزية does not belong under يحتاجني.**

Lifecycle may still be `needs_intervention` and the attention tab may still exist on the row. Carts ignores that tab for ownership.
