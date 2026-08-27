# Queue Composition

The queue is the heart of Carts.

Each row exposes:

- who (customer name, else product, else «سلة»)
- current attention state
- why it is in this queue (canonical label)
- age via `merchant_time_relative_ar` when present
- phone gap when operationally relevant
- VIP chip only when bucket/tabs already say VIP
- one next-action label (same primary key as detail)

Visual priority:

- actionable (`contact_customer` / `follow_up_manually` / `review_cart`) dominate
- waiting (`wait`) is quieter
- completed / archived do not consume equal attention

Filters (existing keys only):

| Key | Merchant intent |
|-----|-----------------|
| `attention` | ماذا يحتاجني؟ |
| `nophone` / `sent` | ماذا ينتظر؟ |
| `recovered` | ماذا اكتمل؟ |
| `all` | كل السلال النشطة |

Default filter (untouched): `attention` when `needs_you > 0`, else waiting/completed/all from truth.

No new taxonomy.
