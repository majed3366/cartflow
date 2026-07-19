# Product Signal Collection V1 — Deploy Verification

**Date (UTC):** 2026-07-20  
**Scope:** Facts-only product signal collection — no UI, scoring, or Decision Engine.

## Deploy checklist

1. Merge `deploy/product-signal-collection-v1` → `main` (Railway redeploy).
2. Ensure Alembic reaches `u4v5w6x7y8z9` **or** rely on `ensure_product_signal_events_schema` (`create_all`) on first write.
3. Keep `CARTFLOW_PRODUCT_SIGNAL_COLLECTION_V1` unset or `1` (default on).
4. Probe Demo store:

```bash
python scripts/_verify_product_signal_collection_v1.py --base https://smartreplyai.net --store demo
```

5. Confirm DB: `SELECT COUNT(*) FROM product_signal_events WHERE store_slug='demo';` increases after cart_state_sync with `lines[]`.
6. Regression smoke: Demo Home / Carts load without error (no new UI).

## Expected signal types (wired)

- `product_cart_added` / `product_cart_synced` / `product_cart_abandoned`
- `product_interest_hesitation`
- `product_purchased`
- `product_recovery_*`
- `product_customer_returned`
- `product_evidence_linked`

Deferred (catalog only): `product_exposed`, `product_viewed`.
