# 01 — Current Dual Contract (forensics)

Read-only inventory of the two “needs you” meanings that Carts was painting at once.

## A. Attention needs-you

| | |
|--|--|
| **Source field** | `merchant_cart_visible_tabs` includes `attention`; optional store counters `merchant_cart_filter_counts.attention` |
| **Classifier** | Lifecycle owner (`customer_lifecycle_states_v1` / `merchant_cart_row_classifier._visible_tabs_for_primary`) — `needs_intervention`, engaged, reply → attention tab |
| **Was consumed by** | Carts `filterCounts()` + `rowMatchesFilter("attention")` |
| **Merchant meaning (old)** | “This cart is in the intervention / follow-up bucket” |
| **Action required now?** | **Not necessarily.** Living Store: 15 attention-tab rows, 0 executable merchant primaries |

## B. Primary-action needs-you

| | |
|--|--|
| **Source field** | `cart_page_primary_action_v1.key` |
| **Classifier** | `project_cart_page_primary_action_v1` + client `resolvePrimary` / `countPrimary` |
| **Consumed by** | Orientation (`orientationCopy`); detail CTA |
| **Merchant meaning** | Merchant must act now: `contact_customer` / `follow_up_manually` / `review_cart` |
| **Action required now?** | **Yes**, by definition |

## C. Wait

| | |
|--|--|
| **Source field** | `cart_page_primary_action_v1.key = wait` |
| **Classifier** | Automatic lifecycle states, or `needs_intervention` + جاهزية / `monitor` |
| **Consumed by** | Orientation detail “CartFlow يتابع N”; primary CTA label |
| **Merchant meaning** | انتظر — CartFlow يتابع |
| **Action required now?** | **No** |

## D. Waiting ready (بانتظار الجاهزية)

| | |
|--|--|
| **Source field** | Display label `LABEL_WAITING_READY_AR` / `customer_lifecycle_label_ar` |
| **Classifier** | `resolve_needs_intervention_display_label` when schedule is not materialized or merchant_needed ≠ نعم |
| **Consumed by** | Row/detail attention label |
| **Merchant meaning** | System is not ready to send yet; CartFlow still owns the next step |
| **Action required now?** | **No** — primary is `wait` |

## E. needs_intervention

| | |
|--|--|
| **Source field** | `customer_lifecycle_state` |
| **Classifier** | Lifecycle truth (not rewritten here) |
| **Consumed by** | Tabs (attention), then primary-action *variants* |
| **Merchant meaning** | Lifecycle bucket: recovery is blocked or not in an automatic wait state |
| **Action required now?** | **Only if** primary projects contact / follow_up / review. جاهزية → wait |

## F. needs_merchant_followup

| | |
|--|--|
| **Source field** | Classifier primary `needs_followup` → UI attention tab |
| **Classifier** | `PRIMARY_NEEDS_FOLLOWUP` |
| **Consumed by** | Legacy filters / tabs (not a Carts V2 primary key) |
| **Merchant meaning** | Follow-up lane |
| **Action required now?** | Only after primary-action projection says so |

## G. review_cart

| | |
|--|--|
| **Source field** | `cart_page_primary_action_v1.key = review_cart` |
| **Classifier** | Intervention not executable; unclassified lifecycle |
| **Consumed by** | Needs-you (canonical) |
| **Merchant meaning** | راجع السلة |
| **Action required now?** | **Yes** (inspect / decide) |

## H. contact_customer

| | |
|--|--|
| **Source field** | `cart_page_primary_action_v1.key = contact_customer` |
| **Classifier** | Executable contact + phone |
| **Consumed by** | Needs-you (canonical) |
| **Merchant meaning** | تواصل مع العميل |
| **Action required now?** | **Yes** |

## Contradiction

Same 25 hot-merged rows: attention-tab **15** vs primary needs-you **0**. Orientation used B; يحتاجني used A. Unification retires A as a Carts ownership signal.
