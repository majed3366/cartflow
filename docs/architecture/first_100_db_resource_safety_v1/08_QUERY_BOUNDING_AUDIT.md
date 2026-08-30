# Query bounding

High-frequency bounds now explicit in `query_bounds_v1.py`:

| Query | Before | After |
|---|---|---|
| Messages fetch | `max(lim, 200)` | cap 80 |
| Customer reply map | `.all()` | `limit 200`, latest-first |
| RecoverySchedule bulk | `.all()` | `limit 2000` |
| MessageLog phones by cart | `.all()` | `limit 1000` (latest-per-cart still applied in memory) |

Already bounded: normal-carts page 50–250, messages visible 40, followups 50, snapshot reads, scanner due limit 25.

Deferred (not merchant-hot or already product-capped): VIP candidate `.all()` before group pick, admin `.all()`, storefront JSON history.

Merchant truth semantics unchanged: Communication still shows recent messages; carts still resolve latest phone per cart.
