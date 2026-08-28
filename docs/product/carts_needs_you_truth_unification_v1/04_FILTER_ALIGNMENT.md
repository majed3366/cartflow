# 04 — Filter Alignment

No new filter keys.

| Key | Label | Membership now |
|-----|--------|----------------|
| `all` | الكل | Active (non-archived) page rows |
| `attention` | يحتاجني | `needsMerchantActionNow` only (same as orientation) |
| `nophone` | بانتظار رقم العميل | Same-generation row tabs `nophone` |
| `sent` | بانتظار الرد | Same-generation row tabs `sent` |
| `recovered` | اكتمل | Completed or archived |

Removed: overwrite from `merchant_cart_filter_counts` (snapshot / store totals — different generation).

Default (untouched merchant): `attention` when canonical needs-you > 0, else `all` (or recovered if only archive). On the current Living Store payload that default is **الكل**.
